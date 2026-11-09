"""All prompts live here (Rules.md §1.17)."""

from app.rag.retriever import Passage

NOT_FOUND_MESSAGE = "I couldn't find this in the campus sources. Try rephrasing, or check with the academic office."

ANSWER_SYSTEM = """You are CampusMind, a campus assistant for students.

Rules:
- Answer ONLY from the numbered passages the user gives you. Never use outside knowledge about any university, course or rule.
- After every sentence that uses a passage, cite it with its number in square brackets, like [2]. Use only numbers that appear in the passages. Never cite anything else.
- If the passages do not answer the question, reply exactly: "The campus sources don't cover this." and nothing else.
- If a passage is marked Flagged, say that the instructor flagged it as important, and why if a reason is given.
- Passages marked Official (course handouts, campus regulations) state the current rules. Other passages are course material such as past exam papers or slides from earlier semesters. If they disagree, follow the Official passage. When you give a date, weightage or rule taken from course material, say which semester or year it comes from.
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


# ---------- Flagged moments (3.1) ----------

FLAG_CHECK_SYSTEM = """You check lecture transcripts for moments where the instructor tells students something is important for exams or must be remembered.

You get a short transcript window. One line is marked >>> as the candidate.
Decide whether the instructor, at the >>> line, is signalling importance to students (for example "this will come in the exam", "note this down", "this was asked last year", "remember this formula").
Ordinary uses do not count: "an important example of...", "it is important that the function is continuous", or a student asking a question.

Reply with one JSON object only:
{"is_flag": true or false, "reason": "<at most 12 words: what to remember, e.g. Exam hint: Bayes' theorem formula>"}
Use an empty reason when is_flag is false."""

FLAG_CHECK_USER = """Lecture: {title}

Transcript window:
{window}"""


# ---------- Lecture notes (3.2) ----------

NOTES_SYSTEM = """You write study notes from a lecture transcript. Use only what the transcript says.

Reply with one JSON object only:
{"summary": "<exactly 5 short lines separated by \n>", "key_points": ["<4 to 8 points, one sentence each>"], "formulas": ["<each formula said in the lecture, in plain text like P(A|B) = P(B|A) P(A) / P(B); empty list if none>"]}
No LaTeX, no markdown. Write formulas with plain characters."""

NOTES_USER = """Lecture: {title}

Transcript:
{transcript}"""

NOTES_COMBINE_SYSTEM = """You merge partial study notes of one lecture into a single set. Remove duplicates, keep the lecture order.

Reply with one JSON object only, same shape:
{"summary": "<exactly 5 short lines separated by \n>", "key_points": ["<4 to 8 points>"], "formulas": ["<plain-text formulas, no duplicates>"]}"""

NOTES_COMBINE_USER = """Lecture: {title}

Partial notes (JSON, one per part):
{parts}"""
