-- AdmitFlow PostgreSQL schema
-- UUID primary keys via gen_random_uuid() to prevent sequential ID enumeration.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE students (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name             VARCHAR(255) NOT NULL,
    date_of_birth         DATE NOT NULL,
    gender                VARCHAR(20) NOT NULL,
    email                 VARCHAR(255) UNIQUE NOT NULL,
    phone                 VARCHAR(10) UNIQUE NOT NULL,
    password_hash         VARCHAR(255),
    email_verified        BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until          TIMESTAMP,
    created_at            TIMESTAMP NOT NULL DEFAULT now(),
    updated_at            TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_students_email ON students (email);
CREATE INDEX idx_students_phone ON students (phone);

CREATE TABLE otp_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    otp_hash    VARCHAR(255) NOT NULL,
    purpose     VARCHAR(30) NOT NULL, -- email_verification | password_reset
    expires_at  TIMESTAMP NOT NULL,
    consumed_at TIMESTAMP,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE applications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id              UUID NOT NULL UNIQUE REFERENCES students (id) ON DELETE CASCADE,
    status                  VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED',
    guidelines_accepted_at  TIMESTAMP,
    programme               VARCHAR(255),
    specialisation          VARCHAR(255),
    photo_url               VARCHAR(500),
    signature_url           VARCHAR(500),
    id_proof_url            VARCHAR(500),
    pdf_url                 VARCHAR(500),
    created_at              TIMESTAMP NOT NULL DEFAULT now(),
    updated_at              TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_applications_status ON applications (status);
CREATE INDEX idx_applications_created_at ON applications (created_at);

CREATE TABLE form_drafts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    step_number    INTEGER NOT NULL,
    data           JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at     TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (application_id, step_number)
);

CREATE TABLE payments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id       UUID NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    razorpay_order_id    VARCHAR(255),
    razorpay_payment_id  VARCHAR(255),
    razorpay_signature   VARCHAR(255),
    amount               NUMERIC(10, 2) NOT NULL,
    status               VARCHAR(20) NOT NULL DEFAULT 'CREATED', -- CREATED | SUCCESS | FAILED
    created_at           TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE admins (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id          UUID REFERENCES admins (id),
    action_type       VARCHAR(50) NOT NULL,
    target_student_id UUID,
    target_email      VARCHAR(255), -- denormalised: survives deletion of the student record
    details           JSONB,
    created_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE test_papers (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title             VARCHAR(255) NOT NULL,
    duration_minutes  INTEGER NOT NULL,
    total_marks       INTEGER NOT NULL,
    pass_marks        INTEGER NOT NULL,
    created_by        UUID REFERENCES admins (id),
    created_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE test_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_paper_id   UUID NOT NULL REFERENCES test_papers (id) ON DELETE CASCADE,
    question_text   TEXT NOT NULL,
    option_a        VARCHAR(500) NOT NULL,
    option_b        VARCHAR(500) NOT NULL,
    option_c        VARCHAR(500) NOT NULL,
    option_d        VARCHAR(500) NOT NULL,
    correct_option  CHAR(1) NOT NULL CHECK (correct_option IN ('A', 'B', 'C', 'D'))
);

CREATE TABLE test_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    test_paper_id   UUID NOT NULL REFERENCES test_papers (id),
    answers         JSONB NOT NULL DEFAULT '{}'::jsonb,
    score           NUMERIC(6, 2),
    submitted_at    TIMESTAMP
);
