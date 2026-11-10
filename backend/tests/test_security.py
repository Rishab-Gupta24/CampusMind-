from pathlib import Path

from fastapi.testclient import TestClient

from app.calendar_ics import _escape
from app.ingest.prepare import content_matches
from app.main import app

# Not used as a context manager, so the model warm-up (lifespan) does not run.
client = TestClient(app, base_url="http://localhost:8000")


def test_unsafe_request_without_client_header_is_blocked() -> None:
    res = client.delete("/api/events/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 403
    res = client.post("/api/documents", files={"file": ("x.pdf", b"%PDF-1.4")}, data={"title": "x", "kind": "campus"})
    assert res.status_code == 403


def test_foreign_host_is_rejected() -> None:
    res = client.get("/api/health", headers={"host": "evil.example.com"})
    assert res.status_code == 400


def test_cors_preflight_only_for_the_app() -> None:
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-campusmind"}
    ok = client.options("/api/quiz", headers={"Origin": "http://127.0.0.1:3000", **preflight})
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"
    bad = client.options("/api/quiz", headers={"Origin": "https://evil.example.com", **preflight})
    assert "access-control-allow-origin" not in bad.headers


def test_content_must_match_extension(tmp_path: Path) -> None:
    fake = tmp_path / "notes.pdf"
    fake.write_bytes(b"MZ\x90\x00 not a pdf")
    assert not content_matches(fake, ".pdf")
    real = tmp_path / "real.pdf"
    real.write_bytes(b"%PDF-1.7\n...")
    assert content_matches(real, ".pdf")
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n....")
    assert content_matches(png, ".png")
    assert not content_matches(png, ".jpg")


def test_ics_escape_blocks_line_injection() -> None:
    assert "\r" not in _escape("Quiz\rBEGIN:VEVENT")
    assert "\n" not in _escape("Quiz\nEND:VCALENDAR")
