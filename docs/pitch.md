# CampusMind — Pitch

**IDEAVERSE 2026 · Smart Campus, AI Solutions** · BITS Pilani, Dubai Campus

> **One line:** CampusMind is a free AI study assistant that knows your campus rules, your lectures and your past papers. It shows what your instructors flagged as important, tracks every deadline, and proves every answer with its source.

---

## Slide 1 — The problem

Students can't quickly get trustworthy answers from their own campus documents and lectures. They also miss what instructors said was important, and lose track of deadlines.

| Where it lives | What goes wrong |
| --- | --- |
| 60-page regulations, handouts, circulars | Dense PDFs; keyword search fails ("makeup" vs "missed test") |
| Lectures | Spoken once, gone after class |
| "This will come in the exam" | Heard only by whoever was paying attention |
| Exam dates, assignment deadlines | Scattered across handouts and emails; missed |
| Handwritten notes, scanned answer keys | Unsearchable images |
| WhatsApp groups and seniors | Fast, often wrong |

## Slide 2 — The solution

One place for everything a course gives you, searchable in plain language:

- **Ask:** cited answers with tables and properly rendered formulas. Every claim links to a page or lecture timestamp, and off-topic questions are refused honestly.
- **Lectures:** transcript, 5-line summary, key points, formulas, plus **Flagged moments** ("this will come in the exam") with the instructor's reason.
- **Practice:** 5–10 question quizzes on any topic, each labelled with its source, e.g. *"Past paper · 2021-22 Sem II · Mid-semester exam · Q1(a)"*. Plus flashcards with repeat-until-learned.
- **Calendar:** exam and deadline dates are pulled out of handouts automatically. Colours: exams red; assignments move green → yellow → orange as time runs out, and bright red in the last 24 hours. Reminders arrive in the browser and through your phone's own calendar.
- **Handwritten notes:** photos and scans are read by OCR and become searchable, marked "Scanned".
- **Gets smarter with use:** thumbs up/down and unanswered questions show admins exactly which document to add next.

## Slide 3 — How AI solves it

```
PDF / photo / lecture ─► prepare (ffmpeg, PyMuPDF) ─► text (PDF text, OCR, Whisper) ─► chunks ─► embeddings
                                                                                              │
Question ─► hybrid search (meaning + exact terms) ─► reranker ─► relevance gate ─► visible boosts ─► LLM writes cited answer
```

| AI part | Job |
| --- | --- |
| faster-whisper | Lecture audio → timestamped transcript |
| gemma4 vision (local) | Reads scanned pages and handwriting |
| bge-m3 embeddings + Postgres full-text | Finds passages by meaning *and* exact terms ("Quiz-1", "MATH F113") |
| bge-reranker-v2-m3 (GPU) | Picks the best passages; refuses below a measured threshold |
| gemma4 LLM (local) | Writes answers, quizzes, flashcards and notes **only** from retrieved passages |
| LLM + cue phrases | Detects instructor "this will come in the exam" moments, two-step confirmed |

No model training: knowledge lives in the database, so adding a document makes it smarter immediately.

## Slide 4 — Demo (about 3 minutes)

| Time | Step | What judges see |
| --- | --- | --- |
| 0:00 | Hook | "It's 11 pm. Your midsem is in 3 days. What's on it, what did the IC say, and when is everything due?" |
| 0:15 | Pick course | MATH F113 · L1 in the course selector |
| 0:25 | Ask a rule | "What is the weightage of the comprehensive exam?" → table + **Official** chip → open the PDF at page 2 |
| 0:50 | Formula | "Formula for Bayes' theorem" → rendered formula, chip with **Flagged · IC · Your section** |
| 1:10 | Lecture | Flagged tab → click the moment → transcript jumps to 0:40, audio plays |
| 1:30 | Practice | "Give me questions on Bayes' theorem" → quiz with sources, including a real past-paper question labelled with its paper and exam |
| 2:00 | Calendar | Deadlines in green / yellow / red, a date found in the handout, "Add to my calendar" |
| 2:20 | Handwriting | A photo of notes uploaded → "Reading page 1 of 1" → now answerable, marked **Scanned** |
| 2:40 | Trust | Off-topic question → "I couldn't find this" → it appears in **Insights** |
| 2:55 | Close | Free, local AI, every answer proven, works for any university |

