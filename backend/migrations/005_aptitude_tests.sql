-- Aptitude test columns (SRD FR-10), exactly as agreed in REMAINING_WORK.md section 3.1. A row in
-- test_submissions is the assignment: the admin creates it, the student's start sets started_at.
-- Safe to run on an existing database (idempotent):   psql <db> -f backend/migrations/005_aptitude_tests.sql
ALTER TABLE test_papers     ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE test_questions  ADD COLUMN IF NOT EXISTS marks        INTEGER NOT NULL DEFAULT 1;
ALTER TABLE test_submissions ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP NOT NULL DEFAULT now();
ALTER TABLE test_submissions ADD COLUMN IF NOT EXISTS started_at  TIMESTAMP;   -- the server-side timer starts here
-- one assignment per applicant per test:
CREATE UNIQUE INDEX IF NOT EXISTS uq_test_submissions_app_paper ON test_submissions (application_id, test_paper_id);
