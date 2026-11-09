import uuid
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app import db
from app.ingest import pipeline
from app.ingest.prepare import save_upload

router = APIRouter()


def _document_out(row: db.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "title": row["title"],
        "kind": row["kind"],
        "course_id": row["course_id"],
        "pages": row["pages"],
        "source_date": row["source_date"],
        "status": row["status"],
        "stage": row.get("stage"),
        "error": row["error"],
        "created_at": row["created_at"],
    }


@router.post("/api/documents", status_code=202)
async def upload_document(
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    kind: Annotated[Literal["campus", "handout", "material"], Form()],
    course_id: Annotated[uuid.UUID | None, Form()] = None,
    source_date: Annotated[date | None, Form()] = None,
) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".pdf" and suffix not in pipeline.IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Add a PDF, or a photo or scan (jpg or png) of notes.")

    title = title.strip()
    course = str(course_id) if course_id else None
    fields = {
        "type": "pdf",
        "kind": kind,
        "title": title,
        "course_id": course,
        "source_date": source_date.isoformat() if source_date else None,
        "status": "processing",
        "error": None,
    }
    existing = db.find_document(title, kind, course)
    if existing:
        source_id = existing["id"]
        db.update_source(source_id, fields)
    else:
        source_id = db.insert_source(fields)["id"]

    upload_path = pipeline.tmp_path(f"{source_id}.upload{suffix}")
    try:
        await save_upload(file, upload_path)
    except HTTPException:
        db.update_source(source_id, {"status": "failed", "error": "The file was too large."})
        raise
    background.add_task(pipeline.process_document, source_id, upload_path)
    return {"source_id": source_id, "status": "processing"}


@router.get("/api/documents")
def list_documents() -> list[dict[str, object]]:
    return [_document_out(row) for row in db.list_sources("pdf")]


@router.get("/api/documents/{source_id}")
def get_document(source_id: uuid.UUID) -> dict[str, object]:
    row = db.get_source(str(source_id))
    if row is None or row["type"] != "pdf":
        raise HTTPException(status_code=404, detail="Document not found.")
    url = db.signed_url(row["storage_path"]) if row["storage_path"] and row["status"] == "ready" else None
    return {**_document_out(row), "file_url": url}


@router.delete("/api/documents/{source_id}")
def delete_document(source_id: uuid.UUID) -> dict[str, bool]:
    sid = str(source_id)
    row = db.get_source(sid)
    if row is None or row["type"] != "pdf":
        raise HTTPException(status_code=404, detail="Document not found.")
    db.remove_files([pipeline.pdf_storage_path(sid)])
    db.delete_source(sid)  # chunks cascade
    return {"ok": True}
