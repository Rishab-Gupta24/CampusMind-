"""Upload preparation: size checks, ffmpeg audio conversion, PDF compression.

Audio/video always becomes mono 16 kHz Opus (Architecture.md §10). No custom codecs (Rules.md §2.12).
"""

import shutil
import subprocess
from pathlib import Path

import pymupdf
from fastapi import HTTPException, UploadFile

from app.config import get_settings

READ_CHUNK = 1024 * 1024  # 1 MB


class PrepareError(Exception):
    """A preparation step failed. The message is safe to show users."""


def max_bytes() -> int:
    return get_settings().max_upload_mb * 1024 * 1024


def check_size(size_bytes: int) -> None:
    """Raise 413 when a file is over MAX_UPLOAD_MB."""
    limit = get_settings().max_upload_mb
    if size_bytes > limit * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"This file is over {limit} MB. Upload a shorter recording or audio only.",
        )


async def save_upload(upload: UploadFile, dest: Path) -> int:
    """Stream an upload to disk, stopping as soon as it passes the size limit. Returns the size in bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with dest.open("wb") as out:
            while chunk := await upload.read(READ_CHUNK):
                written += len(chunk)
                check_size(written)
                out.write(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return written


def ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise PrepareError("ffmpeg is not installed on the server.")
    return path


def prepare_audio(in_path: Path, out_path: Path) -> Path:
    """Convert any audio/video file to mono 16 kHz Opus, dropping video."""
    bitrate = get_settings().audio_bitrate
    cmd = [
        ffmpeg_path(),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(in_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libopus",
        "-b:a",
        bitrate,
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=1800)
    except subprocess.CalledProcessError as exc:
        out_path.unlink(missing_ok=True)
        raise PrepareError("This file could not be read as audio or video.") from exc
    except subprocess.TimeoutExpired as exc:
        out_path.unlink(missing_ok=True)
        raise PrepareError("Converting this recording took too long.") from exc
    return out_path


def prepare_pdf(in_path: Path, out_path: Path) -> Path:
    """Return a PDF path to store: compressed copy when over PDF_COMPRESS_OVER_MB, otherwise the original."""
    try:
        with pymupdf.open(in_path) as doc:
            if not doc.is_pdf:
                raise PrepareError("This file is not a PDF.")
            if doc.needs_pass:
                raise PrepareError("This PDF is password protected.")
            threshold = get_settings().pdf_compress_over_mb * 1024 * 1024
            if in_path.stat().st_size <= threshold:
                return in_path
            doc.save(out_path, garbage=4, deflate=True)
    except PrepareError:
        raise
    except Exception as exc:
        raise PrepareError("This file could not be opened as a PDF.") from exc
    if out_path.stat().st_size >= in_path.stat().st_size:
        out_path.unlink(missing_ok=True)
        return in_path
    return out_path


def cleanup(*paths: Path | None) -> None:
    for path in paths:
        if path is not None:
            path.unlink(missing_ok=True)
