import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from app import db
from app.calendar_ics import build_ics
from app.ingest.deadlines import CAMPUS_TZ, extract_events
from app.llm.base import LLMError

router = APIRouter()

EventType = Literal["exam", "quiz", "assignment", "lab", "deadline", "class", "other"]


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    type: EventType
    due_at: datetime
    starts_at: datetime | None = None
    all_day: bool = False
    course_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("due_at", "starts_at")
    @classmethod
    def campus_time(cls, value: datetime | None) -> datetime | None:
        # A time without a zone is campus time (Dubai).
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=CAMPUS_TZ)
        return value


class EventPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    type: EventType | None = None
    due_at: datetime | None = None
    starts_at: datetime | None = None
    all_day: bool | None = None
    status: Literal["confirmed", "suggested"] | None = None
    notes: str | None = Field(default=None, max_length=500)


def _out(row: db.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "title": row["title"],
        "type": row["type"],
        "course_id": row["course_id"],
        "course_code": (row.get("courses") or {}).get("code"),
        "section_id": row["section_id"],
        "starts_at": row["starts_at"],
        "due_at": row["due_at"],
        "all_day": row["all_day"],
        "location": row["location"],
        "notes": row["notes"],
        "source_id": row["source_id"],
        "source_title": (row.get("sources") or {}).get("title"),
        "page": row["page"],
        "status": row["status"],
    }


def _json(fields: dict[str, object]) -> dict[str, object]:
    return {
        k: (v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, uuid.UUID) else v)
        for k, v in fields.items()
    }


@router.get("/api/events")
def list_events(
    course_id: uuid.UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    include_suggested: bool = False,
) -> list[dict[str, object]]:
    rows = db.list_events(
        str(course_id) if course_id else None,
        start.isoformat() if start else None,
        end.isoformat() if end else None,
        include_suggested,
    )
    return [_out(r) for r in rows]


@router.post("/api/events", status_code=201)
def create_event(event: EventIn) -> dict[str, object]:
    if event.starts_at and event.starts_at >= event.due_at:
        raise HTTPException(status_code=422, detail="The start must be before the due date.")
    row = db.insert_event({**_json(event.model_dump()), "status": "confirmed"})
    return _out(db.get_event(row["id"]) or row)


@router.patch("/api/events/{event_id}")
def update_event(event_id: uuid.UUID, patch: EventPatch) -> dict[str, object]:
    fields = _json(patch.model_dump(exclude_unset=True))
    if not fields:
        raise HTTPException(status_code=422, detail="Nothing to change.")
    if db.update_event(str(event_id), fields) is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return _out(db.get_event(str(event_id)) or {})


@router.delete("/api/events/{event_id}")
def delete_event(event_id: uuid.UUID) -> dict[str, bool]:
    db.delete_event(str(event_id))
    return {"ok": True}


@router.post("/api/events/extract/{source_id}")
async def extract(source_id: uuid.UUID) -> list[dict[str, object]]:
    """Find dates in a document and add them as suggested events."""
    try:
        rows = await extract_events(str(source_id))
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [_out(db.get_event(r["id"]) or r) for r in rows]


@router.get("/api/calendar.ics")
def calendar_feed(course_id: uuid.UUID | None = None) -> Response:
    """Subscribe link for Google, Outlook or Apple Calendar, with reminders built in."""
    code = db.course_codes().get(str(course_id)) if course_id else None
    events = db.list_events(str(course_id) if course_id else None)
    body = build_ics(events, name=f"CampusMind · {code}" if code else "CampusMind")
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="campusmind.ics"', "Cache-Control": "no-cache"},
    )
