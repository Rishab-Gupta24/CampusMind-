-- Task 2.10: index-based vector search.
-- The exact scan in 0006 read every 4 KB embedding from TOAST storage: ~5 s for 4.9k chunks on the free tier,
-- and an 8 s timeout once the textbooks were loaded. The old HNSW index was never used and had bloated to
-- 191 MB with entries for 19.7k deleted rows.
-- New index: half-precision vectors (2 bytes per dimension), about half the size, same ranking quality for
-- cosine search (bge-m3 embeddings are normalized). Queries must use the same expression to hit it.
drop index if exists chunks_embedding_idx;

create index chunks_embedding_hv_idx on chunks
  using hnsw ((embedding::halfvec(1024)) halfvec_cosine_ops)
  with (m = 16, ef_construction = 64);

-- Covering indexes for foreign keys flagged by the performance advisor.
create index if not exists sources_course_idx on sources (course_id);
create index if not exists sources_section_idx on sources (section_id);
create index if not exists sources_instructor_idx on sources (instructor_id);
create index if not exists sections_instructor_idx on sections (instructor_id);
create index if not exists feedback_answer_idx on feedback (answer_id);
create index if not exists events_section_idx on events (section_id);
create index if not exists events_source_idx on events (source_id);
