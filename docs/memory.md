# CampusMind — Project Memory

The project's long-term memory. **Read this first in every session.** Add to it whenever a decision is made, something changes, a bug is found, or eval runs. Newest entries at the top of each table. One or two lines per entry.

---

## 1. Project context (keep current)

- **What:** CampusMind — AI assistant answering student questions from campus PDFs and lecture recordings, always with sources, showing who said it and what instructors flagged as important. See `PRD.md`.
- **Why:** IDEAVERSE 2026 ideathon (GDGoC BPDC × GDG HWUD × IEI). Theme: *Smart Campus, AI Solutions*. Team of 2–4.
- **Deadlines:** Round 1 + shortlisting (top 10) → **10 Nov 2026** · Final pitch → **11 Nov 2026**.
- **Judging needs:** one clear student problem, how AI helps, a **working prototype**.
- **Constraint:** AED 0 → local open-source models (Ollama) + Supabase free tier.
- **Current phase:** Phase 1 (ingestion) done and tested with TEST fixtures. Next: Phase 2 retrieval and answers.
- **Demo machine:** this laptop — Ryzen 9 8940HX, 16 GB RAM, RTX 5050 Laptop 8 GB → `LLM_MODEL=gemma4:e4b` (verified with `ollama pull`).
- **GitHub repo:** https://github.com/Rishab-Gupta24/CampusMind-
- **Supabase project:** `campusmind`, ref `apqaojhsbhvapllcyqto`, region ap-south-1 (Mumbai), free tier.

## 2. Decisions log

| Date | Decision | Reason |
| --- | --- | --- |
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
| 2026-11-09 | Phase 1: prepare, pdf_loader, transcriber, chunker, embedder, pipeline, document + lecture APIs, 9 unit tests | `backend/app/ingest/*`, `backend/app/rag/embedder.py`, `backend/app/db.py`, `backend/app/api/{documents,lectures}.py` |
| 2026-11-09 | Phase 0: Supabase schema + seed, backend and frontend skeletons, README | `supabase/`, `backend/`, `frontend/` |
| 2026-11-09 | Repo scaffold (task 0.1): docs/, backend/, frontend/, supabase/, .gitignore, README | root
| 2026-11-09 | Docs v2: Supabase, instructor priority, flagged moments, feedback loop, upload prep, flowcharts | `docs/*` |
| 2026-11-09 | Docs v1 created | `docs/*` |

## 4. Bugs and fixes

| Date | Bug | Cause | Fix | Status |
| --- | --- | --- | --- | --- |
| 2026-11-09 | Transcription crashed: `av.open() got an unexpected keyword argument 'metadata_errors'` | faster-whisper newer than installed PyAV | Decode audio with ffmpeg → numpy, pass samples to Whisper | Fixed |
| 2026-11-09 | Chunk overlap dropped for long paragraphs | Pieces were exactly MAX_WORDS, so the overlap tail never fit | Split long paragraphs at 85% of MAX_WORDS | Fixed (unit test) |

## 5. Eval scores

| Date | Commit | Correct (/15) | Refused (/3) | Flag recall | First-token time | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | baseline not run yet |

## 6. Open questions

- Which BPDC documents may we use? (Academic regulations, student handbook, one MATH F113 course handout, one circular.)
- Which lecture do we use, with whose consent? Fallback: a teammate records a 5-minute MATH F113 mini-lecture that includes two "this will come in the exam" moments.
- Team member names and who owns backend / frontend / data / pitch.
- Real course/section/instructor names for `supabase/seed.sql` (or clearly fictional demo names).

## 7. Notes for future sessions

- **Delete the TEST sources before task 6.1:** "TEST Academic Regulations" (PDF) and "TEST Lecture 4 - Bayes theorem" (TTS lecture). They exist only to develop Phase 2.
- Speed on this laptop: 2-minute lecture → ready in ~40 s (Whisper small, CPU int8). Expect ~2 min for a 5-minute lecture.
- Flagger (3.1): match cue phrases on word boundaries — "exam" must not match "example".
- Tasks 1.2/1.3 checks were run on generated TEST files; re-check page numbers and transcript on the real D.1/D.2 files.
- Changing `EMBED_MODEL` → delete all `chunks` rows and re-embed every source.
- Supabase free projects pause after 1 week idle → open the dashboard before each round.
- Pre-process all demo files before going on stage; never transcribe live.
- Wi-Fi backup: phone hotspot; or local Supabase (`supabase start`) with the same migrations and a `.env` URL change.
