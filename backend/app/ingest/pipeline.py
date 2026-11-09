"""Runs a whole upload as a background task: prepare → store → load/transcribe → chunk → embed → upsert.

A source ends as `ready`, or `failed` with a short message users can read.
"""

import logging
from pathlib import Path

from app import db
from app.config import get_settings
from app.ingest import prepare
from app.ingest.chunker import Chunk, chunk_lecture, chunk_pdf
from app.ingest.pdf_loader import load_pdf, page_count
from app.ingest.prepare import PrepareError
from app.ingest.transcriber import transcribe
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


def _index(source_id: str, chunks: list[Chunk]) -> None:
    """Replace every chunk of a source. Deterministic ids keep re-uploads from duplicating."""
    vectors = embed_texts([c["content"] for c in chunks])
    rows = [
        {**chunk, "source_id": source_id, "embedding": vector, "flagged": False, "flag_reason": None}
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    db.delete_chunks(source_id)
    db.upsert_chunks(rows)


def _fail(source_id: str, exc: Exception) -> None:
    safe = isinstance(exc, PrepareError | EmbedError)
    if not safe:
        log.exception("Pipeline failed for source %s", source_id)
    db.update_source(source_id, {"status": "failed", "error": str(exc) if safe else GENERIC_FAILURE})


def process_document(source_id: str, upload_path: Path) -> None:
    compressed = tmp_path(f"{source_id}.compressed.pdf")
    try:
        stored = prepare.prepare_pdf(upload_path, compressed)
        pages = load_pdf(stored)
        if not pages:
            raise PrepareError("No text was found in this PDF. Scanned PDFs are not supported yet.")
        db.upload_file(pdf_storage_path(source_id), stored, "application/pdf")
        chunks = chunk_pdf(source_id, pages)
        _index(source_id, chunks)
        db.update_source(
            source_id,
            {
                "status": "ready",
                "error": None,
                "pages": page_count(stored),
                "storage_path": pdf_storage_path(source_id),
            },
        )
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)
    finally:
        prepare.cleanup(upload_path, compressed)


def process_lecture(source_id: str, upload_path: Path) -> None:
    audio = tmp_path(f"{source_id}.opus")
    try:
        prepare.prepare_audio(upload_path, audio)
        db.upload_file(audio_storage_path(source_id), audio, "audio/ogg")
        segments, duration = transcribe(audio)
        if not segments:
            raise PrepareError("No speech was found in this recording.")
        transcript = [{"start_s": s["start"], "end_s": s["end"], "text": s["text"]} for s in segments]
        db.upload_json(transcript_storage_path(source_id), transcript)
        chunks = chunk_lecture(source_id, segments)
        _index(source_id, chunks)
        db.update_source(
            source_id,
            {
                "status": "ready",
                "error": None,
                "duration_s": round(duration, 1),
                "storage_path": audio_storage_path(source_id),
            },
        )
    except Exception as exc:  # noqa: BLE001 — every failure must end as status 'failed'
        _fail(source_id, exc)
    finally:
        prepare.cleanup(upload_path, audio)
