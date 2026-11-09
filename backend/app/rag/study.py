"""Quiz mode and flashcards (PRD F9, plus ideas from study apps): questions grounded in campus sources.

Every question names where it came from. A question is shown as "from a past paper" only when its
passage really is a past paper; the model's claim alone is never trusted.
"""

import asyncio
import json
import re
from typing import Any, Literal

from app.config import get_settings
from app.llm.base import get_provider
from app.rag import reranker
from app.rag.embedder import embed_query
from app.rag.priority import apply_boosts
from app.rag.prompts import (
    FLASHCARDS_SYSTEM,
    FLASHCARDS_USER,
    QUIZ_SYSTEM,
    QUIZ_USER,
    format_time,
    passage_label,
)
from app.rag.retriever import Passage, retrieve

SourceFilter = Literal["all", "past_papers", "notes"]

MAX_PASSAGES = 8
PASSAGE_WORDS = 260
_PAST_PAPER = re.compile(r"\b(PYQ|past paper|question paper|previous year)\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(20\d{2})\s*[-–/]\s*(\d{2,4})\b")
_SEM = re.compile(r"\bsem(?:ester)?\s*(I{1,2}|1|2)\b", re.IGNORECASE)
_EXAM_NAME = re.compile(r"\b(mid|compre|comprehensive|quiz|test|exam)", re.IGNORECASE)


class StudyError(Exception):
    """Nothing to build a quiz from. The message is safe to show users."""


def is_past_paper(p: Passage) -> bool:
    return p.get("kind") == "material" and bool(_PAST_PAPER.search(p.get("title", "")))


def paper_name(title: str) -> str:
    """'P&S 2021-2022 SEM I PYQ' → '2021-22 Sem I'."""
    parts = []
    year = _YEAR.search(title)
    if year:
        start, end = year.group(1), year.group(2)
        parts.append(f"{start}-{end[-2:]}")
    sem = _SEM.search(title)
    if sem:
        parts.append(f"Sem {'II' if sem.group(1) in ('II', '2') else 'I'}")
    return " ".join(parts) or title


def _trim(text: str, words: int = PASSAGE_WORDS) -> str:
    tokens = text.split()
    return " ".join(tokens[:words]) + (" …" if len(tokens) > words else "")


async def study_passages(
    topic: str,
    course_id: str | None,
    section_id: str | None,
    source_filter: SourceFilter = "all",
    lecture_id: str | None = None,
) -> list[Passage]:
    settings = get_settings()
    vector = await asyncio.to_thread(embed_query, topic)
    candidates = await asyncio.to_thread(
        retrieve, topic, vector, "lectures" if lecture_id else "all", course_id, lecture_id, settings.top_k_retrieve
    )
    if source_filter == "past_papers":
        candidates = [p for p in candidates if is_past_paper(p)]
    elif source_filter == "notes":
        candidates = [p for p in candidates if not is_past_paper(p)]
    ranked = await asyncio.to_thread(reranker.rerank, topic, candidates)
    relevant = apply_boosts([p for p in ranked if p["rerank_score"] >= settings.min_relevance], section_id)
    # Flagged first, then by score; at most 2 passages per source so questions cover more ground.
    relevant.sort(key=lambda p: (not p.get("flagged"), -p["final_score"]))
    chosen: list[Passage] = []
    per_source: dict[str, int] = {}
    for p in relevant:
        if per_source.get(p["source_id"], 0) >= 2:
            continue
        chosen.append(p)
        per_source[p["source_id"]] = per_source.get(p["source_id"], 0) + 1
        if len(chosen) == MAX_PASSAGES:
            break
    if not chosen:
        raise StudyError("CampusMind couldn't find material on this topic. Try the chapter name or a key term.")
    return chosen


def _numbered(passages: list[Passage]) -> str:
    blocks = []
    for n, p in enumerate(passages, start=1):
        tag = "PAST PAPER · " if is_past_paper(p) else ""
        flag = " · Flagged" if p.get("flagged") else ""
        blocks.append(f"[{n}] ({tag}{passage_label(p)}{flag})\n{_trim(p['content'])}")
    return "\n\n".join(blocks)


_LATEX_COMMAND = re.compile(r"(?<!\\)\\(?=[A-Za-z]{2,})")


def _parse_json(raw: str) -> dict[str, Any]:
    # Models write LaTeX like \text or \frac inside JSON strings without escaping the backslash;
    # json.loads would read "\t" as a tab and "\f" as a form feed. Protect backslash commands first.
    raw = _LATEX_COMMAND.sub(r"\\\\", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}


def source_of(p: Passage, exam: str = "", number: str = "") -> dict[str, Any]:
    past = is_past_paper(p)
    if past:
        bits = ["Past paper", paper_name(p["title"])]
        if exam:
            bits.append(exam)
        if number:
            bits.append(number)
        label = " · ".join(bits)
    else:
        label = p["title"]
    if p.get("page") is not None:
        where = f"p. {p['page']}"
    elif p.get("start_s") is not None:
        where = format_time(p["start_s"])
    else:
        where = ""
    return {
        "label": label,
        "where": where,
        "past_paper": past,
        "title": p["title"],
        "kind": p.get("kind"),
        "page": p.get("page"),
        "start_s": p.get("start_s"),
        "source_id": p["source_id"],
        "chunk_id": p["chunk_id"],
        "excerpt": p["content"],
        "badges": p.get("badges", []),
        "flag_reason": p.get("flag_reason"),
        "instructor": p.get("instructor"),
        "ocr": bool(p.get("ocr")),
        "n": 0,
    }


