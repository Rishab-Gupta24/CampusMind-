create extension if not exists vector;

create table courses (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  title text not null
);

create table instructors (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  role text not null check (role in ('ic', 'hod', 'instructor'))
);

create table sections (
  id uuid primary key default gen_random_uuid(),
  course_id uuid not null references courses(id) on delete cascade,
  name text not null,
  instructor_id uuid references instructors(id),
  unique (course_id, name)
);

create table sources (
  id uuid primary key default gen_random_uuid(),
  type text not null check (type in ('pdf', 'lecture')),
  kind text not null check (kind in ('campus', 'handout', 'lecture')),
  title text not null,
  course_id uuid references courses(id),
  section_id uuid references sections(id),
  instructor_id uuid references instructors(id),
  storage_path text,
  pages int,
  duration_s real,
  source_date date,
  status text not null default 'processing' check (status in ('processing', 'ready', 'failed')),
  error text,
  created_at timestamptz not null default now()
);

create table chunks (
  id text primary key,                       -- deterministic: {source_id}_{page|start}_{n}
  source_id uuid not null references sources(id) on delete cascade,
  content text not null,
  embedding vector(1024) not null,
  page int,
  start_s real,
  end_s real,
  flagged boolean not null default false,
  flag_reason text,
  fts tsvector generated always as (to_tsvector('english', content)) stored
);
create index chunks_embedding_idx on chunks using hnsw (embedding vector_cosine_ops);
create index chunks_fts_idx on chunks using gin (fts);
create index chunks_source_idx on chunks (source_id);

create table lecture_notes (
  source_id uuid primary key references sources(id) on delete cascade,
  summary text,
  key_points jsonb default '[]',
  formulas jsonb default '[]',
  quiz jsonb
);

create table answers (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  answer text not null,
  source_chunk_ids jsonb not null,
  scope text,
  created_at timestamptz not null default now()
);

create table feedback (
  id uuid primary key default gen_random_uuid(),
  answer_id uuid not null references answers(id) on delete cascade,
  rating int not null check (rating in (1, -1)),
  created_at timestamptz not null default now()
);

create table unanswered (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  scope text,
  best_score real,
  created_at timestamptz not null default now()
);

-- Security: no login yet, so the browser never talks to Supabase.
-- RLS on with no policies = only the backend's service key can read/write.
alter table courses enable row level security;
alter table instructors enable row level security;
alter table sections enable row level security;
alter table sources enable row level security;
alter table chunks enable row level security;
alter table lecture_notes enable row level security;
alter table answers enable row level security;
alter table feedback enable row level security;
alter table unanswered enable row level security;
