# CampusMind

**A free AI assistant that knows your campus rules and your course lectures, tells you what your instructors flagged as important, and proves every answer with its source.**

Built for **IDEAVERSE 2026** (GDGoC BPDC × GDG HWUD × IEI) — theme *Smart Campus, AI Solutions*.

## The problem

Students can't quickly get trustworthy answers from their own campus documents and lectures, and they miss what their instructors said was important. Rules are buried in long PDFs, lectures are spoken once and gone, and "this will come in the exam" is heard only by whoever was in the room.

## What CampusMind does

- **Ask with sources** — plain-language answers from campus PDFs and lecture recordings, each claim linked to a document page or lecture timestamp. If the answer isn't in the sources, it says so.
- **Lecture mode** — upload a recording to get a timestamped transcript, summary, key points and formulas.
- **Flagged by instructor** — detects moments like "this will come in the exam" and explains why each was flagged.
- **Who said it** — every source shows its origin (Official, IC, HOD, your section). Priority is always visible, never hidden.
- **Gets better with use** — answer ratings and a list of unanswered questions show admins what to add next.
- **Practice** — 5–10 question quizzes on any topic or chapter (multiple choice, fill-in, short answer), each showing its source, e.g. "Past paper · 2021-22 Sem II · Mid-semester exam · Q1(a)". Plus flashcards.
- **Calendar** — exam and deadline dates found in handouts, colour-coded by urgency, with reminders and a subscribe link for Google, Outlook or Apple Calendar.
- **Handwritten notes and scans** — photos and scanned PDFs are read by a local vision model and become searchable.
- **Rich answers** — tables and properly rendered formulas.

## Tech stack

| Layer | Choice |
| --- | --- |
| Knowledge base | Supabase (Postgres + pgvector + full-text search + Storage) |
| Speech-to-text | faster-whisper |
| Embeddings / reranker | bge-m3 / bge-reranker-v2-m3 |
| LLM | Open-source models via Ollama (runs locally, AED 0) |
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js + Tailwind (TypeScript) |

## Repository layout

```
docs/       Product, architecture, rules, design and task docs
backend/    FastAPI app, ingestion and RAG pipeline
frontend/   Next.js web app
supabase/   Database migrations and seed data
```

## Documentation

- [Product requirements](docs/PRD.md)
- [Architecture](docs/Architecture.md)
- [Rules](docs/Rules.md)
- [Design](docs/design.md)
- [Build tasks](docs/tasks.md)

## Start the app (Windows, after setup)

Double-click **`CampusMind.bat`**. It starts Ollama (keeping both models loaded), the backend and the app, skips anything already running, and opens <http://localhost:3000>. `CampusMind-stop.bat` stops the backend and app. Use `CampusMind.bat -Rebuild` after pulling new code.

**Install it like an app:** open <http://localhost:3000> in Chrome or Edge and choose **Install CampusMind** in the address bar (on Android: menu → *Add to Home screen*). It opens in its own window with its own icon, and calendar reminders appear as system notifications.

## Run it locally (setup and development)

**Needs:** Python 3.12, Node.js LTS, [ffmpeg](https://ffmpeg.org) on PATH, [Ollama](https://ollama.com), and a Supabase project with `supabase/migrations/*.sql` and `supabase/seed.sql` applied.

**1. Models (once)**

```bash
ollama pull gemma4:e4b
ollama pull bge-m3
```

Ollama must keep **both** models loaded, or every question reloads the LLM (~25 s). Set the environment variable `OLLAMA_MAX_LOADED_MODELS=2` (Windows: System → Environment Variables) and restart Ollama.

**2. Backend** — copy `backend/.env.example` to `backend/.env` and fill in `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (never commit this file).

```bash
cd backend
python3.12 -m venv .venv                         # Windows: py -3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload          # Windows: .venv\Scripts\uvicorn app.main:app --reload
```

**NVIDIA GPU (recommended):** the reranker is ~20x faster on a GPU. After installing requirements, swap in the CUDA build of PyTorch:

```bash
.venv/bin/pip install --force-reinstall --no-deps torch --index-url https://download.pytorch.org/whl/cu130
```

Check: <http://localhost:8000/api/health> shows `"ollama": true, "supabase": true`.

**3. Frontend** — copy `frontend/.env.local.example` to `frontend/.env.local`.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. While `NEXT_PUBLIC_USE_MOCK=true`, the frontend uses mock data and doesn't need the backend.

## Status

Phase 0 (setup) is in progress. See [docs/tasks.md](docs/tasks.md).

## Team

Rishab Gupta and team — BITS Pilani, Dubai Campus.
