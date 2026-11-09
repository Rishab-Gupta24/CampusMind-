from collections import defaultdict

from fastapi import APIRouter

from app import db

router = APIRouter()


@router.get("/api/insights")
def insights() -> dict[str, list[dict[str, object]]]:
    """Missing content (unanswered questions, grouped) and answers students rated down."""
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {"question": "", "count": 0, "last_at": ""})
    for row in db.list_unanswered():
        key = " ".join(row["question"].lower().split()).rstrip("?")
        entry = grouped[key]
        entry["count"] = int(entry["count"]) + 1
        if str(row["created_at"]) >= str(entry["last_at"]):
            entry["question"] = row["question"]
            entry["last_at"] = row["created_at"]
    unanswered = sorted(grouped.values(), key=lambda e: (int(e["count"]), str(e["last_at"])), reverse=True)
    return {"unanswered": unanswered, "thumbs_down": db.list_thumbs_down()}
