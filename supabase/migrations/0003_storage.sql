-- Private bucket for lecture audio and PDFs. Playback uses short-lived signed URLs.
insert into storage.buckets (id, name, public)
values ('sources', 'sources', false)
on conflict (id) do nothing;