def _clean_question(q: dict[str, Any], passages: list[Passage]) -> dict[str, Any] | None:
    try:
        n = int(q.get("passage", 0))
    except (TypeError, ValueError):
        return None
    if not 1 <= n <= len(passages):
        return None
    passage = passages[n - 1]
    kind = q.get("type")
    text = str(q.get("question") or "").strip()
    if kind not in ("mcq", "fill", "short") or len(text) < 8:
        return None
    past = is_past_paper(passage)
    if past:
        # A past-paper question is shown as printed, with no AI-computed answer: the sources hold no
        # official solutions, and a model solving exam maths on the fly gets it wrong too often.
        exam = str(q.get("exam") or "").strip()
        return {
            "type": "short",
            "question": text,
            "answer": "",
            "explanation": "",
            "answer_available": False,
            "source": source_of(
                passage,
                exam=exam if _EXAM_NAME.search(exam) else "",
                number=str(q.get("question_number") or "").strip()[:12],
            ),
        }
    out: dict[str, Any] = {
        "type": kind,
        "question": text,
        "explanation": str(q.get("explanation") or "").strip(),
    }
    if kind == "mcq":
        options = [str(o).strip() for o in q.get("options") or [] if str(o).strip()]
        try:
            answer = int(q.get("answer"))
        except (TypeError, ValueError):
            return None
        if len(options) != 4 or len(set(options)) != 4 or not 0 <= answer < 4:
            return None
        out["options"] = options
        out["answer"] = answer
    else:
        answer_text = str(q.get("answer") or "").strip()
        if kind == "fill" and (not answer_text or "____" not in text):
            return None
        out["answer"] = answer_text
    out["answer_available"] = bool(out["answer"] != "")
    # Provenance comes from the passage, never from the model's claim.
    out["source"] = source_of(passage)
    return out


async def generate_quiz(
    topic: str,
    course_id: str | None = None,
    section_id: str | None = None,
    count: int = 5,
    source_filter: SourceFilter = "all",
    lecture_id: str | None = None,
    exclude: list[str] | None = None,
) -> dict[str, Any]:
    passages = await study_passages(topic, course_id, section_id, source_filter, lecture_id)
    seen = {e.strip().lower() for e in exclude or []}
    raw = await get_provider().generate(
        [
            {"role": "system", "content": QUIZ_SYSTEM},
            {
                "role": "user",
                "content": QUIZ_USER.format(topic=topic, count=count, passages=_numbered(passages))
                + ("\n\nDo not repeat these questions:\n- " + "\n- ".join(exclude) if exclude else ""),
            },
        ],
        temperature=0.4,
        max_tokens=min(400 * count, 3500),
        json_mode=True,
    )
    questions: list[dict[str, Any]] = []
    for q in _parse_json(raw).get("questions") or []:
        cleaned = _clean_question(q, passages) if isinstance(q, dict) else None
        if cleaned and cleaned["question"].lower() not in seen:
            seen.add(cleaned["question"].lower())
            questions.append(cleaned)
        if len(questions) == count:
            break
    if not questions:
        raise StudyError("CampusMind couldn't write questions from the material it found. Try a narrower topic.")
    return {"topic": topic, "questions": questions}


async def generate_flashcards(
    topic: str,
    course_id: str | None = None,
    section_id: str | None = None,
    count: int = 10,
    lecture_id: str | None = None,
) -> dict[str, Any]:
    try:
        # Notes, handouts and lectures make better cards than raw exam questions.
        passages = await study_passages(topic, course_id, section_id, "notes", lecture_id)
    except StudyError:
        passages = await study_passages(topic, course_id, section_id, "all", lecture_id)
    raw = await get_provider().generate(
        [
            {"role": "system", "content": FLASHCARDS_SYSTEM},
            {"role": "user", "content": FLASHCARDS_USER.format(topic=topic, count=count, passages=_numbered(passages))},
        ],
        temperature=0.3,
        max_tokens=min(150 * count, 2500),
        json_mode=True,
    )
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in _parse_json(raw).get("cards") or []:
        if not isinstance(c, dict):
            continue
        front, back = str(c.get("front") or "").strip(), str(c.get("back") or "").strip()
        try:
            n = int(c.get("passage", 0))
        except (TypeError, ValueError):
            continue
        if not front or not back or not 1 <= n <= len(passages) or front.lower() in seen:
            continue
        seen.add(front.lower())
        cards.append({"front": front, "back": back, "source": source_of(passages[n - 1])})
        if len(cards) == count:
            break
    if not cards:
        raise StudyError("CampusMind couldn't make flashcards from the material it found. Try a narrower topic.")
    return {"topic": topic, "cards": cards}
