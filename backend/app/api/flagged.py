import uuid

from fastapi import APIRouter

from app import db
from app.api.lectures import flagged_out

router = APIRouter()


@router.get("/api/flagged")
def list_flagged(course_id: uuid.UUID | None = None) -> list[dict[str, object]]:
    """Every flagged moment in a course's ready lectures, newest lecture first, in lecture order."""
    lectures = [r for r in db.list_sources("lecture", str(course_id) if course_id else None) if r["status"] == "ready"]
    notes = db.lecture_notes_for([r["id"] for r in lectures])
    moments: list[dict[str, object]] = []
    for row in sorted(lectures, key=lambda r: (r.get("source_date") or "", r["created_at"]), reverse=True):
        for moment in sorted(notes.get(row["id"], []), key=lambda m: m["start_s"]):
            moments.append(flagged_out(row, moment))
    return moments
