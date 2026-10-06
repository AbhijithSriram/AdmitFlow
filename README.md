# AdmitFlow

Integrated College Admissions & Evaluation Portal — a web-based admissions platform covering student registration, a multi-step application form with continuous auto-save, document upload, online fee payment, and an admin tracking dashboard. See [AdmitFlow_SRD.docx](AdmitFlow_SRD.docx) for the full Software Requirements Document.

## Stack

React (Vite) · Python Flask · PostgreSQL · MinIO · Nginx + Gunicorn

## Project Structure

```
admitflow/
├── frontend/          React JS application (Vite)
│   ├── src/pages/      Top-level page components
│   ├── src/components/ Reusable components
│   ├── src/hooks/      useAutoSave, useFormRehydrate, usePayment
│   ├── src/api/        Centralised API client
│   └── src/context/    AuthContext (student session state)
├── backend/            Flask REST API
│   ├── app/__init__.py     Flask application factory
│   ├── app/blueprints/     Route handlers: auth, application, admin
│   ├── app/services/       otp, email, minio, payment, pdf
│   ├── app/models/         SQLAlchemy model definitions
│   ├── app/middleware/     auth_guard, admin_guard decorators
│   ├── migrations/schema.sql  Full PostgreSQL schema
│   └── scripts/seed_admins.py One-time admin account seeding
├── nginx/nginx.conf
├── .env.template
└── README.md
```

## Local Setup

### 1. Environment

```bash
cp .env.template .env
```

Fill in `DATABASE_URL`, MinIO, Razorpay, SMTP, and reCAPTCHA values.

### 2. Database

```bash
createdb admitflow
psql admitflow -f backend/migrations/schema.sql
psql admitflow -f backend/migrations/002_admin_portal.sql   # admin sessions + append-only audit log
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m scripts.seed_admins   # reads ADMIN1_*..ADMIN4_* from .env; delete the passwords afterwards
python run.py                # http://localhost:5000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

## Admin portal

Staff sign in at `/admin/auth` (no link from the public site, not indexed). Admin sessions use their own
cookie (`admitflow_admin_session`, HttpOnly, SameSite=Strict) backed by the `admin_sessions` table, so they are
fully separate from student sessions; logout and the idle timeout (`SESSION_TIMEOUT_SECONDS`) are enforced
server-side. Admin accounts are created only by `python -m scripts.seed_admins`.

Endpoints (all need an admin session): `POST /api/admin/login|logout`, `GET /api/admin/me`,
`GET /api/admin/students` (20/page; `sort`, `order`, `q`, `stage`, `payment_status`),
`GET /api/admin/students/:id`, `DELETE /api/admin/students/:id` (body `{"confirmation":"DELETE"}`).

Hard delete order: delete the applicant's MinIO files (abort with nothing deleted if any fail) -> write the audit
entry in its own committed transaction -> one `DELETE FROM students` that cascades. `audit_log` is append-only
(a database trigger rejects UPDATE/DELETE).

### Admin tests

Tests run against real PostgreSQL, rebuilt from `migrations/` each run (never point this at real data):

```bash
createdb admitflow_test
cd backend && pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://user:pw@localhost:5432/admitflow_test pytest
```

## Deployment

Production serves the React build and proxies `/api/*` through Nginx to Gunicorn. No cloud dependency; runs
entirely on a local server. Paths below assume the repo is at `/var/www/admitflow`.

1. **Install** PostgreSQL 16, Nginx, Python 3.12+, Node, and the MinIO binary (`/usr/local/bin/minio`).
2. **Database:** `createdb admitflow`, then run `schema.sql` and `002_admin_portal.sql`.
3. **Backend:** `cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt`.
   Create `/var/www/admitflow/.env` from `.env.template` (`chmod 600`, `FLASK_ENV=production`, a long random
   `FLASK_SECRET_KEY`), then `venv/bin/python -m scripts.seed_admins` and remove the `ADMIN*_PASSWORD` lines.
4. **Frontend:** set `VITE_API_BASE_URL=` (empty = same origin) in `.env`, then `cd frontend && npm ci && npm run build`.
5. **Nginx:** `sudo cp nginx/nginx.conf /etc/nginx/sites-available/admitflow`, symlink into `sites-enabled`,
   `sudo nginx -t && sudo systemctl reload nginx`.
6. **Services:** copy `backend/deploy/admitflow.service` and `minio.service` to `/etc/systemd/system/`, then
   `sudo systemctl daemon-reload && sudo systemctl enable --now minio admitflow`.
7. **HTTPS:** production marks session cookies `Secure`, which browsers will not store over plain HTTP (except on
   localhost). Use HTTPS (a self-signed certificate is fine on a LAN; see the commented 443 block in `nginx.conf`).

Rate limiting is two-layer: Flask-Limiter (per Gunicorn worker) plus an Nginx `limit_req` zone on the login/signup
endpoints, which is the shared cap that actually holds across all 4 workers.
