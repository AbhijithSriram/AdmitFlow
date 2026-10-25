# AdmitFlow SRD v1.1: changes from v1.0 and security checklist

[AdmitFlow_SRD.docx](../AdmitFlow_SRD.docx) is v1.0 (14 August 2026). This file records where the delivered system
differs from it, why, and the evidence for the security checklist in SRD section 11. The team accepted these
changes on 24 October 2026 (decision 6 in [REMAINING_WORK.md](../REMAINING_WORK.md)).

## 1. Deviations from v1.0

| SRD item | v1.0 says | v1.1 (delivered) | Why |
|---|---|---|---|
| FR-6.1 Guidelines | "I Agree & Proceed" is disabled until the applicant scrolls to the bottom | The full guidelines are shown; the button is enabled by an "I have read and understood the guidelines above" checkbox. The acceptance timestamp is still stored. | Nine short guidelines fit on screen, so a scroll gate forced applicants to scroll a tiny box for no reason. An explicit acknowledgement is clearer and is still recorded. |
| FR-6.5 / FR-6.6 Step order | Step 3 Academic, Step 4 Programme | Step 3 Programme, Step 4 Academic | The academic questions depend on the programme (next row), so the programme must be chosen first. Migration 004 moves drafts saved under the old order. |
| FR-6.5 Academic details | Every applicant gives a UG degree | B.Tech (undergraduate entry) gives Class XII and Class X; M.Tech, MCA and M.Sc. give the UG degree plus Class XII and Class X. Class XII can be "appearing / results awaited" for B.Tech. Switching between UG and PG programmes clears the other kind's answers. | A B.Tech applicant has no UG degree. Applications close on 31 March but Class XII results come out in May. |
| FR-6.8 Documents | Photo and signature must be PNG | JPEG, PNG, WebP, GIF or BMP, judged by the file's contents; the same size and dimension limits | A photograph rarely fits in 500 KB as a PNG. HEIC, TIFF and SVG are still refused (browsers cannot show them in the admin viewer). |

## 2. Additions beyond v1.0 (no requirement changed)

- **Text-only fields.** Names, religion, mother tongue, places, degree, specialisation, college and school accept
  letters in any script (and digits only where real names have them, such as towns and colleges), enforced in the
  form and again by the API (`backend/app/services/field_rules.py`).
- **Browser Back/Forward in the form (NFR-4).** The step is in the URL (`/application?step=N`), so Back, Forward
  and refresh move between steps; every auto-save keeps the local draft current.
- **Payment safety (FR-6.9).** A late "dismissed" or "failed" report can never undo a successful payment, a repeated
  confirmation is not processed or emailed twice, and a second payment for a paid application is recorded for refund.
  Retry Payment is offered on the dashboard.
- **Exports are audited (FR-11).** Every CSV/PDF export writes an audit entry first; CSV cells are protected against
  spreadsheet formula injection; exports include the latest aptitude score.
- **Aptitude test details (FR-10, team decisions 1-4).** Each question has its own marks, which must add up to the
  total before publishing; one attempt per test (an admin can reset one); students never see scores; "shortlisted"
  means a paid applicant scoring at or above the pass marks. The timer is the server's.
- **Operations.** Nightly database and file backups with a tested restore (README, "Backups and restore"); a database
  dump before every update; the test suite refuses to wipe anything but a local database named like `*_test`.

## 3. Deployment differs from SRD section 5.3

| SRD 5.3 | Delivered (homeserver) | Why |
|---|---|---|
| Nginx on port 80 (public) | Nginx on 127.0.0.1:8088, reached only through a Cloudflare tunnel at `https://admitflow.abhijith-sriram.in` | The server is shared and not exposed directly; Cloudflare provides HTTPS. |
| Gunicorn on 5000 with 4 workers | Gunicorn on 127.0.0.1:5001 with 2 workers | Port 5000 belongs to another app on the machine; 2 workers is ample for this load. |
| MinIO 9000/9001, PostgreSQL 5432 | Same ports, bound to 127.0.0.1 | Unchanged, loopback-only. |
| Presigned links name the MinIO host | Links are signed for the public host (`MINIO_PUBLIC_ENDPOINT`) and nginx forwards `/admitflow/` to MinIO | A visitor's browser cannot open `127.0.0.1:9000`. |

## 4. Security checklist (SRD section 11)

| Item | Status | Where |
|---|---|---|
| Password hashing: bcrypt, cost 12 or more | Done | `BCRYPT_LOG_ROUNDS = 12` in `backend/app/config.py`; Flask-Bcrypt for students and admins |
| OTP storage: bcrypt hash, never raw | Done | `otp_service.create_otp_token` stores `bcrypt.generate_password_hash(raw_otp)`; a code is burned after 5 wrong guesses |
| Session isolation: separate cookie names | Done | `admitflow_student_session` and `admitflow_admin_session` (`config.py`); admin sessions are server-side rows, cookie scoped to `/api/admin` |
| Admin route guard | Done | `@admin_required` (`middleware/admin_guard.py`) on every `/api/admin/*` route; a student cookie gets 403 |
| Student route guard | Done | `@login_required` (`middleware/auth_guard.py`); `tests/test_extension_scaffold.py` checks every extension route needs a session |
| Payment verification: HMAC-SHA256 server-side | Done | `payment_service.verify_signature` (`hmac.compare_digest`) before anything is marked PAID |
| File validation: MIME, size, dimensions on the server | Done | `upload_document` in `blueprints/application.py`: Pillow decodes the image, the format comes from the contents |
| Private file access: 15-minute presigned URLs | Done | `MINIO_PRESIGNED_URL_EXPIRY_SECONDS = 15 * 60`; the bucket is private and nginx allows only GET/HEAD on `/admitflow/` |
| Environment secrets: in .env, .env git-ignored | Done | `.gitignore` lists `.env`; no `.env` is tracked; on the server secrets live in root-only `/etc/admitflow.env` |
| Security headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS | Done | `register_security_headers` in `app/__init__.py`; the site's CSP and HSTS are set by nginx (`deploy/homeserver/admitflow.nginx.conf`) |
| Rate limiting on login and signup | Done | Flask-Limiter `10 per minute` on signup, send-otp, login, admin login (verify-otp 5/min); nginx `limit_req` 10/min per visitor (Flask-Limiter counts per worker, so nginx is the binding limit) |
| Account lockout: 5 failures, 15 minutes | Done | `LOGIN_LOCKOUT_ATTEMPTS = 5`, `LOGIN_LOCKOUT_MINUTES = 15`, enforced in `auth.login` |
| CORS: dev only; production same-origin | Done | `CORS_ORIGINS` for local development; in production nginx serves the site and the API from one origin |
| Audit log written before the action | Done | `admin_service.write_audit`, in its own transaction, before hard delete, export and test publish/assign/reset, with a `_FAILED` entry if the action then fails. Seat-number changes (not destructive) are audited just after saving. |
| No raw secrets in logs | Done | `logging_config.RedactFilter`; tests check passwords, OTPs, signatures and secrets never reach the log |

## 5. Still open

- **Real content.** The guidelines, programmes, fee, dates, contact details, registration-number format, seat numbers
  and college list are demo placeholders (`frontend/src/content/institution.js`, migration 006).
- **Live verification.** The hosted Razorpay checkout, real email delivery and reCAPTCHA on the live domain are being
  tested on the live site.
