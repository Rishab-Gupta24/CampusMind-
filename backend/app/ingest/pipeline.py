"""Runs a whole upload as a background task: prepare → store → load/transcribe → chunk → (flag) → embed → upsert.

A source ends as `ready`, or `failed` with a short message users can read.
"""

import asyncio
import logging
from pathlib import Path

from app import db
from app.config import get_settings
from app.ingest import flagger, prepare
from app.ingest.chunker import Chunk, chunk_lecture, chunk_pdf
from app.ingest.deadlines import extract_events
from app.ingest.lecture_notes import write_notes
from app.ingest.ocr import OCRError, image_to_pdf
from app.ingest.pdf_loader import load_pdf_with_ocr, page_count
from app.ingest.prepare import PrepareError
from app.ingest.transcriber import Segment, transcribe
from app.rag.embedder import EmbedError, embed_texts

log = logging.getLogger(__name__)

GENERIC_FAILURE = "Processing failed. Try uploading the file again."


def pdf_storage_path(source_id: str) -> str:
    return f"pdfs/{source_id}.pdf"


def audio_storage_path(source_id: str) -> str:
    return f"lectures/{source_id}.opus"


def transcript_storage_path(source_id: str) -> str:
    return f"transcripts/{source_id}.json"


def tmp_path(name: str) -> Path:
    directory = get_settings().tmp_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory / name


def _index(source_id: str, chunks: list[Chunk], flag_reasons: dict[str, str] | None = None) -> None:
    """Replace every chunk of a source. Deterministic ids keep re-uploads from duplicating."""
    reasons = flag_reasons or {}
    vectors = embed_texts([c["content"] for c in chunks])
    rows = [
        {
            **chunk,
            "source_id": source_id,
            "embedding": vector,
            "flagged": chunk["id"] in reasons,
            "flag_reason": reasons.get(chunk["id"]),
            "ocr": bool(chunk.get("ocr")),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    db.delete_chunks(source_id)
    db.upsert_chunks(rows)


def _fail(source_id: str, exc: Exception) -> None:
    safe = isinstance(exc, PrepareError | EmbedError | OCRError)
    if not safe:
        log.exception("Pipeline failed for source %s", source_id)
    db.update_source(source_id, {"status": "failed", "stage": None, "error": str(exc) if safe else GENERIC_FAILURE})


IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def _suggest_dates(source_id: str) -> None:
    """Handouts and circulars often list exam dates: offer them as calendar suggestions (best effort)."""
    source = db.get_source(source_id)
    if not source or source["kind"] not in ("handout", "campus"):
        return
    try:
        asyncio.run(extract_events(source_id))
    except Exception:
        log.exception("Date extraction failed for %s", source_id)


def process_document(source_id: str, upload_path: Path) -> None:
    compressed = tmp_path(f"{source_id}.compressed.pdf")
    converted = tmp_path(f"{source_id}.image.pdf")
    try:
        db.update_source(source_id, {"stage": "reading"})
        source_path = upload_path
        if upload_path.suffix.lower() in IMAGE_TYPES:
            source_path = image_to_pdf(upload_path, converted)
        stored = prepare.prepare_pdf(source_path, compressed)

        def progress(done: int, total: int) -> None:
            db.update_source(source_id, {"stage": f"ocr:{done}/{total}"})

        pages = load_pdf_with_ocr(stored, progress)
        if not pages:
            raise PrepareError("No readable text was found in this file.")
        db.update_source(source_id, {"stage": "indexing"})
        db.upload_file(pdf_storage_path(source_id), stored, "application/pdf")
        chunks = chunk_pdf(source_id, pages)
        _index(source_id, chunks)
        db.update_source(
            source_id,
            {
                "status": "ready",
                "stage": None,
                "error": None,
                "pages": page_count(stored),
                "storage_path": pdf_storage_path(source_id),
            },
        )
        _suggest_dates(source_id)
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)
    finally:
        prepare.cleanup(upload_path, compressed, converted)


def _lecture_intelligence(source_id: str, title: str, segments: list[Segment], duration: float) -> None:
    """Chunk → flag (cue + LLM) → embed → notes. Notes are best effort; flags and chunks are not."""
    db.update_source(source_id, {"stage": "flagging"})
    transcript = [{"start_s": s["start"], "end_s": s["end"], "text": s["text"]} for s in segments]
    db.upload_json(transcript_storage_path(source_id), transcript)
    chunks = chunk_lecture(source_id, segments)
    moments = asyncio.run(flagger.detect(title, segments))
    reasons = flagger.apply_to_chunks(chunks, moments)
    db.update_source(source_id, {"stage": "indexing"})
    _index(source_id, chunks, reasons)
    db.update_source(source_id, {"stage": "notes"})

    notes: dict[str, object] = {"summary": "", "key_points": [], "formulas": []}
    try:
        notes = dict(asyncio.run(write_notes(title, segments)))
    except Exception:
        log.exception("Lecture notes failed for %s", source_id)
    db.upsert_lecture_notes({"source_id": source_id, **notes, "flagged_moments": moments})
    db.update_source(
        source_id,
        {
            "status": "ready",
            "stage": None,
            "error": None,
            "duration_s": round(duration, 1),
            "storage_path": audio_storage_path(source_id),
        },
    )


def process_lecture(source_id: str, upload_path: Path, title: str) -> None:
    audio = tmp_path(f"{source_id}.opus")
    try:
        db.update_source(source_id, {"stage": "preparing"})
        prepare.prepare_audio(upload_path, audio)
        db.upload_file(audio_storage_path(source_id), audio, "audio/ogg")
        db.update_source(source_id, {"stage": "transcribing"})
        segments, duration = transcribe(audio)
        if not segments:
            raise PrepareError("No speech was found in this recording.")
        _lecture_intelligence(source_id, title, segments, duration)
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)
    finally:
        prepare.cleanup(upload_path, audio)


def refresh_lecture(source_id: str) -> None:
    """Re-run flags, chunks and notes from the stored transcript (after a prompt change; no re-transcription)."""
    source = db.get_source(source_id)
    if source is None or source["type"] != "lecture":
        raise ValueError(f"{source_id} is not a lecture")
    stored = db.download_json(transcript_storage_path(source_id))
    segments: list[Segment] = [{"start": t["start_s"], "end": t["end_s"], "text": t["text"]} for t in stored]
    db.update_source(source_id, {"status": "processing", "error": None})
    try:
        _lecture_intelligence(source_id, source["title"], segments, float(source.get("duration_s") or 0))
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)


def reprocess_lecture(source_id: str) -> None:
    """Re-run transcription, flags, embeddings and notes from the stored audio (no new upload)."""
    source = db.get_source(source_id)
    if source is None or source["type"] != "lecture":
        raise ValueError(f"{source_id} is not a lecture")
    audio = tmp_path(f"{source_id}.reprocess.opus")
    try:
        db.update_source(source_id, {"status": "processing", "stage": "transcribing", "error": None})
        db.download_file(audio_storage_path(source_id), audio)
        segments, duration = transcribe(audio)
        if not segments:
            raise PrepareError("No speech was found in this recording.")
        _lecture_intelligence(source_id, source["title"], segments, duration)
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)
    finally:
        prepare.cleanup(audio)
