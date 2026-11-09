-- Adds filter_source so "Ask this lecture" searches one source only.
drop function if exists hybrid_search(text, vector, int, text, uuid, int);

create or replace function hybrid_search(
  query_text text,
  query_embedding vector(1024),
  match_count int default 20,
  filter_type text default null,      -- 'pdf' | 'lecture' | null (all)
  filter_course uuid default null,    -- course chosen by the student; campus docs always included
  rrf_k int default 60,
  filter_source uuid default null     -- one source only (Ask this lecture)
)
returns table (chunk_id text, rrf_score double precision)
language sql stable
set search_path = public
as $$
  with candidates as (
    select c.*
    from chunks c
    join sources s on s.id = c.source_id
    where s.status = 'ready'
      and (filter_type is null or s.type = filter_type)
      and (filter_course is null or s.course_id is null or s.course_id = filter_course)
      and (filter_source is null or s.id = filter_source)
  ),
  full_text as (
    select id, row_number() over (
      order by ts_rank_cd(fts, websearch_to_tsquery('english', query_text)) desc
    ) as rank_ix
    from candidates
    where fts @@ websearch_to_tsquery('english', query_text)
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
