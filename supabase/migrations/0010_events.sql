-- Calendar: exams, quizzes, assignments and deadlines per course.
-- 'suggested' events were extracted from documents and wait for a student/admin to confirm them.
create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  type text not null check (type in ('exam', 'quiz', 'assignment', 'lab', 'deadline', 'class', 'other')),
  course_id uuid references courses(id) on delete cascade,
  section_id uuid references sections(id) on delete set null,
  starts_at timestamptz,            -- when an assignment opens (drives the green → red urgency)
  due_at timestamptz not null,      -- exam start or deadline
  all_day boolean not null default false,
  location text,
  notes text,
  source_id uuid references sources(id) on delete set null,
  page int,
  status text not null default 'confirmed' check (status in ('confirmed', 'suggested')),
  created_at timestamptz not null default now()
);
create index if not exists events_due_idx on events (due_at);
create index if not exists events_course_idx on events (course_id);
alter table events enable row level security;
