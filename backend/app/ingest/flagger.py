"""Flagged by instructor (PRD F6): cue-phrase match, then an LLM confirmation with a one-line reason.

A moment is flagged only when both steps agree (Rules.md §1.6). Cue phrases match on word
boundaries, so "exam" never matches "example".
"""

import json
import logging
import re
from typing import TypedDict

from app.ingest.chunker import Chunk
from app.ingest.transcriber import Segment
from app.llm.base import LLMError, get_provider
from app.rag.prompts import FLAG_CHECK_SYSTEM, FLAG_CHECK_USER

log = logging.getLogger(__name__)

CONTEXT_S = 30.0
MERGE_GAP_S = 10.0  # cues this close to a confirmed moment belong to it

CUE_PHRASES = [
    r"come (?:in|on) (?:the |your )?exams?",
    r"(?:will|would|might|can|could) be asked",
    r"(?:was|were|got) asked",
    r"asked last year",
    r"(?:very |really |most )?important",
    r"note (?:this|that|it) down",
    r"write (?:this|that|it) down",
    r"note this",
    r"remember (?:this|that)",
    r"don'?t forget",
    r"for (?:the )?(?:quiz|quizzes|compre|comprehensive|midsem|mid-?sem|mid semester|exam|exams|test)",
    r"exam question",
    r"must know",
]
_CUES = re.compile(r"\b(?:" + "|".join(CUE_PHRASES) + r")\b", re.IGNORECASE)


class FlaggedMoment(TypedDict):
    start_s: float
    cue_s: float
    end_s: float
    quote: str
    reason: str
    chunk_id: str | None


def find_candidates(segments: list[Segment]) -> list[int]:
    """Indexes of segments that contain a cue phrase."""
    return [i for i, seg in enumerate(segments) if _CUES.search(seg["text"])]


def context_window(segments: list[Segment], index: int) -> str:
    centre = segments[index]
    lines = []
    for i, seg in enumerate(segments):
        if seg["end"] < centre["start"] - CONTEXT_S or seg["start"] > centre["end"] + CONTEXT_S:
            continue
        marker = ">>> " if i == index else "    "
        lines.append(f"{marker}[{seg['start']:.0f}s] {seg['text']}")
    return "\n".join(lines)


def parse_verdict(raw: str) -> tuple[bool, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return False, ""
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return False, ""
    is_flag = data.get("is_flag") is True
    reason = str(data.get("reason") or "").strip().rstrip(".")
    # No flag without a reason.
    return (is_flag and bool(reason)), reason


async def detect(title: str, segments: list[Segment]) -> list[FlaggedMoment]:
    provider = get_provider()
    moments: list[FlaggedMoment] = []
    for index in find_candidates(segments):
        seg = segments[index]
        previous = moments[-1] if moments else None
        if previous is not None and seg["start"] <= previous["end_s"] + MERGE_GAP_S:
            # Same moment continuing ("note this down. This will come in the exam."): extend, don't re-flag.
            if seg["end"] > previous["end_s"]:
                previous["end_s"] = seg["end"]
                previous["quote"] = f"{previous['quote']} {seg['text']}"
            continue
        messages = [
            {"role": "system", "content": FLAG_CHECK_SYSTEM},
            {"role": "user", "content": FLAG_CHECK_USER.format(title=title, window=context_window(segments, index))},
        ]
        try:
            raw = await provider.generate(messages, temperature=0.0, max_tokens=80, json_mode=True)
        except LLMError:
            log.warning("Flag check failed for segment at %.1fs; skipping", seg["start"])
            continue
        is_flag, reason = parse_verdict(raw)
        if not is_flag:
            continue
        # Quote the cue line with the sentence just before it, which usually names the topic.
        start_index = max(0, index - 1)
        quote = " ".join(s["text"] for s in segments[start_index : index + 1])
        moments.append(
            {
                "start_s": segments[start_index]["start"],
                "cue_s": seg["start"],
                "end_s": seg["end"],
                "quote": quote,
                "reason": reason,
                "chunk_id": None,
            }
        )
    return moments


def apply_to_chunks(chunks: list[Chunk], moments: list[FlaggedMoment]) -> dict[str, str]:
    """Link each moment to the chunk containing it. Returns {chunk_id: combined reason}."""
    reasons: dict[str, list[str]] = {}
    for moment in moments:
        cue_time = moment["cue_s"]
        for chunk in chunks:
            if (chunk["start_s"] or 0.0) <= cue_time <= (chunk["end_s"] or 0.0):
                moment["chunk_id"] = chunk["id"]
                reasons.setdefault(chunk["id"], []).append(moment["reason"])
                break
    return {chunk_id: "; ".join(rs) for chunk_id, rs in reasons.items()}
