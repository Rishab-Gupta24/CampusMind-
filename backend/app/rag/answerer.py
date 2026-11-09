"""Question → events: gate → visible boosts → LLM stream → citation check → saved answer.

Events (dicts with `event` and JSON-ready `data`): token, sources, not_found, done, error.
"""

import asyncio
import logging
import re
import time
from collections.abc import AsyncIterator
from typing import Any

from app import db
from app.config import get_settings
from app.llm.base import LLMError, get_provider
from app.rag import reranker
from app.rag.embedder import EmbedError, embed_query
from app.rag.priority import apply_boosts, best_raw_score
from app.rag.prompts import NOT_FOUND_MESSAGE, answer_messages
from app.rag.retriever import Passage, Scope, retrieve

log = logging.getLogger(__name__)

Event = dict[str, Any]

LLM_REFUSAL = "The campus sources don't cover this"
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_MAX_HOLD = 40  # longest "[1, 2, 3, 4, 5]"-style marker we wait for before giving up


class CitationFilter:
    """Streams text through, dropping `[n]` markers that don't point at a passage that was sent.

    `[1, 3]` becomes `[1][3]`. Brackets that aren't citations pass through unchanged.
    """

    def __init__(self, valid: int) -> None:
        self.valid = valid
        self.held = ""
        self.cited: set[int] = set()

    def _clean_marker(self, marker: str) -> str:
        match = _CITATION.fullmatch(marker)
        if not match:
            return marker
        numbers = [int(n) for n in re.split(r"\s*,\s*", match.group(1))]
        kept = [n for n in numbers if 1 <= n <= self.valid]
        self.cited.update(kept)
        return "".join(f"[{n}]" for n in kept)

    def feed(self, text: str) -> str:
        out: list[str] = []
        for ch in text:
            if self.held:
                self.held += ch
                if ch == "]":
                    out.append(self._clean_marker(self.held))
                    self.held = ""
                elif len(self.held) > _MAX_HOLD or ch == "\n":
                    out.append(self.held)
                    self.held = ""
            elif ch == "[":
                self.held = ch
            else:
                out.append(ch)
        return "".join(out)

    def flush(self) -> str:
        rest, self.held = self.held, ""
        return rest


def clean_citations(text: str, valid: int) -> tuple[str, set[int]]:
    """Non-streaming version, used by tests and the eval runner."""
    f = CitationFilter(valid)
    cleaned = f.feed(text) + f.flush()
    return cleaned, f.cited


def _source_event(n: int, p: Passage) -> dict[str, Any]:
    return {
        "n": n,
        "title": p["title"],
        "kind": p["kind"],
        "page": p.get("page"),
        "start_s": p.get("start_s"),
        "source_id": p["source_id"],
        "chunk_id": p["chunk_id"],
        "excerpt": p["content"],
        "badges": p.get("badges", []),
        "flag_reason": p.get("flag_reason"),
        "instructor": p.get("instructor"),
    }


MAX_PER_SOURCE = 2
OFFICIAL_KINDS = ("campus", "handout")


def select_passages(boosted: list[Passage], k: int) -> list[Passage]:
    """Top k by final score, at most MAX_PER_SOURCE per source, always keeping the best official passage.

    Every passage here already passed the relevance gate. The rule is visible: official passages carry
    the Official badge, and the prompt tells the model to prefer them over older course material.
    """
    chosen: list[Passage] = []
    per_source: dict[str, int] = {}
    for p in boosted:
        if per_source.get(p["source_id"], 0) >= MAX_PER_SOURCE:
            continue
        chosen.append(p)
        per_source[p["source_id"]] = per_source.get(p["source_id"], 0) + 1
        if len(chosen) == k:
            break
    official = next((p for p in boosted if p.get("kind") in OFFICIAL_KINDS), None)
    if official is not None and official not in chosen:
        if len(chosen) == k:
            chosen.pop()
        chosen.append(official)
    return chosen


