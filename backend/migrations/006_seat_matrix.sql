-- Seat matrix for the ERP statistics view (SRD FR-11): how many seats each programme and
-- specialisation has. Editable by an admin through PUT /api/admin/seats. Safe to run repeatedly:
-- the table is created only if missing, and the demo seats are inserted only where no row exists,
-- so seat numbers an admin has already changed are never overwritten.
--   psql <db> -f backend/migrations/006_seat_matrix.sql
CREATE TABLE IF NOT EXISTS programme_seats (
    programme      VARCHAR(100) NOT NULL,
    specialisation VARCHAR(100) NOT NULL,
    seats          INTEGER NOT NULL CHECK (seats >= 0),
    PRIMARY KEY (programme, specialisation)
);

-- Demo values. The names must match PROGRAMMES in frontend/src/content/institution.js.
INSERT INTO programme_seats (programme, specialisation, seats) VALUES
    ('B.Tech', 'CSE', 120),
    ('B.Tech', 'IT', 60),
    ('B.Tech', 'ECE', 60),
    ('B.Tech', 'EEE', 60),
    ('B.Tech', 'Mechanical', 60),
    ('B.Tech', 'Civil', 60),
    ('M.Tech', 'Computer Science', 18),
    ('M.Tech', 'VLSI Design', 18),
    ('M.Tech', 'Data Science', 18),
    ('M.Tech', 'Structural Engineering', 18),
    ('MCA', 'General', 60),
    ('M.Sc.', 'Computer Science', 30),
    ('M.Sc.', 'Mathematics', 30),
    ('M.Sc.', 'Physics', 30),
    ('M.Sc.', 'Data Science', 30)
ON CONFLICT (programme, specialisation) DO NOTHING;
