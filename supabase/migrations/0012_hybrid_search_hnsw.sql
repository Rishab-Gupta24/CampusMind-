-- Task 2.10: hybrid_search on indexes instead of an exact scan.
-- Semantic half: HNSW on half-precision vectors (0011) with pgvector 0.8 iterative scans, so filters
-- (status, course, source) are applied while walking the index and do not drop rows. Distances are
-- re-sorted exactly on the returned rows (relaxed_order only affects the walk).
-- Full-text half: unchanged logic (OR of query terms, ts_rank_cd), now through the GIN index without
-- materializing every candidate embedding first (that CTE spilled to disk and took ~7 s).
-- Same signature and output as 0006, so the backend does not change.

-- Load pgvector in this session so its hnsw.* settings exist when the function's SET clauses are checked.
select '[1]'::vector;

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
set hnsw.iterative_scan = relaxed_order
set hnsw.ef_search = 100
as $$
  with scoped as (
    select s.id
    from sources s
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
    from chunks c, query
    where query.q is not null
      and c.fts @@ to_tsquery('english', query.q)
      and c.source_id in (select id from scoped)
    order by rank_ix
    limit match_count * 2
  ),
  nearest as (
    select c.id, c.embedding::halfvec(1024) <=> query_embedding::halfvec(1024) as dist
    from chunks c
    where c.source_id in (select id from scoped)
    order by c.embedding::halfvec(1024) <=> query_embedding::halfvec(1024)
    limit match_count * 2
  ),
  semantic as (
    select id, row_number() over (order by dist) as rank_ix from nearest
  )
  select
    coalesce(f.id, s.id) as chunk_id,
    coalesce(1.0 / (rrf_k + f.rank_ix), 0.0) + coalesce(1.0 / (rrf_k + s.rank_ix), 0.0) as rrf_score
  from full_text f
  full outer join semantic s on f.id = s.id
  order by rrf_score desc
  limit match_count;
$$;

-- Only the backend (service role) calls this. Without these grants the publishable key could run an
-- expensive search directly (rows would still be hidden by RLS, but the CPU cost is not).
revoke execute on function hybrid_search(text, vector, int, text, uuid, int, uuid) from public, anon, authenticated;
grant execute on function hybrid_search(text, vector, int, text, uuid, int, uuid) to service_role;
