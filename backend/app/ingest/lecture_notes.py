"""Lecture notes (PRD F2): 5-line summary, 4–8 key points, plain-text formulas.

Long transcripts are summarised in parts, then the parts are merged.
"""

import json
import logging
import re
from typing import TypedDict

from app.ingest.transcriber import Segment
from app.llm.base import get_provider
from app.llm.json_utils import parse_json_object
from app.rag.prompts import NOTES_COMBINE_SYSTEM, NOTES_COMBINE_USER, NOTES_SYSTEM, NOTES_USER

log = logging.getLogger(__name__)

PART_WORDS = 2500  # ~3,300 tokens per part keeps prompt + reply inside an 8k context


class Notes(TypedDict):
    summary: str
    key_points: list[str]
    formulas: list[str]


# The model sometimes spells probability operators as words inside LaTeX: P(A \text{ given } B).
_WORD_OPERATORS = {"given": r"\mid", "and": r"\cap", "or": r"\cup"}
_WORD_OPERATOR = re.compile(r"\s*\\(?:text|mathrm|textrm)\{\s*(given|and|or)\s*\}\s*")


def symbol_operators(text: str) -> str:
    r"""P(A \text{ given } B) -> P(A \mid B); "and" -> \cap, "or" -> \cup. Plain prose is untouched."""
    return _WORD_OPERATOR.sub(lambda m: " " + _WORD_OPERATORS[m.group(1)] + " ", text)


def _parse(raw: str) -> Notes:
    data = parse_json_object(raw)
    summary = data.get("summary") or ""
    if isinstance(summary, list):
        summary = "\n".join(str(s) for s in summary)
    summary = str(summary).strip()
    if summary and "\n" not in summary:
        summary = "\n".join(s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if s.strip())
    return {
        "summary": symbol_operators(summary),
        "key_points": [symbol_operators(str(p).strip()) for p in data.get("key_points") or [] if str(p).strip()][:8],
        "formulas": [symbol_operators(str(f).strip()) for f in data.get("formulas") or [] if str(f).strip()],
    }


def split_parts(segments: list[Segment], part_words: int = PART_WORDS) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    words = 0
    for seg in segments:
        current.append(seg["text"])
        words += len(seg["text"].split())
        if words >= part_words:
            parts.append(" ".join(current))
            current, words = [], 0
    if current:
        parts.append(" ".join(current))
    return parts


async def write_notes(title: str, segments: list[Segment]) -> Notes:
    provider = get_provider()
    parts = split_parts(segments)
    partial: list[Notes] = []
    for part in parts:
        raw = await provider.generate(
            [
                {"role": "system", "content": NOTES_SYSTEM},
                {"role": "user", "content": NOTES_USER.format(title=title, transcript=part)},
            ],
            temperature=0.2,
            max_tokens=900,
            json_mode=True,
        )
        partial.append(_parse(raw))
    if len(partial) == 1:
        return partial[0]
    raw = await provider.generate(
        [
            {"role": "system", "content": NOTES_COMBINE_SYSTEM},
            {
                "role": "user",
                "content": NOTES_COMBINE_USER.format(title=title, parts=json.dumps(partial, ensure_ascii=False)),
            },
        ],
        temperature=0.2,
        max_tokens=900,
        json_mode=True,
    )
    return _parse(raw)
