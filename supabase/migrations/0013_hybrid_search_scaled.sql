-- Task 2.10: keep hybrid_search fast at ~25k chunks (textbooks re-added).
-- 0012 was a SQL function, so Postgres planned it once with unknown filter values. With every chunk in
-- scope that generic plan computed exact distances over all embeddings (~12 s at 23k chunks) and unscoped
-- searches hit the 8 s PostgREST timeout. This version is PL/pgSQL with dynamic SQL, so each call is
-- planned with the filters actually given, and it picks the vector strategy explicitly:
--   * small scope (one lecture, a small course: <= 1000 chunks): exact distances, as before;
--   * large scope: the half-precision HNSW index with iterative scans. The scope filter is written so it
--     cannot use chunks_source_idx, which forces the planner onto the HNSW index.
-- Full-text half: still an OR of the question's terms ranked with ts_rank_cd on all terms, but rows are
-- matched only on the rarer terms (in <= 2% of chunks, per ANALYZE's lexeme statistics in pg_stats; at
-- least the 2 rarest terms are always kept). Words like "system" or "energy" matched ~40% of the corpus
-- and ranking every match took ~1.2 s. Lexemes missing from pg_stats are rare by definition, so they are
-- always kept. Same signature and output as 0006/0012, so the backend does not change.

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
language plpgsql stable
set search_path = public
set hnsw.iterative_scan = relaxed_order
set hnsw.ef_search = 100
as $fn$
declare
  exact_max constant int := 1000;      -- scopes up to this many chunks use exact distances
  common_freq constant real := 0.02;   -- terms in more than 2% of chunks are not used for matching
  rank_q text := nullif(replace(plainto_tsquery('english', query_text)::text, '&', '|'), '');
  match_q text;
  scope_sql text := 's.status = ''ready''';
  scoped_ids uuid[];
  n_scope int;
  nearest_sql text;
begin
  if filter_type is not null then scope_sql := scope_sql || ' and s.type = $1'; end if;
  if filter_course is not null then scope_sql := scope_sql || ' and (s.course_id is null or s.course_id = $2)'; end if;
  if filter_source is not null then scope_sql := scope_sql || ' and s.id = $3'; end if;
  execute format('select coalesce(array_agg(s.id), ''{}'') from sources s where %s', scope_sql)
    into scoped_ids using filter_type, filter_course, filter_source;
  select count(*) into n_scope from chunks c where c.source_id = any(scoped_ids);

  if rank_q is not null then
    with stats as (
      select st.most_common_elems::text::text[] as elems, st.most_common_elem_freqs as freqs
      from pg_stats st
      where st.schemaname = 'public' and st.tablename = 'chunks' and st.attname = 'fts'
    ),
    terms as (
      select t.lex,
             coalesce((select st.freqs[array_position(st.elems, t.lex)] from stats st), 0) as freq
      from unnest(tsvector_to_array(to_tsvector('english', query_text))) as t(lex)
    ),
    ranked as (select lex, freq, row_number() over (order by freq, lex) as rn from terms)
    select string_agg(quote_literal(lex), ' | ') into match_q
    from ranked where freq <= common_freq or rn <= 2;
  end if;

  if n_scope <= exact_max then
    nearest_sql := 'select c.id, c.embedding::halfvec(1024) <=> $1::halfvec(1024) as dist
      from chunks c where c.source_id = any($3)
      order by 2 limit $2 * 2';
  else
    -- source_id::text keeps chunks_source_idx out of the plan, so the HNSW index is used.
    nearest_sql := 'select c.id, c.embedding::halfvec(1024) <=> $1::halfvec(1024) as dist
      from chunks c where c.source_id::text = any($3::text[])
      order by c.embedding::halfvec(1024) <=> $1::halfvec(1024) limit $2 * 2';
  end if;

  return query execute format($q$
    with full_text as (
      select c.id, row_number() over (order by ts_rank_cd(c.fts, to_tsquery('english', $4)) desc) as rank_ix
      from chunks c
      where $5 is not null
        and c.fts @@ to_tsquery('english', $5)
        and c.source_id = any($3)
      order by rank_ix
      limit $2 * 2
    ),
    nearest as (%s),
    semantic as (select id, row_number() over (order by dist) as rank_ix from nearest)
    select coalesce(f.id, s.id) as chunk_id,
           (coalesce(1.0 / ($6 + f.rank_ix), 0.0) + coalesce(1.0 / ($6 + s.rank_ix), 0.0))::double precision
    from full_text f
    full outer join semantic s on f.id = s.id
    order by 2 desc
    limit $2
  $q$, nearest_sql)
  using query_embedding, match_count, scoped_ids, rank_q, match_q, rrf_k;
end;
$fn$;

revoke execute on function hybrid_search(text, vector, int, text, uuid, int, uuid) from public, anon, authenticated;
grant execute on function hybrid_search(text, vector, int, text, uuid, int, uuid) to service_role;
