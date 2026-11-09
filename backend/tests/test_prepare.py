import asyncio
import io
from pathlib import Path

import pymupdf
import pytest
from fastapi import HTTPException, UploadFile

from app.config import Settings
from app.ingest import prepare


@pytest.fixture
def small_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(max_upload_mb=1, pdf_compress_over_mb=0)
    monkeypatch.setattr(prepare, "get_settings", lambda: settings)


def _uncompressed_pdf(path: Path, pages: int = 20) -> None:
    doc = pymupdf.open()
    filler = ("repeated filler text for compression " * 20 + "\n") * 40
    for _ in range(pages):
        page = doc.new_page()
        page.insert_textbox(page.rect + (20, 20, -20, -20), filler, fontsize=4)
    doc.save(path, garbage=0, deflate=False)


def test_check_size_rejects_over_limit(small_limits: None) -> None:
    prepare.check_size(1024 * 1024)
    with pytest.raises(HTTPException) as err:
        prepare.check_size(1024 * 1024 + 1)
    assert err.value.status_code == 413
    assert "over 1 MB" in err.value.detail


def test_save_upload_stops_and_cleans_up(small_limits: None, tmp_path: Path) -> None:
    upload = UploadFile(io.BytesIO(b"x" * (2 * 1024 * 1024)), filename="big.mp3")
    dest = tmp_path / "big.mp3"
    with pytest.raises(HTTPException):
        asyncio.run(prepare.save_upload(upload, dest))
    assert not dest.exists()


def test_prepare_pdf_compresses_large_file(small_limits: None, tmp_path: Path) -> None:
    src = tmp_path / "in.pdf"
    _uncompressed_pdf(src)
    out = prepare.prepare_pdf(src, tmp_path / "out.pdf")
    assert out == tmp_path / "out.pdf"
    assert out.stat().st_size < src.stat().st_size * 0.8


def test_prepare_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"not a pdf at all")
    with pytest.raises(prepare.PrepareError):
        prepare.prepare_pdf(fake, tmp_path / "out.pdf")
