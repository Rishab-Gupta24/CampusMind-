import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app import db
from app.ingest import pipeline
from app.ingest.prepare import save_upload

router = APIRouter()

AUDIO_VIDEO_TYPES = {".mp3", ".m4a", ".wav", ".mp4", ".webm", ".ogg", ".opus", ".aac", ".mov"}


def _lecture_out(row: db.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "title": row["title"],
        "course_id": row["course_id"],
        "section_id": row["section_id"],
        "section": (row.get("sections") or {}).get("name"),
        "instructor": row.get("instructors"),
        "source_date": row["source_date"],
        "duration_s": row["duration_s"],
        "status": row["status"],
        "stage": row.get("stage"),
        "error": row["error"],
    }


@router.post("/api/lectures", status_code=202)
async def upload_lecture(
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    course_id: Annotated[uuid.UUID, Form()],
    section_id: Annotated[uuid.UUID, Form()],
    instructor_id: Annotated[uuid.UUID, Form()],
    source_date: Annotated[date, Form()],
) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in AUDIO_VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Upload an audio or video file (mp3, m4a, wav or mp4).")

    row = db.insert_source(
        {
            "type": "lecture",
            "kind": "lecture",
            "title": title.strip(),
            "course_id": str(course_id),
            "section_id": str(section_id),
            "instructor_id": str(instructor_id),
            "source_date": source_date.isoformat(),
            "status": "processing",
        }
    )
    source_id = row["id"]
    upload_path = pipeline.tmp_path(f"{source_id}.upload{suffix}")
    try:
        await save_upload(file, upload_path)
    except HTTPException:
        db.update_source(source_id, {"status": "failed", "error": "The file was too large."})
        raise
    background.add_task(pipeline.process_lecture, source_id, upload_path, row["title"])
    return {"source_id": source_id, "status": "processing"}


@router.get("/api/lectures")
def list_lectures(course_id: uuid.UUID | None = None) -> list[dict[str, object]]:
    return [_lecture_out(row) for row in db.list_sources("lecture", str(course_id) if course_id else None)]


@router.get("/api/lectures/{source_id}")
def get_lecture(source_id: uuid.UUID) -> dict[str, object]:
    sid = str(source_id)
    row = db.get_source(sid)
    if row is None or row["type"] != "lecture":
        raise HTTPException(status_code=404, detail="Lecture not found.")

    detail: dict[str, object] = {
        **_lecture_out(row),
        "transcript": [],
        "summary": "",
        "key_points": [],
        "formulas": [],
        "flagged": [],
        "audio_url": None,
    }
    if row["status"] != "ready":
        return detail

    notes = db.get_lecture_notes(sid) or {}
    moments = notes.get("flagged_moments") or []
    transcript = db.download_json(pipeline.transcript_storage_path(sid))
    for line in transcript:
        line["flagged"] = any(m["start_s"] <= line["start_s"] < m["end_s"] for m in moments)

    detail.update(
        {
            "transcript": transcript,
            "summary": notes.get("summary") or "",
            "key_points": notes.get("key_points") or [],
            "formulas": notes.get("formulas") or [],
            "flagged": [flagged_out(row, m) for m in moments],
            "audio_url": db.signed_url(row["storage_path"]) if row["storage_path"] else None,
        }
    )
    return detail


def flagged_out(row: db.Row, moment: db.Row) -> dict[str, object]:
    return {
        "source_id": row["id"],
        "title": row["title"],
        "source_date": row.get("source_date"),
        "start_s": moment["start_s"],
        "end_s": moment["end_s"],
        "reason": moment["reason"],
        "quote": moment["quote"],
        "instructor": row.get("instructors"),
        "section": (row.get("sections") or {}).get("name"),
    }
