"""iCalendar (RFC 5545) feed so students can subscribe from Google, Outlook or Apple Calendar.

Reminders (VALARM) are inside the feed, so the student's own calendar app notifies them even when
CampusMind is closed. Written by hand: the format is small and no extra dependency is needed.
"""

from datetime import UTC, datetime, timedelta

from app.db import Row

PRODID = "-//CampusMind//Campus calendar//EN"
# Assignments and deadlines: 1 day and 2 hours before. Exams and quizzes: 1 day and 1 hour before.
ALARMS = {
    "assignment": ["-P1D", "-PT2H"],
    "deadline": ["-P1D", "-PT2H"],
    "exam": ["-P1D", "-PT1H"],
    "quiz": ["-P1D", "-PT1H"],
    "lab": ["-PT1H"],
}
DEFAULT_LENGTH = {"exam": timedelta(hours=3), "quiz": timedelta(minutes=50), "lab": timedelta(hours=2)}
TYPE_LABEL = {"exam": "Exam", "quiz": "Quiz", "assignment": "Due", "deadline": "Deadline", "lab": "Lab"}


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _fold(line: str) -> str:
    """Lines longer than 75 octets continue on the next line after a space."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not parts else 74):
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def build_ics(events: list[Row], name: str = "CampusMind") -> str:
    now = _stamp(datetime.now(UTC))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
        "X-WR-TIMEZONE:Asia/Dubai",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for e in events:
        due = _utc(e["due_at"])
        kind = e["type"]
        code = (e.get("courses") or {}).get("code")
        summary = f"{TYPE_LABEL.get(kind, 'Event')}: {e['title']}" + (f" ({code})" if code else "")
        lines += ["BEGIN:VEVENT", f"UID:{e['id']}@campusmind", f"DTSTAMP:{now}", f"SUMMARY:{_escape(summary)}"]
        if e.get("all_day"):
            day = datetime.fromisoformat(e["due_at"]).date()
            lines += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
        elif kind in ("assignment", "deadline"):
            # A deadline is a moment: show it as a short block ending at the due time.
            lines += [f"DTSTART:{_stamp(due - timedelta(minutes=30))}", f"DTEND:{_stamp(due)}"]
        else:
            lines += [f"DTSTART:{_stamp(due)}", f"DTEND:{_stamp(due + DEFAULT_LENGTH.get(kind, timedelta(hours=1)))}"]
        details = [e.get("notes") or ""]
        if (e.get("sources") or {}).get("title"):
            details.append(f"Source: {e['sources']['title']}" + (f", p. {e['page']}" if e.get("page") else ""))
        description = "\n".join(d for d in details if d)
        if description:
            lines.append(f"DESCRIPTION:{_escape(description)}")
        if e.get("location"):
            lines.append(f"LOCATION:{_escape(e['location'])}")
        lines.append(f"CATEGORIES:{kind.upper()}")
        for trigger in ALARMS.get(kind, []):
            lines += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escape(summary)}",
                f"TRIGGER:{trigger}",
                "END:VALARM",
            ]
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
