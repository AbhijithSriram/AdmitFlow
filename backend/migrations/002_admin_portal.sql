-- Person 4: admin portal additions. Safe to run on an existing database
-- (all statements are idempotent):  psql <db> -f backend/migrations/002_admin_portal.sql
-- Fresh installs: run schema.sql first, then this file.

-- Server-side admin sessions. Admins get their own cookie (ADMIN_SESSION_COOKIE_NAME),
-- fully separate from the student Flask-Session cookie (SRD FR-7.1). Only a SHA-256
-- of the cookie token is stored, so a DB leak cannot be replayed as a session.
CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash    VARCHAR(64) PRIMARY KEY,
    admin_id      UUID NOT NULL REFERENCES admins (id) ON DELETE CASCADE,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    last_seen_at  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_admin_sessions_admin_id ON admin_sessions (admin_id);

-- audit_log is append-only: no UPDATE or DELETE, even by the application user.
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_log_append_only ON audit_log;
CREATE TRIGGER trg_audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at);
