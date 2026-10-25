ALTER TABLE test_papers
    ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE test_questions
    ADD COLUMN IF NOT EXISTS marks INTEGER NOT NULL DEFAULT 1;

ALTER TABLE test_submissions
    ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP NOT NULL DEFAULT now();

ALTER TABLE test_submissions
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_test_submissions_app_paper
    ON test_submissions (application_id, test_paper_id);