## Slide 5 — Gets smarter with use

```
Students ask ─► answered? ── yes ─► thumbs up / down ─┐
                    └─ no ─► logged as unanswered ─────┴─► Insights page ─► admin uploads the missing document ─► knowledge base grows
```

## Slide 6 — Impact

- **Measured:** 15 of 15 test questions answered with the right source, 3 of 3 off-topic questions refused, first words in about 2.5 s on a student laptop.
- **Speed:** a 2-minute lecture is ready in about 30 s; a scanned page is read in about 8 s.
- **Cost:** AED 0, using open-source models and free tiers.
- **Who it helps most:** students who missed class, non-native English speakers, students with hearing difficulties, first-years.

---

## One-line answers for judges

| Question | Answer |
| --- | --- |
| Accuracy? | Answers only from retrieved sources, reranked, refused below a measured threshold; 15/15 on our test set, every citation checked. |
| Why not ChatGPT? | It doesn't know BPDC's rules, your lectures or your past papers, and it can't cite a page or a timestamp. |
| Can it make things up? | It can only cite passages it was given; invalid citations are removed. Past-paper questions show **no** AI-computed answer, because the sources don't contain one. |
| Privacy? | AI runs locally on the laptop; database keys stay on the server; lectures only with the instructor's consent. |
| Cost? | AED 0: open-source models (Ollama, Whisper, bge) and free tiers. |
| Is instructor priority fair? | Every boost is a visible badge (Official, IC, HOD, Flagged, Your section); nothing is hidden. |
| Handwriting accuracy? | Printed text ~99%, clear handwriting ~85% of words; scanned passages carry a badge telling students to check the original page. |
| Scale? | Works for Heriot-Watt or any university: upload their documents and lectures. |

---

## What else we could have added

Features we designed but deliberately left out of the prototype, and why.

### 1. LMS / Moodle sync

Pull deadlines, course materials and handouts straight from the campus LMS instead of uploading them.

| Route | What it gives | What it needs | Effort |
| --- | --- | --- | --- |
| **Moodle calendar export:** each student pastes their personal iCal link (Calendar → Export) | Assignment deadlines, quiz close times, course events, automatically | Nothing from IT; the student's own link | ~2 hours |
| **Moodle Web Services API** (`core_calendar_get_action_events_by_timesort`, `mod_assign_get_assignments`, `core_course_get_contents`), with the student's own token | Deadlines plus course contents, files and handouts | Web services / mobile app access enabled on the campus Moodle | 4–6 hours |
| **Official LTI or admin integration** | Everything, for every student, with instructor control | University IT approval and a data agreement | Weeks |

Why not now: pulling course materials into a shared knowledge base needs instructor consent and IT approval (copyright and privacy). Scraping the LMS is against our own rules.

### 2. More from modern study apps

| Idea | Value | Why it waits |
| --- | --- | --- |
| Audio summaries ("podcast" of a lecture or chapter) | Revise while commuting | Needs a local text-to-speech model; a heavy new dependency |
| YouTube and web-page import | Many courses use video | Transcript download tools raise terms-of-service questions |
| Live lecture note-taking | Notes while the class happens | PRD rules out live transcription; consent needed per class |
| Shared notes and study groups | Learning together | Needs accounts |
| Native mobile app | Reminders and study on the go | The website is responsive; an app needs store releases |

### 3. Platform

| Idea | Value |
| --- | --- |
| BITS email login, roles for students, class reps and faculty | Personal calendars, faculty-only uploads, per-student history |
| Hosted backend with Gemini free tier | Anyone can use it from a phone, not just the demo laptop |
| Server push notifications | Reminders with every tab closed (today: the browser while open, plus the subscribed calendar) |
| Two-way Google / Outlook calendar sync | Personal events next to campus deadlines |
| Spaced repetition across devices | Flashcard progress follows the student |
| Auto-sync of circulars from email | Notices land in the knowledge base the day they're sent |
| On-campus server | Answers never leave the university |
