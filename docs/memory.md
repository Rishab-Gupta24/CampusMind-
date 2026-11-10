# CampusMind — Project Memory

The project's long-term memory. **Read this first in every session.** Add to it whenever a decision is made, something changes, a bug is found, or eval runs. Newest entries at the top of each table. One or two lines per entry.

---

## 1. Project context (keep current)

- **What:** CampusMind — AI assistant answering student questions from campus PDFs and lecture recordings, always with sources, showing who said it and what instructors flagged as important. See `PRD.md`.
- **Why:** IDEAVERSE 2026 ideathon (GDGoC BPDC × GDG HWUD × IEI). Theme: *Smart Campus, AI Solutions*. Team of 2–4.
- **Deadlines:** Round 1 + shortlisting (top 10) → **10 Nov 2026** · Final pitch → **11 Nov 2026**.
- **Judging needs:** one clear student problem, how AI helps, a **working prototype**.
- **Constraint:** AED 0 → local open-source models (Ollama) + Supabase free tier.
- **Current phase:** Phases 0–5 plus P1 features built and browser-tested: rich answers (tables, LaTeX), quiz mode + flashcards, OCR for scans/handwriting, calendar with deadline extraction, colours, subscribe feed and reminders. Eval 15/15 + 3/3. Pitch draft in `docs/pitch.md`. Next: Phase D real data, Phase 6 readiness.
- **Demo machine:** this laptop — Ryzen 9 8940HX, 16 GB RAM, RTX 5050 Laptop 8 GB → `LLM_MODEL=gemma4:e4b` (verified with `ollama pull`).
- **GitHub repo:** https://github.com/Rishab-Gupta24/CampusMind-
- **Supabase project:** `campusmind`, ref `apqaojhsbhvapllcyqto`, region ap-south-1 (Mumbai), free tier.

