-- Processing stage shown in the upload card: preparing → transcribing → flagging → indexing → notes.
alter table sources add column if not exists stage text;
