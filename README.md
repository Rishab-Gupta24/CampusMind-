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

## Status

Early build. Setup and run instructions will be added here as the backend and frontend land.

## Team

Rishab Gupta and team — BITS Pilani, Dubai Campus.
