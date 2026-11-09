"""Split loaded text into chunks with deterministic ids: {source_id}_{page|int(start)}_{n}.

PDF: paragraphs within one page, about 300–500 tokens, 15% overlap, never across pages.
Lecture: segments merged into 60–90 s windows, breaking at pauses > 1.5 s where possible.
"""

import re
from typing import TypedDict

from app.ingest.pdf_loader import PdfPage
from app.ingest.transcriber import Segment

# Words are a cheap token proxy (~1.3 tokens per English word): 380 words ≈ 500 tokens.
MAX_WORDS = 380
OVERLAP = 0.15
MIN_WINDOW_S = 60.0
MAX_WINDOW_S = 90.0
PAUSE_S = 1.5

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class Chunk(TypedDict):
    id: str
    content: str
    page: int | None
    start_s: float | None
    end_s: float | None


def _split_long(paragraph: str, max_words: int) -> list[str]:
    """Break an oversized paragraph at sentence ends, falling back to hard word windows."""
    pieces: list[str] = []
    current: list[str] = []
    for sentence in _SENTENCE_END.split(paragraph):
        words = sentence.split()
        if current and len(current) + len(words) > max_words:
            pieces.append(" ".join(current))
            current = []
        while len(words) > max_words:
            pieces.append(" ".join(words[:max_words]))
            words = words[max_words:]
        current.extend(words)
    if current:
        pieces.append(" ".join(current))
    return pieces


def _pack_page(text: str, max_words: int, overlap: float) -> list[str]:
    # Pieces of a long paragraph leave room for the overlap tail carried from the previous chunk.
    piece_words = max(1, int(max_words * (1 - overlap)))
    units: list[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        units.extend(_split_long(para, piece_words) if len(para.split()) > piece_words else [para])

    packed: list[list[str]] = []
    current: list[str] = []
    for unit in units:
        words = unit.split()
        if current and len(current) + len(words) > max_words:
            packed.append(current)
            tail = current[-int(len(current) * overlap) :] if overlap > 0 else []
            current = list(tail) if len(tail) + len(words) <= max_words else []
        current.extend(words)
    if current:
        packed.append(current)
    return [" ".join(words) for words in packed if words]


def chunk_pdf(
    source_id: str, pages: list[PdfPage], max_words: int = MAX_WORDS, overlap: float = OVERLAP
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for n, content in enumerate(_pack_page(page["text"], max_words, overlap)):
            chunks.append(
                {
                    "id": f"{source_id}_{page['page']}_{n}",
                    "content": content,
                    "page": page["page"],
                    "start_s": None,
                    "end_s": None,
                }
            )
    return chunks


def chunk_lecture(source_id: str, segments: list[Segment]) -> list[Chunk]:
    windows: list[list[Segment]] = []
    current: list[Segment] = []
    for i, seg in enumerate(segments):
        current.append(seg)
        duration = seg["end"] - current[0]["start"]
        next_seg = segments[i + 1] if i + 1 < len(segments) else None
        gap = next_seg["start"] - seg["end"] if next_seg else 0.0
        if next_seg is None or duration >= MAX_WINDOW_S or (duration >= MIN_WINDOW_S and gap > PAUSE_S):
            windows.append(current)
            current = []

    chunks: list[Chunk] = []
    for n, window in enumerate(windows):
        content = " ".join(s["text"] for s in window).strip()
        if not content:
            continue
        start = window[0]["start"]
        chunks.append(
            {
                "id": f"{source_id}_{int(start)}_{n}",
                "content": content,
                "page": None,
                "start_s": start,
                "end_s": window[-1]["end"],
            }
        )
    return chunks
