"""Find exam, quiz and deadline dates in handouts and circulars; save them as *suggested* calendar events.

The model only copies dates as written; this module parses them (DD.MM.YY, DD.MM.YYYY, "5 Oct 2023",
FN/AN sessions), so a date is never invented by the model. Students confirm suggestions in the UI.
"""

import logging
import re
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Any

from app import db
from app.llm.base import get_provider
from app.llm.json_utils import parse_json_object
from app.rag.prompts import DEADLINES_SYSTEM, DEADLINES_USER

log = logging.getLogger(__name__)

CAMPUS_TZ = timezone(timedelta(hours=4))  # Dubai, no daylight saving
SESSION_TIMES = {"FN": time(9, 0), "AN": time(14, 0)}  # BITS forenoon / afternoon sessions
DATE_HINT = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|\b\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}\b")
_NUMERIC = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})")
_TEXTUAL = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})")
# Lookarounds keep dates like 28.4.2014 or 14.05.2023 from being read as 4:20 or 14:05.
_CLOCK = re.compile(
    r"(?<![\d.])(\d{1,2})[:.](\d{2})(?!\d|\.\d)\s*(am|pm)?|(?<![\d.])(\d{1,2})\s*(am|pm)\b", re.IGNORECASE
)
MONTHS = {
    m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)
}
TYPES = {"exam", "quiz", "assignment", "lab", "deadline", "other"}


def parse_date(text: str) -> datetime | None:
    """'03.11.23' / '31.10.2023' / '5 Oct 2023' → date (day first, as written in Indian/UAE documents)."""
    m = _NUMERIC.match(text)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        year += 2000 if year < 100 else 0
    else:
        m = _TEXTUAL.match(text)
        if not m:
            return None
        month = MONTHS.get(m.group(2)[:3].lower(), 0)
        day, year = int(m.group(1)), int(m.group(3))
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def parse_time(text: str) -> tuple[time | None, bool]:
    """Returns (time, all_day). FN/AN map to session start times; nothing usable means all day."""
    upper = text.upper()
    for session, start in SESSION_TIMES.items():
        if re.search(rf"\b{session}\b", upper):
            return start, False
    # "3.00 p.m." / "10 a.m." -> "3.00 pm" / "10 am"
    m = _CLOCK.search(re.sub(r"\b([ap])\.\s?m\b\.?", r"\1m", text, flags=re.IGNORECASE))
    if not m:
        return None, True
    if m.group(1):
        hour, minute, ampm = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
    else:
        hour, minute, ampm = int(m.group(4)), 0, m.group(5).lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if not 0 <= hour < 24 or not 0 <= minute < 60:
        return None, True
    return time(hour, minute), False


def to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    day = parse_date(str(item.get("date") or ""))
    title = str(item.get("title") or "").strip()
    if day is None or not title:
        return None
    start, all_day = parse_time(str(item.get("time") or ""))
    due = datetime.combine(day.date(), start or time(9, 0), tzinfo=CAMPUS_TZ)
    kind = str(item.get("type") or "other").lower()
    return {
        "title": title[:120],
        "type": kind if kind in TYPES else "other",
        "due_at": due.isoformat(),
        "all_day": all_day,
        "notes": str(item.get("evidence") or "").strip()[:300] or None,
    }


def _parse_json(raw: str) -> dict[str, Any]:
    return parse_json_object(raw)


def _is_past(due_at: str) -> bool:
    """Old dates (sample letters, last year's handout) are not deadlines worth suggesting."""
    try:
        due = datetime.fromisoformat(due_at)
    except ValueError:
        return True
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    return due < datetime.now(UTC) - timedelta(days=1)


async def extract_events(source_id: str) -> list[dict[str, Any]]:
    """Read pages that contain dates, extract events, store new ones as 'suggested'. Returns stored rows."""
    source = db.get_source(source_id)
    if source is None or source["type"] != "pdf":
        return []
    course = db.course_codes().get(source.get("course_id") or "", "campus-wide")
    pages: dict[int, list[str]] = {}
    for chunk in db.chunks_for(source_id):
        if chunk.get("page") is not None and DATE_HINT.search(chunk["content"]):
            pages.setdefault(chunk["page"], []).append(chunk["content"])

    found: list[dict[str, Any]] = []
    provider = get_provider()
    for page, texts in sorted(pages.items()):
        raw = await provider.generate(
            [
                {"role": "system", "content": DEADLINES_SYSTEM},
                {
                    "role": "user",
                    "content": DEADLINES_USER.format(
                        title=source["title"], course=course, page=page, text="\n".join(texts)
                    ),
                },
            ],
            temperature=0.0,
            max_tokens=700,
            json_mode=True,
        )
        for item in _parse_json(raw).get("events") or []:
            if not isinstance(item, dict):
                continue
            event = to_event(item)
            # The evidence must really be on the page: the model may not invent a date.
            evidence = str(item.get("date") or "")
            if event and evidence and evidence in " ".join(texts) and not _is_past(event["due_at"]):
                found.append({**event, "page": page})

    stored = []
    existing = {(e["title"].lower(), e["due_at"][:10]) for e in db.events_for_source(source_id)}
    for event in found:
        key = (event["title"].lower(), event["due_at"][:10])
        if key in existing:
            continue
        existing.add(key)
        stored.append(
            db.insert_event(
                {**event, "course_id": source.get("course_id"), "source_id": source_id, "status": "suggested"}
            )
        )
    return stored
