-- The application form used to ask for Academic details (step 3) before the Programme (step 4).
-- The academic questions now depend on the programme (B.Tech asks for Class XII and Class X; the
-- postgraduate programmes ask for the UG degree as well), so the programme is chosen first:
-- step 3 is now the Programme and step 4 the Academic details.
--
-- This moves drafts saved under the old numbering. Safe to run any number of times: it only touches
-- rows that still have the OLD shape (a step-3 row holding UG-degree fields, a step-4 row holding a
-- programme), and a row in the new layout never looks like that. Fresh databases have no such rows.
--   psql <db> -f backend/migrations/004_swap_programme_and_academic_steps.sql
BEGIN;

-- Park the rows on spare step numbers first: swapping 3 and 4 directly would collide with the
-- UNIQUE (application_id, step_number) constraint half way through.
UPDATE form_drafts SET step_number = 104
 WHERE step_number = 3
   AND data ?| ARRAY['ug_degree', 'ug_specialisation', 'college', 'university', 'passing_year'];

UPDATE form_drafts SET step_number = 103
 WHERE step_number = 4
   AND data ? 'programme';

UPDATE form_drafts SET step_number = 3 WHERE step_number = 103;
UPDATE form_drafts SET step_number = 4 WHERE step_number = 104;

COMMIT;
