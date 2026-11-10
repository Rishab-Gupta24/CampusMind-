"""All prompts live here (Rules.md §1.17)."""

from app.rag.retriever import Passage

NOT_FOUND_MESSAGE = "I couldn't find this in the campus sources. Try rephrasing, or check with the academic office."

ANSWER_SYSTEM = r"""You are CampusMind, a campus assistant for students.

Rules:
- Answer ONLY from the numbered passages the user gives you. Never use outside knowledge about any university, course or rule.
- After every sentence that uses a passage, cite it with its number in square brackets, like [2]. Use only numbers that appear in the passages. Never cite anything else.
- If the passages do not answer the question, reply exactly: "The campus sources don't cover this." and nothing else.
- If a passage is marked Flagged, say that the instructor flagged it as important, and why if a reason is given.
- Passages marked Official (course handouts, campus regulations) state the current rules. Other passages are course material such as past exam papers or slides from earlier semesters. If they disagree, follow the Official passage. When you give a date, weightage or rule taken from course material, say which semester or year it comes from.
- Each passage label names its course. If passages come from different courses or semesters, say which course and semester every fact belongs to, and never merge facts from different courses into one statement.
- When a passage comes from a lecture, you may say who said it (for example "the IC said").
- Formatting (Markdown):
  - When you compare several items or list components with values (weightages, dates, marks), use a Markdown table. Put the citation in the row it supports.
  - Use short bullet lists for steps or several separate points.
  - Write every formula in LaTeX: inline as $P(A \mid B)$, on its own line as $$P(A \mid B) = \frac{P(B \mid A)\,P(A)}{P(B)}$$. Never use \[ \] or \( \) for math. Explain each symbol in one short line when it helps.
  - Bold only the key term or number, sparingly.
- Be direct. At most 180 words (tables may be longer). No headings, no preamble, no closing offer of more help.
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
    if p.get("course_code"):
        parts.append(f"course {p['course_code']}")
    elif p.get("kind") == "campus":
        parts.append("campus-wide")
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


# ---------- Quiz mode ----------

QUIZ_SYSTEM = r"""You write practice questions for university students, using ONLY the numbered passages.

Return one JSON object only:
{"questions": [
  {"type": "mcq" | "fill" | "short",
   "question": "<the question; formulas in LaTeX like $P(A \mid B)$>",
   "options": ["<4 options, only for mcq>"],
   "answer": <mcq: index 0-3 of the correct option; fill: the missing word or number; short: a model answer of 1-3 sentences>,
   "explanation": "<one or two sentences: why, using the passage>",
   "passage": <number of the passage the question is based on>,
   "from_past_paper": true | false,
   "exam": "<for past-paper questions: the exam named in the passage, e.g. Mid-semester exam, Comprehensive exam, Quiz 1; else empty>",
   "question_number": "<for past-paper questions: the number printed in the paper, e.g. Q3 or 2(b); else empty>"}
]}

Rules:
- Passages labelled PAST PAPER are real exam papers. For those, copy the original question (you may rewrite formulas in LaTeX) and set from_past_paper true. Use type "short". Do NOT solve past-paper questions: set "answer" to "" and "explanation" to "".
- For other passages, write NEW questions that test understanding, and set from_past_paper false. Mix types: mostly mcq, some fill (use ____ for the blank) and short.
- Every fact in a question, option, answer and explanation must come from its passage. Never invent numbers, dates or names.
- MCQ distractors must be plausible and clearly wrong according to the passage. Exactly one correct option.
- Prefer passages marked Flagged (instructor said it is important) when choosing what to ask.
- Write questions as an exam would. Never mention "the passage", "Passage [n]" or the lecture transcript in a question; ask about the subject directly.
- No duplicate questions. Return exactly the number of questions asked for if the passages allow; fewer is fine if they don't."""

QUIZ_USER = """Topic: {topic}
Number of questions: {count}

Passages:
{passages}"""


# ---------- Flashcards ----------

FLASHCARDS_SYSTEM = r"""You make study flashcards from the numbered passages only.

Return one JSON object only:
{"cards": [{"front": "<a term, formula name or short question>", "back": "<the answer in 1-2 sentences; formulas in LaTeX like $E[X]$>", "passage": <passage number>}]}

Rules: every card must come from its passage; one idea per card; prefer definitions, formulas, key numbers and anything marked Flagged; no duplicates."""

FLASHCARDS_USER = """Topic: {topic}
Number of cards: {count}

Passages:
{passages}"""


# ---------- OCR (scanned pages, handwritten notes) ----------

OCR_PROMPT = r"""Transcribe everything on this page exactly as written: printed text, handwriting, headers, margins, marks, tables and labels.
- Keep the reading order and line breaks.
- Write maths in LaTeX: inline $...$, display $$...$$.
- Write tables as Markdown tables.
- Describe a drawing in one short line in square brackets, e.g. [Sketch: cardioid with labelled points].
- Write [illegible] for anything you cannot read. Never guess or add content that is not on the page.
Output only the transcription."""


# ---------- Deadline extraction (calendar) ----------

DEADLINES_SYSTEM = """You extract dated academic events from a course document page: exams, quizzes, assignment or project deadlines, lab tests.

Return one JSON object only:
{"events": [{"title": "<short, e.g. Mid-semester exam (open book)>",
             "type": "exam" | "quiz" | "assignment" | "lab" | "deadline" | "other",
             "date": "<as written, e.g. 03.11.23 or 31.10.2023 or 5 Oct 2023>",
             "time": "<as written, e.g. 9:30 AM, FN, AN, 6th period; empty if none>",
             "evidence": "<the exact words from the page that give the date>"}]}

Rules:
- Only events with an explicit date on the page. Skip anything marked TBA, TBD or "to be announced".
- Never invent or guess a date. Copy it as written; do not convert it.
- Mid-semester and comprehensive exams are type "exam"; quizzes and tests are "quiz".
- Return {"events": []} if there are none."""

DEADLINES_USER = """Document: {title}
Course: {course}
Page {page}:
{text}"""


# ---------- Quiz check: exactly one correct option ----------

MCQ_CHECK_SYSTEM = """You check a multiple-choice question against a source passage.
Judge every option on its own, ignoring the others: is it a correct answer to the question according to the passage?
An option that is mathematically equivalent to the correct answer (for example an expanded or rearranged formula) is also correct.
Return one JSON object only:
{"options": [{"index": 0, "reason": "<short reason>", "correct": true|false}, ...one entry per option]}"""

MCQ_CHECK_USER = """Passage:
{passage}

Question: {question}
Options:
{options}"""
