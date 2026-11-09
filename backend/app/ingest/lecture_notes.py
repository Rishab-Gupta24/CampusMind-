"""Lecture notes (PRD F2): 5-line summary, 4–8 key points, plain-text formulas.

Long transcripts are summarised in parts, then the parts are merged.
"""

import json
import logging
import re
from typing import TypedDict

from app.ingest.transcriber import Segment
from app.llm.base import get_provider
from app.rag.prompts import NOTES_COMBINE_SYSTEM, NOTES_COMBINE_USER, NOTES_SYSTEM, NOTES_USER

log = logging.getLogger(__name__)

PART_WORDS = 2500  # ~3,300 tokens per part keeps prompt + reply inside an 8k context


class Notes(TypedDict):
    summary: str
    key_points: list[str]
    formulas: list[str]


def _parse(raw: str) -> Notes:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}
    summary = data.get("summary") or ""
    if isinstance(summary, list):
        summary = "\n".join(str(s) for s in summary)
    summary = str(summary).strip()
    if summary and "\n" not in summary:
        summary = "\n".join(s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if s.strip())
    return {
        "summary": summary,
        "key_points": [str(p).strip() for p in data.get("key_points") or [] if str(p).strip()][:8],
        "formulas": [str(f).strip() for f in data.get("formulas") or [] if str(f).strip()],
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
