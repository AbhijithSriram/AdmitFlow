# AdmitFlow — Remaining Work (SRD gap analysis and 4-person split)

Module 1 (the Admissions Core) is built, merged and running on the homeserver. This document lists what the
[SRD](AdmitFlow_SRD.docx) still asks for, checked against the actual code on `main`, and splits it into four
independent workstreams in the same style as [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) (read its sections 0–1
and 5 again: the branching rules and the learning links still apply).

---

## 1. Where we are against the SRD

| SRD item | Status | Note |
|---|---|---|
| FR-1 Landing page | Done | Content is still demo placeholder text (see Person 3, task C5) |
| FR-2 Registration + reCAPTCHA | Done | |
| FR-3 OTP + password setup | Done | |
| FR-4 Login, lockout, session, forgot password, logout | Done | |
| FR-5 Applicant dashboard | **Partial** | No "Retry Payment" button for a `PAYMENT_PENDING` application |
| FR-6.1 Guidelines step | Done, **differs from SRD** | Scroll-to-bottom was replaced by an "I have read and understood" checkbox |
| FR-6.2 Auto-save + rehydrate | Done | |
| FR-6.3 – 6.4 Personal, address (pincode auto-fill) | Done | |
| FR-6.5 – 6.6 Academic, programme | Done, **differs from SRD** | Programme is now Step 3 and Academic Step 4; B.Tech asks Class XII/X, PG asks UG degree too |
| FR-6.7 Entrance details | Done | Registration-number format is a placeholder (6–15 letters/digits) |
| FR-6.8 Document uploads | Done, **differs from SRD** | Photo/signature accept JPEG, PNG, WebP, GIF, BMP (SRD says PNG) |
| FR-6.9 Preview and payment | Done | Retry Payment on the dashboard is the missing piece (FR-5) |
| FR-7.1 – 7.3 Admin portal, hard delete | Done | |
| FR-8 PDF generation | Done | |
| FR-9 Email notifications | Done | |
| **FR-10 Online aptitude test (Module 2)** | **Not started** | Tables and models exist; no routes, no pages |
| **FR-11 ERP statistics view (Module 3)** | **Not started** | Nothing exists |
| NFR-1 Security | Done | Rate-limit counters are per Gunicorn worker (the nginx limit is the real one) |
| NFR-2 Reliability | Done | |
| NFR-3 Performance | Done | Indexes and 20-per-page exist; load times never measured |
| NFR-4 Usability | **Partial** | Browser Back button leaves the form instead of going to the previous step |
| NFR-5 Maintainability | Mostly done | Backend tests: 171. Frontend: no automated tests |
| NFR-6 Auditability | **Partial** | Admin actions are audited; OTP dispatch, login failures, payment created/confirmed are not logged |
| §5.3 Deployment | Done | Homeserver install script; no backups yet |

**So what remains:** two extension modules (FR-10, FR-11), four small core gaps (Retry Payment, audit logging,
Back-button navigation, rate-limit storage), content/documentation, and operations (backups, live verification).

---

## 2. Decisions that change what people build

These are **settled**: the recommended option was approved, and the answers are recorded in section 7. They are kept
here with their reasoning so you can see why.

1. **Marks:** does every question carry equal marks? *Recommended:* each question has its own `marks` (default 1), and
   `total_marks` must equal their sum when the paper is published.
2. **Retakes:** one attempt per student per test. *Recommended:* yes, one attempt; an admin can reset a submission.
3. **Do students see their score?** *Recommended:* no, only admins (the SRD only says the admin dashboard shows it).
4. **"Shortlisted" in the seat matrix** (SRD §2 Module 3). Merit lists are out of scope, so *recommended:* shortlisted =
   a PAID application whose aptitude score is at or above the pass marks. With no test assigned, it shows 0.
5. **Seat numbers:** where do they come from? *Recommended:* an admin-editable table (Person 2 builds it), seeded
   with demo values.
6. **SRD changes:** record the three deviations in the table above as "SRD v1.1" so the report matches the software.

---

## 3. Contracts (so you can work in parallel without waiting on each other)

### 3.1 Database changes — two new migration files, one owner each

