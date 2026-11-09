"""PDF → [{text, page}] with headers/footers removed and whitespace normalised."""

import re
from collections import Counter
from pathlib import Path
from typing import TypedDict

import pymupdf

REPEAT_SHARE = 0.6  # a line on more than 60% of pages is a header or footer
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"[ \t ]+")


class PdfPage(TypedDict):
    text: str
    page: int


def _line_key(line: str) -> str:
    """Normalise a line so 'Page 3 of 40' and 'Page 4 of 40' count as the same footer."""
    return _DIGITS.sub("#", line.strip().lower())


def _page_paragraphs(page: pymupdf.Page) -> list[list[str]]:
    """Text blocks of one page, each as a list of cleaned lines, in reading order."""
    paragraphs: list[list[str]] = []
    for block in page.get_text("blocks", sort=True):
        if block[6] != 0:  # 0 = text block; skip images
            continue
        lines = [_SPACES.sub(" ", ln).strip() for ln in block[4].splitlines()]
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
            result.append({"text": text, "page": number})
    return result


def page_count(path: Path) -> int:
    with pymupdf.open(path) as doc:
        return doc.page_count
