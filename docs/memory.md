# CampusMind — Project Memory

The project's long-term memory. **Read this first in every session.** Add to it whenever a decision is made, something changes, a bug is found, or eval runs. Newest entries at the top of each table. One or two lines per entry.

---

## 1. Project context (keep current)

- **What:** CampusMind — AI assistant answering student questions from campus PDFs and lecture recordings, always with sources, showing who said it and what instructors flagged as important. See `PRD.md`.
- **Why:** IDEAVERSE 2026 ideathon (GDGoC BPDC × GDG HWUD × IEI). Theme: *Smart Campus, AI Solutions*. Team of 2–4.
- **Deadlines:** Round 1 + shortlisting (top 10) → **10 Nov 2026** · Final pitch → **11 Nov 2026**.
- **Judging needs:** one clear student problem, how AI helps, a **working prototype**.
- **Constraint:** AED 0 → local open-source models (Ollama) + Supabase free tier.
- **Current phase:** Phases 1–3 done (ingestion, cited answers, flagged moments + notes). Eval 15/15 + 3/3 on the provisional set. Next: Phase 4/5 frontend.
- **Demo machine:** this laptop — Ryzen 9 8940HX, 16 GB RAM, RTX 5050 Laptop 8 GB → `LLM_MODEL=gemma4:e4b` (verified with `ollama pull`).
- **GitHub repo:** https://github.com/Rishab-Gupta24/CampusMind-
- **Supabase project:** `campusmind`, ref `apqaojhsbhvapllcyqto`, region ap-south-1 (Mumbai), free tier.

## 2. Decisions log

| Date | Decision | Reason |
| --- | --- | --- |
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