## 2. Decisions log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-11-10 | Textbooks removed from the KB for Round 1; re-add only after hybrid_search uses indexes | With 12 textbooks (19.7k of 24.5k chunks) the exact-scan hybrid_search took 1–5.5 s and unscoped queries hit the 8 s PostgREST timeout |
| 2026-11-10 | KB budget: stop bulk ingest at ~24k chunks / ~400 MB DB | Free tier: 500 MB DB (read-only when full), 1 GB storage, 50 MB per stored file; ~16 KB per chunk |
| 2026-11-10 | Installable app (PWA): `app/manifest.ts`, icons in `public/icons`, `public/sw.js` (offline page + system notifications; caches nothing else), registered only in production builds | 'Make this app': own window and icon, notifications through the service worker |
| 2026-11-10 | One-click launcher `CampusMind.bat` → `scripts/start.ps1` (starts only what isn't running; Ollama with 2 model slots; production Next build) + `CampusMind-stop.bat` | Demo laptop: one double-click, no terminals |
| 2026-11-10 | On backend start, sources still 'processing' are marked failed ('interrupted, upload again') | Background uploads die with the process; they stayed 'processing' forever |
| 2026-11-10 | Quiz MCQs get a second check (model lists every correct option); kept only if exactly the marked one is correct | Two-correct-option questions seen in testing |
| 2026-11-10 | Answers may use Markdown tables, lists and LaTeX (`$…$`, `$$…$$`), rendered with react-markdown + remark-gfm + remark-math + rehype-katex + katex | User request: tables and Gemini-style formulas. New libs logged here per Rules §3 |
| 2026-11-10 | Citation filter ignores brackets inside `$…$`/`$$…$$` | Intervals like $[0, 1]$ must not be read as citations |
| 2026-11-10 | Passage labels name the course; prompt says never merge facts from different courses | Mixed MATH/PHY/past-paper facts in one sentence (user screenshot) |
| 2026-11-10 | Question naming one course code with no course selected → search that course; naming a different course than the selected one → search all | 'Compare MATH F113 and PHY F111' was refused with MATH selected; PHY handout dropped out of the top 40 once ~300 PDFs were ingested |
| 2026-11-10 | Quiz mode (`/api/quiz`, Practice page): 5–10 questions (MCQ, fill-in, short), each with its source; 'Past paper' label only when the passage really is a past paper (`material` + PYQ in title) | User request; provenance never comes from the model's claim |
| 2026-11-10 | Past-paper questions show the original question and **no AI-computed answer** | Test run: the model 'solved' a probability as 5/3. Sources hold no official solutions |
| 2026-11-10 | Flashcards (`/api/flashcards`): notes/handouts/lectures first; Again / Got it queue stored in localStorage | Idea from turbo.ai's public feature list; adapted, not copied |
| 2026-11-10 | 'Give me questions on X' in Ask → `quiz` SSE event → 'Start quiz' card | Ask refused these as lookups (user screenshot) |
| 2026-11-10 | OCR via gemma4 vision (already loaded; no new model): pages with < 30 chars of text, 150 dpi, max 80 pages; chunks marked `ocr` → 'Scanned' badge; jpg/png/webp uploads wrapped into PDF | Test on a real scanned answer key: ~8 s/page, printed ~99%, handwriting ~85%, tables/diagrams weaker, one header block skipped → prompt says transcribe everything |
| 2026-11-10 | Calendar: `events` table (migration 0010); dates extracted from handouts/circulars as **suggested** events (model copies dates as written; Python parses DD.MM.YY, FN = 09:00, AN = 14:00 Dubai; the date must appear on the page) | Never invent dates; the student confirms |
| 2026-11-10 | Urgency colours: exams/quizzes red; assignments green (> 50% of the window left) → yellow (> 25%) → orange → bright red (< 24 h); without an opening date: > 7 d green, > 3 d yellow. Always with a text label | User spec; design.md exception §3a |
| 2026-11-10 | Notifications: ICS feed (`/api/calendar.ics`) with reminders (deadlines −1 d / −2 h, exams −1 d / −1 h) + browser notifications while CampusMind is open | Works with the app closed through the phone's calendar; server push needs hosting + 2 new deps (future scope) |
| 2026-11-10 | Moodle/LMS sync not built; documented in `docs/pitch.md` 'What else we could have added' | User decision; materials need consent / IT approval |
| 2026-11-10 | Demo calendar events titled 'Demo: …' (6 events, MATH F113) | Show the colour range in the pitch; delete or replace with real dates |
| 2026-11-09 | Frontend talks to the real API only (mock mode removed); `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` | Backend was ready before the UI; one code path to test |
| 2026-11-09 | Answer text rendered by a small citation renderer (`AnswerText`), not `react-markdown` | Answers are short plain text; avoids a dependency |
| 2026-11-09 | Citations renumbered 1..k for display (backend keeps passage numbers) | Model may cite only passage 5; showing "5" alone looks broken |
| 2026-11-09 | Chips show max 3 badges + "+n"; source panel shows every badge | design.md §7.2 limit vs Rules §1.4 "every boost visible" |
| 2026-11-09 | `sources.stage` column (migration `0008`) drives "Preparing → Transcribing → Finding important moments → Ready" | Upload card needs real progress, not a fake timer |
| 2026-11-09 | Popovers/panels use `.glass-strong` (97% surface) | Nested inside the glass nav, backdrop blur can't reach the page, so text behind showed through |
| 2026-11-09 | Phone tables: secondary columns fold into a sub-line under the title (`max-sm:hidden`) | A wide table (even in `overflow-x-auto`) widened Chrome's mobile layout viewport to 618 px |
| 2026-11-09 | Insights lives as a tab on Sources (no separate `/insights` route) | design.md §7.7 |
| 2026-11-09 | New source kind `material` (past papers, slides, notes, manuals): searchable, **no Official badge/boost**; 17 existing PYQ/slide/notes/manual uploads reclassified by title (migration `0007`) | PYQ cover pages stated old weightages/dates and outranked the current handout, while wrongly wearing "Official" |
| 2026-11-09 | Final 5 passages: max 2 per source, and the best gate-passing Official passage is always included; prompt says Official wins over older material and to name the semester for dates from material | Visible rule (badge + prompt), fixed 3 eval misses; boosts alone (0.04) can't close a 0.3 rerank gap |
| 2026-11-09 | `MIN_RELEVANCE` 0.3 → **0.02**; `TOP_K_RETRIEVE` 20 → **40** | Eval: off-topic questions score ≤ 0.004, hard-but-relevant (garbled tables) 0.04+; LLM's own "sources don't cover this" is a second gate. 40 candidates cost ~0.3 s more on GPU |
| 2026-11-09 | Reranker reads `title · instructor (role)` + chunk text | "What did the IC say…" scored 0.21 → 0.84 |
| 2026-11-09 | `hybrid_search`: full-text terms ORed (was AND via websearch_to_tsquery) + exact vector scan on a materialized candidate set (migration `0006`) | Natural questions matched 0 chunks with AND; exact scan is cheap at campus scale and can't drop filtered rows |
| 2026-11-09 | `hybrid_search` gets `filter_source` (migration `0004`) | "Ask this lecture" |
| 2026-11-09 | Reranker on GPU: CUDA build of torch (`2.14.1+cu130`), fp16 | CPU took 17 s for 20 passages; GPU 0.3 s. README has the install line; CPU still works (slow) |
| 2026-11-09 | gemma4 called with `think: false` and a fixed `num_ctx: 8192` everywhere (incl. warm-up) | Thinking delays first token; any different num_ctx forces a 25 s model reload |
| 2026-11-09 | Ollama needs `OLLAMA_MAX_LOADED_MODELS=2` (user env had 1) | Each question uses bge-m3 then gemma; with 1 slot they swap and gemma reloads every question |
| 2026-11-09 | Flagged moments stored exactly in `lecture_notes.flagged_moments` (migration `0005`); chunks also get `flagged` + `flag_reason`; cues within 10 s of a confirmed moment extend it | A 60–90 s chunk can hold several moments; precise timestamps for the Flagged tab |
| 2026-11-09 | SSE payloads are JSON (`token {text}`, `not_found {message}`, `done {answer_id, answer}`); invalid `[n]` stripped while streaming; model's own refusal held back and turned into `not_found` | UI never shows an invented citation or a refusal dressed as an answer |
| 2026-11-09 | Eval runs use `save=False` (no answers/unanswered rows) | Keeps the Insights page clean |
| 2026-11-09 | Whisper gets audio decoded by the ffmpeg binary (numpy samples), not PyAV | Installed faster-whisper and av versions are incompatible; ffmpeg is already required |
| 2026-11-09 | Re-upload identity for PDFs = same title + kind + course → reuses the source id | F3 "re-upload replaces"; deterministic chunk ids then overwrite |
| 2026-11-09 | Lecture transcript stored in Storage `transcripts/{id}.json` | `lecture_notes` has no transcript column; keeps rows small |
| 2026-11-09 | Chunk size measured in words (≤ 380 words ≈ 500 tokens); long paragraphs split at 85% so the 15% overlap fits | No tokenizer dependency |
| 2026-11-09 | Accept extra audio types (webm, ogg, opus, aac, mov) besides mp3/m4a/wav/mp4 | ffmpeg converts them all; phones record in these |
| 2026-11-09 | Next.js 16 + Tailwind v4 (create-next-app defaults); added `lucide-react`, `clsx` | Current versions; both libs approved |
| 2026-11-09 | Python 3.12 instead of 3.11 | Already installed; 3.15 too new for faster-whisper/torch wheels; 3.12 works with every approved lib |
| 2026-11-09 | Seed uses fictional names (Dr. Asha Demo, etc.) | No permission yet for real instructor names |
| 2026-11-09 | `vector` extension left in `public` schema (advisor WARN) | Matches Architecture SQL; low risk while RLS blocks public access |
| 2026-11-09 | `hybrid_search` gets `set search_path = public`; bucket created in `0003_storage.sql` | Advisor best practice; every Supabase change lives in migrations |
| 2026-11-09 | Design skill not installed; `design.md` followed directly | Owner's choice |
| 2026-11-09 | Upload prep with ffmpeg (audio → mono 16 kHz Opus 24 kbps) and PyMuPDF (PDF > 20 MB); 200 MB cap; no custom compressor | Small storage (~10 MB per lecture hour), faster Whisper; building a codec is out of scope |
| 2026-11-09 | Feedback loop: thumbs up/down, unanswered-question log, Insights page | System improves through usage without training |
| 2026-11-09 | "Flagged by instructor": cue-phrase match + LLM confirmation with a reason | Surfaces exam hints; two steps limit false flags |
| 2026-11-09 | Instructor priority is **visible** (badges: Official, IC, HOD, Flagged, Your section), not secret; small config boosts after reranking; gate uses raw score | Keeps answers trustworthy; IC usually sets BITS exams |
| 2026-11-09 | Course → section selector; lectures tagged with instructor and role (ic / hod / instructor) | Students prefer their own instructor's explanation |
| 2026-11-09 | Knowledge base moves online to **Supabase** (Postgres + pgvector + Storage); hybrid search in one SQL function (pgvector + full-text, RRF); Chroma and rank-bm25 dropped | Shared across students, free, one place for vectors, metadata and feedback |
| 2026-11-09 | Only the backend talks to Supabase (service key); RLS on, no public policies | No login yet; protects the database |
| 2026-11-09 | GitHub for code only, not as a database | GitHub can't serve queries; 100 MB file limit |
| 2026-11-09 | Local LLM via Ollama is default; Gemini free tier only as P1 switch for multi-user | AED 0 and private; online answering needs a hosted model |
| 2026-11-09 | No model training; knowledge in the database, LLM writes answers from retrieved passages | Faster, cheaper, accurate, citable |
| 2026-11-09 | Reranker `bge-reranker-v2-m3`; embeddings `bge-m3` (1024-dim); faster-whisper `small` | Accuracy, multilingual, free |
| 2026-11-09 | FastAPI backend; Next.js + Tailwind frontend; no LangChain / LlamaIndex | Simple, debuggable; design needs Next.js |
| 2026-11-09 | Design: minimal, plain colours, no gradients, liquid glass only on navigation and controls | Avoid "vibecoded" look |
| 2026-11-09 | Combine docs Q&A ("Campus Copilot") and lecture notes ("Lecture Buddy") into CampusMind | Same RAG engine; one problem: scattered campus knowledge |

## 3. Changes log

| Date | Change | Files |
| --- | --- | --- |
| 2026-11-10 | Bulk ingest from the shared BITS Materials Drive (1st year only): 499 files downloaded, 305 text PDFs ready; 165 scanned skipped (OCR off for the run), 17 duplicates of the zip test set. KB now **321 ready docs, 4,905 chunks, DB 317 MB, storage 271 MB**. Retrieval probe over 13 courses: relevant top hits for every course, median ~1.1 s | Supabase data |
| 2026-11-10 | Seed: all 13 1st-year courses (MATH F111/F112, EEE F111, ME F110/F112, BIO F111, CHEM F111, BITS F111/F112 added) | `supabase/seed.sql` |
| 2026-11-10 | `upsert_chunks`: batches of 25 + retry on dropped connections and statement timeouts; 4 unit tests | `backend/app/db.py`, `backend/tests/test_db_upsert.py` |
| 2026-11-10 | P1: rich answers, quiz + flashcards (Practice page), OCR, calendar (events API, extraction, ICS, page, reminders), pitch draft | `backend/app/rag/{study,prompts,answerer}.py`, `backend/app/ingest/{ocr,deadlines,pdf_loader}.py`, `backend/app/api/{study,events}.py`, `backend/app/calendar_ics.py`, `frontend/app/{practice,calendar}`, `docs/pitch.md` |
| 2026-11-09 | Phases 4–5: Ask thread (scope, examples, streaming, chips, source panel, feedback), course selector, Lectures list + upload card with live stages, lecture detail (Summary/Flagged/Transcript/Ask, audio bar, `?t=` deep links), Flagged page, Sources (documents table + add/delete, Insights) | `frontend/app/*`, `frontend/components/*`, `frontend/lib/*` |
| 2026-11-09 | Phase 3: flagger (cue regex + LLM JSON check), lecture notes (parts + combine), `reprocess_lecture()`, `GET /api/flagged`, `GET /api/insights`; lecture detail uses exact moments | `backend/app/ingest/{flagger,lecture_notes,pipeline}.py`, `backend/app/api/{flagged,insights,lectures}.py` |
| 2026-11-09 | Phase 2: LLM provider, retriever, reranker, priority, prompts, answerer, `/api/ask` (SSE), `/api/feedback`, eval runner + provisional set; 22 unit tests | `backend/app/{llm,rag,api}/*`, `backend/eval/*` |
| 2026-11-09 | Real-data ingest test: 19 BPDC PDFs (MATH F113 + PHY F111 handouts, PHY F110 lab handout + manual, 5 MOW slide decks, 1 MOW notes, 9 PYQs) uploaded via `/api/documents`; all `ready`, 488 chunks. Retrieval probe (16 questions, embed → `hybrid_search`): **15/16 expected doc in top 5**, 13 at rank 1. Miss: "When was the MATH F113 midsem / open book?" → PYQ headers outrank the handout | Supabase data only |
| 2026-11-09 | `OLLAMA_URL` → `http://127.0.0.1:11434` (see bug below) | `backend/.env`, `.env.example`, `app/config.py`, `docs/Architecture.md` |
| 2026-11-09 | Phase 1: prepare, pdf_loader, transcriber, chunker, embedder, pipeline, document + lecture APIs, 9 unit tests | `backend/app/ingest/*`, `backend/app/rag/embedder.py`, `backend/app/db.py`, `backend/app/api/{documents,lectures}.py` |
| 2026-11-09 | Phase 0: Supabase schema + seed, backend and frontend skeletons, README | `supabase/`, `backend/`, `frontend/` |
| 2026-11-09 | Repo scaffold (task 0.1): docs/, backend/, frontend/, supabase/, .gitignore, README | root
| 2026-11-09 | Docs v2: Supabase, instructor priority, flagged moments, feedback loop, upload prep, flowcharts | `docs/*` |
| 2026-11-09 | Docs v1 created | `docs/*` |

## 4. Bugs and fixes

| Date | Bug | Cause | Fix | Status |
| --- | --- | --- | --- | --- |
| 2026-11-10 | Large textbooks failed: Postgres 57014 statement timeout on chunk upsert | PostgREST `statement_timeout=8s`; 100-row HNSW inserts too slow above ~10k chunks | Batch 25 + retry | Fixed |
| 2026-11-10 | Random 'Server disconnected' / HTTP 500 on uploads | Supabase drops idle HTTP/2 connections | Retry in `upsert_chunks`; other DB calls still unprotected | Partly fixed |
| 2026-11-10 | PDFs > 50 MB after compression fail at Storage upload (400) | Free-tier 50 MB per-file limit | Not fixed: Introduction to Mechanics (58 MB), Maths Solutions Manual (63 MB) left out | Open |
| 2026-11-10 | Search 1–5.5 s and unscoped queries time out with 24.5k chunks | `hybrid_search` (0006) exact-scans every candidate, no HNSW/GIN use | Textbooks removed (now ~1.1 s); real fix = index-based search (tasks.md 2.10) | Workaround |
| 2026-11-10 | Prompt contained a form-feed character instead of `\frac` | `\f` escape in a non-raw Python string written by a script | Raw string; character replaced | Fixed |
| 2026-11-10 | Quiz LaTeX broke (`\text` became a tab) | Model writes LaTeX in JSON strings without escaping backslashes | Escape backslash commands before `json.loads` | Fixed |
| 2026-11-10 | Chunk upsert failed with Postgres 22P05 on some PDFs (reported by the testing-materials session) | NUL characters in PDF text | `clean_text()` strips C0 control characters from page and OCR text | Fixed (unit test) |
| 2026-11-10 | `/calendar` prerender error: `new Date()` in a client component | `cacheComponents` | Page wrapped in `<Suspense>` | Fixed |
| 2026-11-10 | Some AI-written MCQs have two correct options (e.g. P(A∩B)/P(B) and Bayes' formula) | Model limit | Every question shows its source; prompt asks for exactly one correct option | Open (known limit) |
| 2026-11-09 | `/lectures/[id]` errored: `usePathname()` outside `<Suspense>` | `cacheComponents: true` (create-next-app default) requires Suspense for runtime hooks in the layout | Nav split into `NavBar` + Suspense-wrapped `ActiveNav` | Fixed |
| 2026-11-09 | `/sources` page 618 px wide on a 375 px phone | Table min-content widened the mobile layout viewport despite `overflow-x-auto` | Hide secondary columns on phones | Fixed |
| 2026-11-09 | Every question took ~50 s to first token | (1) Ollama 1-model limit swapped bge-m3/gemma; (2) warm-up loaded gemma with default 4096 ctx, real calls used 8192 → reload; (3) reranker on CPU (17 s) | 2-model Ollama, same options in warm-up, CUDA torch | Fixed: 2.2 s median |
| 2026-11-09 | Ollama 500 on `/api/chat` from Python while curl worked | Model load failing under memory pressure while the reranker downloaded + 1-model limit | Same fix as above | Fixed |
| 2026-11-09 | `[1, 2, 3, 4, 5]` leaked unfiltered | Citation filter only held 12 chars | Hold up to 40 chars | Fixed |
| 2026-11-09 | Two flags for one moment ("note this down." + "will come in the exam") | Adjacent cue lines each confirmed | Merge cues within 10 s of a confirmed moment | Fixed (unit test) |
| 2026-11-09 | Physics docs leaked into MATH F113 searches | Seed had no PHY courses; docs uploaded with `course_id = null` count as campus-wide | Added PHY F111 (`…c3`, sections L1/L2) and PHY F110 (`…c4`, P1) to `seed.sql` with fictional instructors; re-tagged 13 physics sources via SQL; scoped searches verified clean | Fixed |
| 2026-11-09 | Every embed call took ~2.8 s (query retrieval ~2.9 s) | On Windows `localhost` tries IPv6 `::1` first; Ollama listens on `127.0.0.1` only | `OLLAMA_URL=http://127.0.0.1:11434`; retrieval now ~0.8 s | Fixed |
| 2026-11-09 | Scanned PDFs fail ingest ("No text was found") — most BPDC answer keys, handwritten chapter notes and older PYQs | No OCR in pipeline | By design for now; OCR would be a new dependency (ask first) | Open |
| 2026-11-09 | Slide decks / notes give tiny chunks (median 33–53 words; 101 of 488 chunks < 25 words, e.g. "are plotted in the next slide.") | Chunker never crosses pages; one slide = one page | Consider merging consecutive short pages in 2.9 tuning | Open |
| 2026-11-09 | Transcription crashed: `av.open() got an unexpected keyword argument 'metadata_errors'` | faster-whisper newer than installed PyAV | Decode audio with ffmpeg → numpy, pass samples to Whisper | Fixed |
| 2026-11-09 | Chunk overlap dropped for long paragraphs | Pieces were exactly MAX_WORDS, so the overlap tail never fit | Split long paragraphs at 85% of MAX_WORDS | Fixed (unit test) |

## 5. Eval scores

| Date | Commit | Correct (/15) | Refused (/3) | Flag recall | First-token time | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10 | p1 | 15/15 | 3/3 | — | 2.3 s median, 3.9 s max | Corpus now includes the testing session's bulk PDFs; + course code in the question selects that course |
| 2026-11-10 | p1 (before fix) | 13/15 | 3/3 | — | 2.6 s median | Tables/LaTeX prompt; 2 PHY misses: handout out of the top 40 in the bigger corpus |
| 2026-11-09 | phase-2 tuned | 15/15 | 3/3 | 2/2 (TEST lecture) | 2.2 s median, 2.6 s max | + TOP_K_RETRIEVE 40 (phy-quiz1 fixed) |
| 2026-11-09 | phase-2 | 14/15 | 3/3 | — | 2.3 s median | + `material` kind, official-passage rule, gate 0.02 |
| 2026-11-09 | phase-2 | 10/15 | 3/3 | — | 2.1 s median | + OR full-text, exact vector scan, reranker sees title/instructor |
| 2026-11-09 | phase-2 baseline | 7/15 | 3/3 | — | 2.0 s median | Provisional set (`backend/eval/questions.json`): handouts + TEST lecture. PYQ cover pages outranked handouts |

## 6. Open questions

- Which BPDC documents may we use? (Academic regulations, student handbook, one MATH F113 course handout, one circular.)
- Which lecture do we use, with whose consent? Fallback: a teammate records a 5-minute MATH F113 mini-lecture that includes two "this will come in the exam" moments.
- Team member names and who owns backend / frontend / data / pitch.
- Real course/section/instructor names for `supabase/seed.sql` (or clearly fictional demo names).
- Test PDFs carry real instructor names (handouts). OK for the demo? Textbooks (Devore, Kleppner, Fundamentals of Physics) and solution manuals were **not** uploaded (copyright + size).
- `.docx` handouts were converted to PDF with Word for this test; the API accepts PDF only. Accept .docx in the product?
- Retrieval RRF scores are ~0.016 for relevant and irrelevant queries alike → refusal must rely on the reranker score (2.3/2.6), never RRF.

## 7. Notes for future sessions

- **Start for the demo:** double-click `CampusMind.bat` (production build, faster than `npm run dev`). Install from Chrome/Edge for a full-screen app window.
- **Before the demo (P1):** delete or replace the 6 'Demo: …' calendar events and 'TEST Handwritten notes - Random variables'. Review suggested calendar dates. Browser reminders fire only while a CampusMind tab is open; the phone-calendar subscription covers the closed case.
- Quiz generation takes 15–30 s, flashcards ~5 s, OCR ~8 s per scanned page (all on the shared gemma4).
- **Before the demo:** set Windows env var `OLLAMA_MAX_LOADED_MODELS=2` and restart Ollama (this session ran its own Ollama with it). Install CUDA torch on the demo laptop (README).
- **Eval set is provisional.** Replace with the real D.3 set; questions 14–15 point at the TEST lecture. Re-run `python eval/run_eval.py` after.
- Answers quoting dates from past papers don't always name the semester even though the prompt asks — watch in demo questions.
- To give an existing lecture flags/notes without re-uploading: `from app.ingest.pipeline import reprocess_lecture; reprocess_lecture("<id>")`.
- **Delete the TEST sources before task 6.1:** "TEST Academic Regulations" (PDF) and "TEST Lecture 4 - Bayes theorem" (TTS lecture). They exist only to develop Phase 2.
- Speed on this laptop: 2-minute lecture → ready in ~40 s (Whisper small, CPU int8). Expect ~2 min for a 5-minute lecture.
- Flagger (3.1): match cue phrases on word boundaries — "exam" must not match "example".
- Tasks 1.2/1.3 checks were run on generated TEST files; re-check page numbers and transcript on the real D.1/D.2 files.
- Changing `EMBED_MODEL` → delete all `chunks` rows and re-embed every source.
- Supabase free projects pause after 1 week idle → open the dashboard before each round.
- Pre-process all demo files before going on stage; never transcribe live.
- Wi-Fi backup: phone hotspot; or local Supabase (`supabase start`) with the same migrations and a `.env` URL change.