Nobody edits `schema.sql`. New columns go in numbered migration files (they must be safe to run repeatedly, like
`003`/`004`). `deploy/homeserver/install.sh` applies every `NNN_*.sql` file in numeric order on each run, so adding
the file is all it takes: do not edit `install.sh` for a migration.

**`backend/migrations/005_aptitude_tests.sql` — owner Person 4, merged FIRST (day 1)**
```sql
ALTER TABLE test_papers     ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE test_questions  ADD COLUMN IF NOT EXISTS marks        INTEGER NOT NULL DEFAULT 1;
ALTER TABLE test_submissions ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP NOT NULL DEFAULT now();
ALTER TABLE test_submissions ADD COLUMN IF NOT EXISTS started_at  TIMESTAMP;   -- the server-side timer starts here
-- one assignment per applicant per test:
CREATE UNIQUE INDEX IF NOT EXISTS uq_test_submissions_app_paper ON test_submissions (application_id, test_paper_id);
```
A row in `test_submissions` **is** the assignment: created by the admin at assign time with `started_at` and
`submitted_at` empty; the student fills them in.
(A paper that already has submissions cannot be deleted, because `test_submissions.test_paper_id` has no cascade.
Admins un-publish it instead.)

**`backend/migrations/006_seat_matrix.sql` — owner Person 2**
```sql
CREATE TABLE IF NOT EXISTS programme_seats (
    programme      VARCHAR(100) NOT NULL,
    specialisation VARCHAR(100) NOT NULL,
    seats          INTEGER NOT NULL CHECK (seats >= 0),
    PRIMARY KEY (programme, specialisation)
);
```

### 3.2 API contracts (envelope as everywhere: `{success, data}` / `{success: false, error}`)

**Admin side, Person 4** (all `@admin_required`)
| Method | Endpoint | Purpose |
|---|---|---|
| GET / POST | `/api/admin/tests` | List papers / create a paper with its questions |
| GET / PUT / DELETE | `/api/admin/tests/:id` | Read / edit (only while unpublished) / delete (only without submissions) |
| POST | `/api/admin/tests/:id/publish` | Check marks add up, then publish |
| POST | `/api/admin/tests/:id/assign` | Body `{programme?, specialisation?}`; assigns to PAID applicants; returns `{assigned: n}` |
| GET | `/api/admin/tests/:id/results` | Paginated: applicant, score, pass/fail, submitted_at |
| POST | `/api/admin/tests/:id/reset/:application_id` | Allow one more attempt |

**Student side, Person 1** (all `@login_required`, PAID applicants only)
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/student/tests` | Assigned tests with `status`: ASSIGNED / IN_PROGRESS / SUBMITTED |
| POST | `/api/student/tests/:paper_id/start` | Sets `started_at` once; returns questions (**never `correct_option`**) and `deadline` |
| PUT | `/api/student/tests/:paper_id/answers` | Saves `{question_id: "A".."D"}`; refused after the deadline |
| POST | `/api/student/tests/:paper_id/submit` | Grades, stores `score`, sets `submitted_at` |

**Stats side, Person 2** (`@admin_required`)
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/admin/stats/summary` | Registrations, applications started, paid, pending |
| GET | `/api/admin/stats/programmes` | Per programme/specialisation: seats, applied, paid, shortlisted |
| GET | `/api/admin/stats/registrations?from=&to=` | `[{date, count}]` for the chart |
| GET / PUT | `/api/admin/seats` | Read / set seat numbers |

