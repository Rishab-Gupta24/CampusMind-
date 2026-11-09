"""PDF → [{text, page}] with headers/footers removed and whitespace normalised."""

import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import pymupdf

from app.config import get_settings
from app.ingest.ocr import needs_ocr, render_page, transcribe_image

REPEAT_SHARE = 0.6  # a line on more than 60% of pages is a header or footer
# NUL and other C0 control characters (except tab and newline) appear in some PDFs; Postgres text
# columns reject \x00 (error 22P05), so they are removed before chunking.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(text: str) -> str:
    return _CONTROL.sub("", text)


_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"[ \t ]+")


class PdfPage(TypedDict, total=False):
    text: str
    page: int
    ocr: bool


def _line_key(line: str) -> str:
    """Normalise a line so 'Page 3 of 40' and 'Page 4 of 40' count as the same footer."""
    return _DIGITS.sub("#", line.strip().lower())


def _page_paragraphs(page: pymupdf.Page) -> list[list[str]]:
    """Text blocks of one page, each as a list of cleaned lines, in reading order."""
    paragraphs: list[list[str]] = []
    for block in page.get_text("blocks", sort=True):
        if block[6] != 0:  # 0 = text block; skip images
            continue
        lines = [_SPACES.sub(" ", clean_text(ln)).strip() for ln in block[4].splitlines()]
        lines = [ln for ln in lines if ln]
        if lines:
            paragraphs.append(lines)
    return paragraphs


def load_pdf(path: Path) -> list[PdfPage]:
    with pymupdf.open(path) as doc:
        pages = [_page_paragraphs(page) for page in doc]

    repeated: set[str] = set()
    if len(pages) >= 3:
        counts: Counter[str] = Counter()
        for paras in pages:
            counts.update({_line_key(ln) for para in paras for ln in para})
        repeated = {key for key, n in counts.items() if n / len(pages) > REPEAT_SHARE}

    result: list[PdfPage] = []
    for number, paras in enumerate(pages, start=1):
        kept: list[str] = []
        for para in paras:
            lines = [ln for ln in para if _line_key(ln) not in repeated]
            if lines:
                kept.append(" ".join(lines))
        text = "\n\n".join(kept).strip()
        if text:
            result.append({"text": text, "page": number, "ocr": False})
    return result


def load_pdf_with_ocr(path: Path, on_progress: Callable[[int, int], None] | None = None) -> list[PdfPage]:
    """Text pages as usual; pages without a text layer (scans, handwriting) are read by OCR."""
    settings = get_settings()
    pages = {p["page"]: p for p in load_pdf(path)}
    with pymupdf.open(path) as doc:
        scanned = [i for i in range(doc.page_count) if needs_ocr(doc[i].get_text())]
        if not settings.ocr_enabled:
            scanned = []
        scanned = scanned[: settings.ocr_max_pages]
        for done, index in enumerate(scanned, start=1):
            if on_progress:
                on_progress(done, len(scanned))
            text = clean_text(transcribe_image(render_page(doc, index)))
            if text and text.strip().lower() not in ("[illegible]", ""):
                pages[index + 1] = {"text": text, "page": index + 1, "ocr": True}
    return [pages[n] for n in sorted(pages)]


def page_count(path: Path) -> int:
    with pymupdf.open(path) as doc:
        return doc.page_count
