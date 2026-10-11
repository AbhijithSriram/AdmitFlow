-- Counts wrong guesses against each one-time code so it can be burned after 5 (brute-force
-- protection). Safe to run on an existing database (idempotent); fresh installs already get
-- this column from schema.sql:   psql <db> -f backend/migrations/003_otp_attempts.sql
ALTER TABLE otp_tokens ADD COLUMN IF NOT EXISTS failed_attempts INTEGER NOT NULL DEFAULT 0;
