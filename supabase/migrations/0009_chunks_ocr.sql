-- Chunks read by OCR from scanned pages or handwriting. Shown with a "Scanned" badge so students check the original.
alter table chunks add column if not exists ocr boolean not null default false;
