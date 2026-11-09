-- Exact flagged moments per lecture: [{start_s, end_s, quote, reason, chunk_id}].
-- Chunks still carry flagged / flag_reason for boosts and badges; a chunk (60–90 s) can hold several moments.
alter table lecture_notes add column if not exists flagged_moments jsonb not null default '[]';
