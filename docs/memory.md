# CampusMind — Project Memory

The project's long-term memory. **Read this first in every session.** Add to it whenever a decision is made, something changes, a bug is found, or eval runs. Newest entries at the top of each table. One or two lines per entry.

---

## 1. Project context (keep current)

- **What:** CampusMind — AI assistant answering student questions from campus PDFs and lecture recordings, always with sources, showing who said it and what instructors flagged as important. See `PRD.md`.
- **Why:** IDEAVERSE 2026 ideathon (GDGoC BPDC × GDG HWUD × IEI). Theme: *Smart Campus, AI Solutions*. Team of 2–4.
- **Deadlines:** Round 1 + shortlisting (top 10) → **10 Nov 2026** · Final pitch → **11 Nov 2026**.
- **Judging needs:** one clear student problem, how AI helps, a **working prototype**.
- **Constraint:** AED 0 → local open-source models (Ollama) + Supabase free tier.
- **Current phase:** Docs v2 written. Build not started. Next: task 0.1.
- **Demo machine:** _fill in: laptop model, RAM, GPU_ → decides `LLM_MODEL`.
- **GitHub repo:** https://github.com/Rishab-Gupta24/CampusMind-
- **Supabase project:** _fill in project name / ref (never the keys)_

## 2. Decisions log

| Date | Decision | Reason |
| --- | --- | --- |
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
| 2026-11-09 | Repo scaffold (task 0.1): docs/, backend/, frontend/, supabase/, .gitignore, README | root
| 2026-11-09 | Docs v2: Supabase, instructor priority, flagged moments, feedback loop, upload prep, flowcharts | `docs/*` |
| 2026-11-09 | Docs v1 created | `docs/*` |

## 4. Bugs and fixes

| Date | Bug | Cause | Fix | Status |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

## 5. Eval scores

| Date | Commit | Correct (/15) | Refused (/3) | Flag recall | First-token time | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | baseline not run yet |

## 6. Open questions

- Which BPDC documents may we use? (Academic regulations, student handbook, one MATH F113 course handout, one circular.)
- Which lecture do we use, with whose consent? Fallback: a teammate records a 5-minute MATH F113 mini-lecture that includes two "this will come in the exam" moments.
- Demo laptop specs → `LLM_MODEL`.
- Team member names and who owns backend / frontend / data / pitch.
- Real course/section/instructor names for `supabase/seed.sql` (or clearly fictional demo names).

## 7. Notes for future sessions

- Changing `EMBED_MODEL` → delete all `chunks` rows and re-embed every source.
- Supabase free projects pause after 1 week idle → open the dashboard before each round.
- Pre-process all demo files before going on stage; never transcribe live.
- Wi-Fi backup: phone hotspot; or local Supabase (`supabase start`) with the same migrations and a `.env` URL change.
