from datetime import time

from app.calendar_ics import _fold, build_ics
from app.ingest.deadlines import parse_date, parse_time, to_event


def test_parse_dates_day_first() -> None:
    assert parse_date("03.11.23").strftime("%Y-%m-%d") == "2023-11-03"
    assert parse_date("31.10.2023 FN").strftime("%Y-%m-%d") == "2023-10-31"
    assert parse_date("05-01-2026").strftime("%Y-%m-%d") == "2026-01-05"
    assert parse_date("5 Oct 2023").strftime("%Y-%m-%d") == "2023-10-05"
    assert parse_date("TBA") is None
    assert parse_date("31.02.2024") is None


def test_parse_times_and_sessions() -> None:
    assert parse_time("FN") == (time(9, 0), False)
    assert parse_time("03.01.2024 AN") == (time(14, 0), False)
    assert parse_time("8:30 AM to 8:55 AM") == (time(8, 30), False)
    assert parse_time("2 pm") == (time(14, 0), False)
    assert parse_time("6th period") == (None, True)


def test_to_event_uses_campus_time() -> None:
    event = to_event({"title": "Mid-semester exam", "type": "exam", "date": "31.10.2023", "time": "FN"})
    assert event is not None
    assert event["due_at"] == "2023-10-31T09:00:00+04:00"
    assert event["all_day"] is False
    assert to_event({"title": "Quiz", "date": "TBA"}) is None


def test_ics_has_events_alarms_and_folding() -> None:
    events = [
        {
            "id": "e1",
            "title": "Assignment 2, Bayes; part (b)",
            "type": "assignment",
            "due_at": "2026-11-12T23:59:00+04:00",
            "all_day": False,
            "courses": {"code": "MATH F113"},
            "notes": "Submit on LMS",
            "sources": None,
            "page": None,
            "location": None,
        }
    ]
    ics = build_ics(events)
    assert ics.startswith("BEGIN:VCALENDAR\r\n") and ics.endswith("END:VCALENDAR\r\n")
    assert r"SUMMARY:Due: Assignment 2\, Bayes\; part (b) (MATH F113)" in ics
    assert "DTEND:20261112T195900Z" in ics
    assert ics.count("BEGIN:VALARM") == 2 and "TRIGGER:-P1D" in ics
    long_line = "DESCRIPTION:" + "x" * 200
    assert all(len(part.encode()) <= 75 for part in _fold(long_line).split("\r\n"))
