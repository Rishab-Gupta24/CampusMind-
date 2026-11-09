-- Retrieval fixes found by the eval (task 2.9):
-- 1. Full-text used websearch_to_tsquery, which ANDs every word: natural questions matched nothing.
--    Now terms are ORed and ranked by ts_rank_cd, so exact terms (course codes, "Quiz-1", rule numbers) still count.
-- 2. Vector search runs on a materialized candidate set: an exact scan after filtering. At campus scale
--    (thousands of chunks) this is fast and avoids the approximate HNSW index dropping filtered rows.
create or replace function hybrid_search(
  query_text text,
  query_embedding vector(1024),
  match_count int default 20,
  filter_type text default null,
  filter_course uuid default null,
  rrf_k int default 60,
  filter_source uuid default null
)
returns table (chunk_id text, rrf_score double precision)
language sql stable
set search_path = public
as $$
  with candidates as materialized (
    select c.id, c.fts, c.embedding
    from chunks c
    join sources s on s.id = c.source_id
    where s.status = 'ready'
      and (filter_type is null or s.type = filter_type)
      and (filter_course is null or s.course_id is null or s.course_id = filter_course)
      and (filter_source is null or s.id = filter_source)
  ),
  query as (
    select nullif(replace(plainto_tsquery('english', query_text)::text, '&', '|'), '') as q
  ),
  full_text as (
    select c.id, row_number() over (order by ts_rank_cd(c.fts, to_tsquery('english', query.q)) desc) as rank_ix
    from candidates c, query
    where query.q is not null and c.fts @@ to_tsquery('english', query.q)
    order by rank_ix
    limit match_count * 2
  ),
  semantic as (
    select id, row_number() over (order by embedding <=> query_embedding) as rank_ix
    from candidates
    order by embedding <=> query_embedding
    limit match_count * 2
  )
  select
    coalesce(f.id, s.id) as chunk_id,
    coalesce(1.0 / (rrf_k + f.rank_ix), 0.0) + coalesce(1.0 / (rrf_k + s.rank_ix), 0.0) as rrf_score
  from full_text f
  full outer join semantic s on f.id = s.id
  order by rrf_score desc
  limit match_count;
$$;