async def _find_passages(
    question: str, scope: Scope, course_id: str | None, section_id: str | None, lecture_id: str | None
) -> tuple[list[Passage], float, list[Passage]]:
    settings = get_settings()
    vector = await asyncio.to_thread(embed_query, question)
    candidates = await asyncio.to_thread(
        retrieve, question, vector, scope, course_id, lecture_id, settings.top_k_retrieve
    )
    ranked = await asyncio.to_thread(reranker.rerank, question, candidates)
    best = best_raw_score(ranked)
    # Gate on the raw score first; boosts only re-order what already passed.
    relevant = [p for p in ranked if p["rerank_score"] >= settings.min_relevance]
    boosted = apply_boosts(relevant, section_id)
    return select_passages(boosted, settings.top_k_final), best, ranked


async def answer(
    question: str,
    scope: Scope = "all",
    course_id: str | None = None,
    section_id: str | None = None,
    lecture_id: str | None = None,
    save: bool = True,
) -> AsyncIterator[Event]:
    """`save=False` skips writing answers/unanswered rows (eval runs must not pollute Insights)."""
    question = question.strip()

    async def log_unanswered(best: float) -> None:
        if save:
            await asyncio.to_thread(db.insert_unanswered, question, scope, round(best, 4))

    try:
        passages, best, _ranked = await _find_passages(question, scope, course_id, section_id, lecture_id)
    except EmbedError as exc:
        yield {"event": "error", "data": {"error": str(exc)}}
        return

    if not passages:
        await log_unanswered(best)
        yield {"event": "not_found", "data": {"message": NOT_FOUND_MESSAGE}}
        return

    citations = CitationFilter(valid=len(passages))
    pending = ""  # held until we know the reply isn't the model's own refusal
    decided = False
    full: list[str] = []
    try:
        async for piece in get_provider().stream(answer_messages(question, passages)):
            full.append(piece)
            if decided:
                text = citations.feed(piece)
                if text:
                    yield {"event": "token", "data": {"text": text}}
                continue
            pending += piece
            stripped = pending.lstrip()
            if len(stripped) >= len(LLM_REFUSAL) or not LLM_REFUSAL.startswith(stripped[: len(LLM_REFUSAL)]):
                if stripped.startswith(LLM_REFUSAL):
                    break  # refusal: stop reading, never show it as an answer
                decided = True
                text = citations.feed(pending)
                if text:
                    yield {"event": "token", "data": {"text": text}}
    except LLMError as exc:
        yield {"event": "error", "data": {"error": str(exc)}}
        return

    raw = "".join(full).strip()
    if not decided:
        if raw.startswith(LLM_REFUSAL) or not raw:
            await log_unanswered(best)
            yield {"event": "not_found", "data": {"message": NOT_FOUND_MESSAGE}}
            return
        text = citations.feed(pending)
        if text:
            yield {"event": "token", "data": {"text": text}}
    tail = citations.flush()
    if tail:
        yield {"event": "token", "data": {"text": tail}}

    final_text, cited = clean_citations(raw, len(passages))
    # Every answer shows its sources. If the model forgot to cite, show all passages it was given.
    shown = sorted(cited) or list(range(1, len(passages) + 1))
    sources = [_source_event(n, passages[n - 1]) for n in shown]
    chunk_ids = [passages[n - 1]["chunk_id"] for n in shown]
    answer_id = await asyncio.to_thread(db.insert_answer, question, final_text, chunk_ids, scope) if save else None

    yield {"event": "sources", "data": sources}
    yield {"event": "done", "data": {"answer_id": answer_id, "answer": final_text}}


async def answer_once(question: str, **kwargs: Any) -> dict[str, Any]:
    """Run the whole pipeline without streaming. Used by the eval runner."""
    start = time.perf_counter()
    first_token: float | None = None
    text: list[str] = []
    result: dict[str, Any] = {"not_found": False, "sources": [], "error": None, "best_score": None}
    async for event in answer(question, **kwargs):
        kind = event["event"]
        if kind == "token":
            if first_token is None:
                first_token = time.perf_counter() - start
            text.append(event["data"]["text"])
        elif kind == "sources":
            result["sources"] = event["data"]
        elif kind == "not_found":
            result["not_found"] = True
        elif kind == "error":
            result["error"] = event["data"]["error"]
        elif kind == "done":
            result["answer_id"] = event["data"]["answer_id"]
    result["answer"] = "".join(text)
    result["first_token_s"] = first_token
    result["total_s"] = time.perf_counter() - start
    return result
