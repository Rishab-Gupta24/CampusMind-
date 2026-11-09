# CampusMind — Rule Book

**Version:** v2 · **Last updated:** 2026-11-09

These rules are **strict**. Anyone (human or AI) working on this repo follows them. If a rule blocks you, write it in `memory.md` and ask; never silently break it.

---

## 1. Strict requirements (MUST)

### Product and trust
1. **Every answer cites its sources.** No answer without at least one source chip, except the "couldn't find" message.
2. **Answer only from retrieved passages.** The LLM never uses its general knowledge about BITS or any university.
3. **Refuse when unsure.** If the best **raw** reranker score < `MIN_RELEVANCE`: return *"I couldn't find this in the campus sources. Try rephrasing, or check with the academic office."* and log the question in `unanswered`.
4. **Priority is always visible.** Every boost applied to a passage (Official, IC, HOD, Flagged, Your section) appears as a badge on its chip. No hidden ranking, no hidden sources.
5. **Boosts never bypass the relevance gate.** The gate uses the raw score; boosts only re-order already-relevant passages.
6. **Flagged moments need two steps:** a cue-phrase match **and** an LLM confirmation with a one-line reason. No flag without a reason.
7. **Cost stays AED 0.** Free tiers (Supabase, optional Gemini) and local models only.
8. **The demo path always works.** `main` runs end to end: upload PDF → upload lecture → ask → cited answer with badges → rate it.

### Data and security
9. **Only the backend talks to Supabase.** The service-role key lives in `backend/.env` and nowhere else. The frontend never imports a Supabase client.
10. **RLS stays enabled on every table** with no public policies until login exists.
11. **Schema changes only through migration files** in `supabase/migrations/`, numbered in order. Never edit tables by hand in the dashboard without adding the migration.
12. **Uploads:** reject files > `MAX_UPLOAD_MB` (200). Audio/video **always** go through `ingest/prepare.py` (mono 16 kHz Opus). PDFs > `PDF_COMPRESS_OVER_MB` (20) are compressed. Temporary files are deleted after processing.
13. **Lecture uploads require course, section, instructor and date.** Lectures without an instructor role cannot be boosted.
14. Storage bucket `sources` is **private**; playback uses short-lived signed URLs.

### Code
15. Python 3.11, type hints on every function, `ruff` clean.
16. TypeScript `strict: true`. No `any` without a comment explaining why.
17. **All prompts live in `backend/app/rag/prompts.py`.**
18. **All model names, URLs, thresholds and boost values live in config** (`.env` → `config.py`).
19. **LLM calls go through `llm/base.py` (`LLMProvider`).** Ollama ↔ Gemini is a config change only.
20. **Same embedding model for indexing and querying.** Changing `EMBED_MODEL` = clear `chunks` and re-embed everything; log it in `memory.md`.
21. **Deterministic chunk IDs** (`{source_id}_{page or start}_{n}`), so re-uploads replace instead of duplicate.
22. Long work (prepare, transcribe, flag, embed) runs as a background task; upload endpoints return `202` immediately.
23. Every API error returns `{error: string}` with a correct status; the UI shows a short human message.
24. Frontend talks to the backend **only** through `frontend/lib/api.ts`.
25. Follow `design.md` for every UI change.

### Process
26. Work from `tasks.md` in order. One task = one branch = one commit (`feat(rag): add priority boosts`).
27. After each task: run it, tick it in `tasks.md`, update `memory.md` (decision, change, bug or eval score).
28. Run `python eval/run_eval.py` after any change to chunking, retrieval, reranking, boosts or prompts. The score must not drop.
29. Keep `README.md` run instructions correct.

## 2. Prohibited practices (MUST NOT)

1. Committing `.env`, keys, uploads, transcripts, `backend/tmp/`.
2. Exposing `SUPABASE_SERVICE_ROLE_KEY` to the browser, logs, or error messages.
3. Calling paid APIs (OpenAI, Anthropic, paid Gemini tiers).
4. Training or fine-tuning models.
5. Adding LangChain, LlamaIndex, Haystack or similar frameworks.
6. **Secret or unexplained ranking** of instructors or sources.
7. Flagging a moment without an LLM-confirmed reason.
8. Sending whole documents to the LLM; only the top passages go into the prompt.
9. Showing users stack traces, model names, or "As an AI language model…".
10. Inventing citations; every `[n]` must map to a passage actually sent.
11. Gradients, glowing shadows, "AI" purple styling, emoji in the UI (see `design.md`).
12. Writing a custom compressor or codec. Use ffmpeg and PyMuPDF.
13. Uploading lectures without the instructor's consent.
14. Scraping the BITS portal, LMS or email.
15. Adding pages or features not in `PRD.md` / `tasks.md` without logging them in `memory.md` first.
16. Large refactors after 22:00 the night before a round — bug fixes only.
17. Leaving `print` / `console.log` debugging in committed code.

## 3. Approved vs prohibited libraries

### Backend (Python)

| Approved | Purpose |
| --- | --- |
| `fastapi`, `uvicorn[standard]` | API server |
| `pydantic`, `pydantic-settings` | Schemas, config |
| `python-multipart` | Uploads |
| `sse-starlette` | Streaming answers |
| `httpx` | Ollama calls |
| `supabase` | Database, RPC, Storage (backend only) |
| `sentence-transformers` | Reranker |
| `faster-whisper` | Speech-to-text |
| `pymupdf` | PDF text, page numbers, compression |
| `ffmpeg` (system binary via `subprocess`) | Audio/video preparation |
| `Pillow` | Image resizing (only if images are added later) |
| `google-genai` | **P1 only**, Gemini fallback |
| `pytest`, `ruff` | Tests, lint |

| Prohibited | Why |
| --- | --- |
| `langchain*`, `llama-index*`, `haystack` | Heavy, hides the pipeline |
| `openai`, `anthropic` SDKs | Paid APIs |
| `openai-whisper` (original) | Slower than faster-whisper |
| `PyPDF2` | Poor text extraction |
| `pinecone`, `weaviate-client`, `qdrant-client`, `chromadb` | One store only: Supabase |
| `rank-bm25` | Replaced by Postgres full-text search |
| `ffmpeg-python`, `moviepy`, `pydub` | Wrappers not needed; call ffmpeg directly |
| `streamlit`, `gradio`, `flask`, `django` | One backend, one frontend |

### Frontend (TypeScript)

| Approved | Purpose |
| --- | --- |
| `next`, `react`, `react-dom`, `typescript` | App |
| `tailwindcss` | Styling with tokens |
| `lucide-react` | Icons |
| `clsx` | Class names |
| `react-markdown` | Render answers |
| `@radix-ui/react-*` (unstyled, only if needed) | Accessible select, tabs, dialog, tooltip |

| Prohibited | Why |
| --- | --- |
| `@supabase/supabase-js` | Browser must not touch the database |
| MUI, Chakra, Ant Design, Bootstrap, DaisyUI, Mantine | Generic look |
| Pre-styled shadcn templates copied as-is | "Vibecoded" look |
| `framer-motion`, GSAP, Lottie | CSS transitions only |
| `axios` | Use `fetch` in `lib/api.ts` |
| Analytics or tracking scripts | Privacy |

New library not listed → write the reason in `memory.md` first.

## 4. Definition of done (every task)

- [ ] Runs from a clean start using `README.md`.
- [ ] No errors in backend logs or browser console.
- [ ] Follows `design.md` (if UI) and Section 1 here.
- [ ] Eval score not lower (if RAG-related).
- [ ] Ticked in `tasks.md`; `memory.md` updated if needed.
