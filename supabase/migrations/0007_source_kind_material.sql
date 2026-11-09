-- New source kind 'material': past papers, slides, notes, lab manuals.
-- Course material is searchable but is not 'Official' (no badge, no boost): only handouts and
-- campus regulations describe the current rules. Found in eval tuning (task 2.9), where past-paper
-- cover pages outranked the current handout for weightage and date questions.
alter table sources drop constraint if exists sources_kind_check;
alter table sources add constraint sources_kind_check check (kind in ('campus', 'handout', 'material', 'lecture'));
