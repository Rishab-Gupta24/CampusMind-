"""All prompts live here (Rules.md §1.17)."""

from app.rag.retriever import Passage

NOT_FOUND_MESSAGE = "I couldn't find this in the campus sources. Try rephrasing, or check with the academic office."

ANSWER_SYSTEM = """You are CampusMind, a campus assistant for students.

Rules:
- Answer ONLY from the numbered passages the user gives you. Never use outside knowledge about any university, course or rule.
- After every sentence that uses a passage, cite it with its number in square brackets, like [2]. Use only numbers that appear in the passages. Never cite anything else.
- If the passages do not answer the question, reply exactly: "The campus sources don't cover this." and nothing else.
- If a passage is marked Flagged, say that the instructor flagged it as important, and why if a reason is given.
- When a passage comes from a lecture, you may say who said it (for example "the IC said").
- Be direct and plain. At most 150 words. No headings, no preamble, no closing offer of more help.
- Reply in the same language as the question."""

ANSWER_USER = """Passages:
{passages}

Question: {question}"""


def format_time(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def passage_label(p: Passage) -> str:
    parts = [p["title"]]
    if p.get("page") is not None:
        parts.append(f"p. {p['page']}")
    if p.get("start_s") is not None:
        parts.append(format_time(p["start_s"]))
    instructor = p.get("instructor")
    if instructor:
        role = {"ic": "IC", "hod": "HOD"}.get(instructor["role"], "Instructor")
        parts.append(f"{instructor['name']} ({role})")
    label = " · ".join(parts)
    badges = p.get("badges") or []
    if badges:
        label += " · " + ", ".join(badges)
    if p.get("flagged") and p.get("flag_reason"):
        label += f" · flag reason: {p['flag_reason']}"
    return label


def format_passages(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{n}] ({passage_label(p)})\n{p['content']}" for n, p in enumerate(passages, start=1))


def answer_messages(question: str, passages: list[Passage]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "user", "content": ANSWER_USER.format(passages=format_passages(passages), question=question)},
    ]
