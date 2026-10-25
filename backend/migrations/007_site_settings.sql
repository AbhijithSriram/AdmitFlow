-- Site content an admin can edit from the portal (institution name, contact, dates, guidelines,
-- eligibility, documents, fee, college suggestions, programmes). One row per section; a section
-- without a row uses the defaults in backend/app/content_defaults.json, so a new deployment works
-- before anyone edits anything. Safe to run repeatedly.
--   psql <db> -f backend/migrations/007_site_settings.sql
CREATE TABLE IF NOT EXISTS site_settings (
    key        VARCHAR(50) PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES admins (id) ON DELETE SET NULL
);
