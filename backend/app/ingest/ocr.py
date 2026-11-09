"""OCR for scanned pages and handwritten notes, using the local vision-capable LLM (gemma4 reads images).

Pages with no text layer are rendered to PNG and transcribed. Output keeps line breaks and writes
maths in LaTeX. Text read this way is marked `ocr` so the UI can show a "Scanned" badge.
"""

import base64
import logging
from pathlib import Path

import httpx
import pymupdf

from app.config import get_settings
from app.rag.prompts import OCR_PROMPT

log = logging.getLogger(__name__)

MIN_TEXT_CHARS = 30  # a page with less selectable text than this is treated as a scan


class OCRError(Exception):
    """OCR failed. The message is safe to show users."""


def needs_ocr(page_text: str) -> bool:
    return len(page_text.strip()) < MIN_TEXT_CHARS


def render_page(doc: pymupdf.Document, index: int) -> bytes:
    return doc[index].get_pixmap(dpi=get_settings().ocr_dpi).tobytes("png")


def transcribe_image(png: bytes) -> str:
    settings = get_settings()
    payload = {
        "model": settings.ocr_model or settings.llm_model,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        # Same num_ctx as answers so the shared model is not reloaded between OCR and questions.
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2000},
        "messages": [{"role": "user", "content": OCR_PROMPT, "images": [base64.b64encode(png).decode()]}],
    }
    try:
        res = httpx.post(f"{settings.ollama_url}/api/chat", json=payload, timeout=300)
        res.raise_for_status()
    except httpx.HTTPError as exc:
        raise OCRError("The model that reads scanned pages is not reachable. Check that Ollama is running.") from exc
    return res.json()["message"]["content"].strip()


def image_to_pdf(image_path: Path, pdf_path: Path) -> Path:
    """Wrap a photo or scan (jpg/png) in a one-page PDF so every document is stored the same way."""
    try:
        with pymupdf.open(image_path) as img:
            pdf_bytes = img.convert_to_pdf()
    except Exception as exc:
        raise OCRError("This image could not be read.") from exc
    pdf_path.write_bytes(pdf_bytes)
    return pdf_path