**Export side, Person 3** (`@admin_required`)
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/admin/export/applicants.csv` | Same filter parameters as `/api/admin/students` |
| GET | `/api/admin/export/applicants.pdf` | Same, rendered with WeasyPrint |

### 3.3 Step 0 — scaffold (DONE)

To avoid the shared-file conflicts from last time, one scaffold commit already did the shared edits. After it,
**nobody edits `app/__init__.py`, `App.jsx` or `api/client.js`** for this work; you only replace the stubs in the
files you own below.

- **Backend stubs** (each route exists, is behind the right guard, and answers `501 Not implemented`), registered in
  `app/__init__.py`: `admin_tests.py` → `/api/admin/tests` (P4), `student_tests.py` → `/api/student/tests` (P1),
  `admin_stats.py` → `/api/admin/stats/*` and `/api/admin/seats` (P2), `admin_export.py` → `/api/admin/export/*` (P3).
  Admin routes must stay under `/api/admin`, because the admin session cookie is only sent to that path.
- **Frontend placeholders and routes** in `App.jsx`: `/tests` (`Tests.jsx`) and `/tests/:paperId` (`TakeTest.jsx`) (P1);
  `/admin/tests` (`AdminTests.jsx`), `/admin/tests/new` and `/admin/tests/:paperId` (`TestEditor.jsx`) (P4);
  `/admin/stats` (`AdminStats.jsx`) (P2). `TestsCard.jsx` (P1) is already mounted in the student dashboard for PAID
  applicants and renders nothing until it is built.
- **API client functions** already in `api/client.js`: `studentTestsApi`, `adminTestsApi`, `adminStatsApi`,
  `adminExportApi`. Use them as they are; if a signature is wrong for you, tell the group rather than editing it.
- **`backend/tests/test_extension_scaffold.py`** pins the guard behaviour of every new route. Keep the "needs a session"
  tests when you implement a route; only replace the "answers 501" test of your routes with real tests.

The two migration files (`005`, `006`) are not part of the scaffold: their owners write them (section 3.1).

---

## 4. Task split

### Person 1 — Student aptitude test (FR-10, student side) + auth-side audit logging

**Covers:** SRD FR-10 (applicant sees the test with a countdown, auto-submit at expiry, auto-grade) · NFR-6 (auth events)

**Your files:**
```
backend/app/blueprints/student_tests.py          (new)
backend/app/services/test_service.py             (new: grading, deadline logic)
backend/tests/test_student_tests.py              (new)
frontend/src/pages/Tests.jsx                     (new: list)
frontend/src/pages/TakeTest.jsx                  (new: the timed test)
frontend/src/components/TestsCard.jsx            (new: shown on the dashboard)
backend/app/blueprints/auth.py                   (audit logging only)
```

**Build order:**
1. **Grading function first** — `grade(paper, answers) -> score`. Pure Python, no web: write its tests before anything else.
2. **`GET /student/tests`** and **`start`**. `start` is idempotent: the second call returns the same `deadline`
   (`started_at + duration`), never a fresh one. Never include `correct_option` in any response (write a test that
   searches the response for it).
3. **The timer is the server's, not the browser's.** The page shows a countdown computed from the server's
   `deadline`, but the server is what refuses late answers. Reading the clock only in JS would let anyone extend
   the test from the dev tools.
4. **`answers` auto-save** on every selection (reuse your understanding of `useAutoSave`; see how it debounces).
5. **`submit` + auto-submit.** At 0:00 the page submits whatever is selected. Also handle the browser being closed:
   when `/student/tests` or `start` is called after the deadline for an unsubmitted test, grade it then ("lazy submit").
6. **`TakeTest.jsx`:** question navigator, countdown, a confirmation before manual submit, a warning at 1 minute left.
7. **`TestsCard.jsx`:** list assigned tests on the dashboard. It is already mounted in `Dashboard.jsx` (for PAID
   applicants), so you only edit your own file.
8. **Audit logging (NFR-6):** add `log.info`/`log.warning` lines in `auth.py` for OTP dispatch, login failure
   (log the student id, never the email or password), logout. Extend the redaction test so a password or OTP in a
   log line is caught.

**Definition of done:** a paid applicant with an assigned test sees it on the dashboard, takes it with a working
countdown, and is graded on submit or at expiry (even if they close the tab). A student cannot see correct answers,
cannot answer after the deadline, and cannot start a second attempt.

---

### Person 2 — ERP statistics view (FR-11) + form navigation

**Covers:** SRD FR-11 (cards, programme table, time-series chart) · NFR-4 (Back-button navigation) · FR-6.5 (optional college list)

**Your files:**
```
backend/migrations/006_seat_matrix.sql           (new)
backend/app/blueprints/admin_stats.py            (new)
backend/app/services/stats_service.py            (new: the SQL)
backend/tests/test_admin_stats.py                (new)
frontend/src/pages/Admin/AdminStats.jsx          (new)
frontend/src/pages/ApplicationForm.jsx           (Back-button work)
frontend/src/content/institution.js              (college list, seat defaults)
```

**Build order:**
1. **`006` migration + `seats` endpoints.** Seed demo seat numbers for the four programmes.
2. **`/stats/summary`:** four counts from `students` and `applications` (`PAID`, `PAYMENT_PENDING`, started =
   status not `NOT_STARTED`). Do it as one query with `COUNT(*) FILTER (WHERE ...)`; learn that syntax.
3. **`/stats/programmes`:** `GROUP BY programme, specialisation`, `LEFT JOIN programme_seats` so a programme with no
   applications still shows. "Shortlisted" follows the team decision in section 2.
4. **`/stats/registrations`:** counts per day with `date_trunc('day', created_at)`. Fill in days with zero registrations
   so the chart has no gaps.
5. **`AdminStats.jsx`:** summary cards, the programme table, and the chart. Use a charting library pinned to an exact
   version (recommended: `recharts`), and read its "Getting started" page first.
6. **Back-button navigation (NFR-4):** put the step in the URL (`/application/3`) with React Router so the browser Back
   and Forward buttons move between steps, and a refresh stays on the same step. Keep the existing "save before
   advancing" rule.
7. **Optional:** a searchable college/university list (FR-6.5) from a configurable array, using an HTML `<datalist>`.
   Free text must still be allowed.

**Definition of done:** an admin opens `/admin/stats`, sees correct totals that match the applicant table, the
seats-vs-applied-vs-paid table and the daily-registrations chart; browser Back moves one form step instead of
leaving the form.

---

### Person 3 — Exports, payment gaps, content, operations

**Covers:** SRD FR-11 (CSV/PDF export) · FR-5 / FR-6.9 (Retry Payment) · NFR-6 (payment events) · deployment and quality

**Your files:**
```
backend/app/blueprints/admin_export.py           (new)
backend/app/services/export_service.py           (new)
backend/tests/test_admin_export.py               (new)
frontend/src/pages/Dashboard.jsx                 (Retry Payment, mount TestsCard)
frontend/src/hooks/usePayment.js
backend/app/blueprints/payment.py                (logging only)
frontend/src/content/institution.js              (real content: coordinate with Person 2's edits)
deploy/homeserver/*, README.md, SRD change log
```

**Build order:**
1. **Step 0 scaffold** (section 3.3): done.
2. **Retry Payment (FR-5):** when the dashboard status is `PAYMENT_PENDING`, show a "Retry Payment" button that
   opens the payment step. Test the whole failure path: dismiss the Razorpay modal, check the badge and the button.
3. **Payment logging (NFR-6):** `INFO` lines for payment order created and payment confirmed (order id and application
   id only; never keys or signatures).
4. **CSV export:** stream rows with the filters of `/api/admin/students`. Ask Person 4 to expose the query builder
   from `admin_service.py` as a function you can call (do not copy the filter logic). Protect against **CSV formula
   injection**: a cell starting with `=`, `+`, `-` or `@` must be prefixed with a quote, because an applicant controls
   their own name. Cap the row count.
5. **PDF export:** reuse `pdf_service.py` and WeasyPrint to render the same rows as a table.
6. **Audit the export:** every export writes an `audit_log` row (admin, filters, row count). Exports contain personal
   data, so this matters.
7. **C5 — Real content:** the guidelines, programmes and specialisations, fee, key dates, contact details and the
   registration-number format are demo placeholders in `content/institution.js`. Collect the real ones from the
   team and replace them (and keep the fee in step with `APPLICATION_FEE_PAISE` in `payment.py`).
8. **Operations on the homeserver:** a nightly `pg_dump` of the `admitflow` database and a copy of
   `/srv/nas/admitflow/minio` to a second location, with a tested restore; `journald` size limit; a short runbook in
   the README (restart, logs, update, restore). Optional: a GitHub Actions workflow running `pytest` against a
   Postgres service plus `npm run build`.
9. **Live verification checklist** once everything is deployed: a real Razorpay test payment through the hosted
   modal, a real confirmation email with the PDF and receipt attachments, the signup reCAPTCHA on the live domain,
   and the whole student journey at 375px, 768px and 1280px widths.
10. **Documentation:** update the SRD to v1.1 with the deviations listed in section 1, and tick the section 11 security
    checklist with the evidence for each line.

**Definition of done:** a failed payment can be retried from the dashboard; an admin can export the filtered
applicant list as CSV and PDF with an audit entry; backups run and a restore has been tested; the live checklist passes.

---

### Person 4 — Admin side of the aptitude test (FR-10) + admin housekeeping

**Covers:** SRD FR-10 (admin creates a test, assigns it, sees scores next to the application) · §6.2 cascade chain

**Your files:**
```
backend/migrations/005_aptitude_tests.sql        (new — merge this FIRST, day 1)
backend/app/blueprints/admin_tests.py            (new)
backend/app/services/admin_test_service.py       (new)
backend/app/services/admin_service.py            (scores in the detail view; expose the query builder)
backend/tests/test_admin_tests.py                (new)
frontend/src/pages/Admin/AdminTests.jsx          (new: list + assign)
frontend/src/pages/Admin/TestEditor.jsx          (new: create/edit with the question editor)
frontend/src/pages/Admin/StudentDetailPanel.jsx  (score section)
frontend/src/pages/Admin/AdminDashboard.jsx      (score column, link to Tests and Stats)
```

**Build order:**
1. **Migration 005** — push it on day 1 so Person 1 can start (section 3.1). Test that it is safe to run twice.
2. **Create a paper** with its questions in one request: validate 4 options, exactly one correct answer, and
   `pass_marks <= total_marks`. Wrap it in one transaction so a paper is never saved half-built.
3. **Publish rule:** a paper can only be assigned once published, and only editable while unpublished. Publishing
   checks that the questions' marks add up to `total_marks`.
4. **Assign:** insert one `test_submissions` row per PAID applicant (optionally filtered by programme and
   specialisation). Use `INSERT ... ON CONFLICT DO NOTHING` so assigning twice never duplicates (this is where
   the unique index from the migration earns its keep). Write an audit-log entry for each assign and reset.
5. **Results:** paginated list per paper; show the score in the applicant detail view and as a column in the
   applicants table.
6. **UI:** `TestEditor.jsx` is the largest piece: add/remove questions, mark the correct option, show a live
   marks total. Build it as a controlled form (`useState` holding an array of questions).
7. **Cascade chain (§6.2):** the hard-delete response must now also list the deleted test submissions. Update the
   service and its test.
8. **Expose the filter/query builder** from `admin_service.py` for Person 3's export.

**Definition of done:** an admin creates and publishes a test, assigns it to all PAID applicants or a filtered
subset, and later sees each applicant's score in the table and detail view; hard-deleting a student removes their
submissions and says so.

---

## 5. Housekeeping (anyone, 15 minutes each)

- Each teammate sets Claude Code's commit and PR attribution to empty in their own settings, so no automated
  co-author trailer appears in the repo history. (Add a short note about this to the README so new contributors see it.)
- Delete the stale remote branch `person4-admin-portal` and re-enable branch protection on `main`.
- Remove the local `backup-main-before-rewrite` tag from the clone that created it.

## 6. Suggested order

| Phase | Who | What |
|---|---|---|
| Done | Person 3 | Step 0 scaffold; the decisions in section 7 |
| Day 1 | Person 4 | Migration 005 merged (Person 1 depends on it) |
| Week 1 | P1 / P2 / P3 / P4 | Each builds their own slice against stub data |
| Week 2 | P1 + P4 | Integrate: assign a real test and take it end to end |
| Week 2 | P2 + P3 | Integrate: export uses P4's query builder; stats and export agree on the same numbers |
| Week 3 | Everyone | Live verification checklist, documentation, demo rehearsal |

## 7. Decisions (settled)

Approved by Abhijith (Person 3) on 24 October 2026; the other three should read them before starting. If you disagree,
raise it now, because they decide what gets built.

1. **Marks per question:** each question has its own `marks` (default 1); `total_marks` must equal their sum when the
   paper is published.
2. **Retakes:** one attempt per student per test. An admin can reset an attempt (`POST .../reset/:application_id`).
3. **Students see scores:** no. Only admins see them.
4. **"Shortlisted" means:** a PAID application whose aptitude score is at or above the test's pass marks. With no test
   assigned it shows 0.
5. **Seat numbers:** an admin-editable table (`programme_seats`, migration 006, built by Person 2), seeded with demo values.
6. **SRD v1.1:** the deviations listed in section 1 (guidelines checkbox, non-PNG photos and signatures, programme before
   academic details) are accepted. Person 3 records them in the SRD.
