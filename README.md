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

### 2. Database and file storage

The quickest way is Docker, which starts PostgreSQL (port 5435) and MinIO (ports 9000 and 9001). The
development credentials are in `docker-compose.yml`; copy them into your `.env`:

```bash
docker compose up -d
```

MinIO no longer publishes prebuilt images, so the first `docker compose up` **builds it from source**
(`docker/minio/Dockerfile`). That takes a couple of minutes once, then it is cached.

Then create the tables:

```bash
createdb admitflow
psql admitflow -f backend/migrations/schema.sql
psql admitflow -f backend/migrations/002_admin_portal.sql   # admin sessions + append-only audit log
```

`schema.sql` already includes everything. **If your database was created before these changes**, run the
migrations you have not applied yet (each is safe to re-run):
`002_admin_portal.sql` (admin sessions and audit log), `003_otp_attempts.sql` (counts wrong one-time-code guesses) and `004_swap_programme_and_academic_steps.sql` (moves drafts saved before the programme became Step 3 and the academic details Step 4).

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

### On the homeserver (behind the Cloudflare tunnel)

`deploy/homeserver/` deploys AdmitFlow the same way as the voice lab: a systemd service on localhost, secrets in
`/etc/admitflow.env` generated on the box, files under `/srv/nas/admitflow`, and one hostname added to the existing
tunnel (`https://admitflow.abhijith-sriram.in`). It also installs nginx and PostgreSQL if they are missing, and runs
MinIO from a binary built from source (`docker/minio/Dockerfile`), because MinIO no longer publishes packages.

```bash
cd /home/abhijith/admitflow && git pull && sudo bash deploy/homeserver/install.sh
```

The script is idempotent, so re-running it is also the update path. Before the first run:

1. Put the third-party keys in `/home/abhijith/.admitflow-secrets.env` (template: `deploy/homeserver/secrets.env.example`).
2. Stage the MinIO binary at `/home/abhijith/.admitflow-stage/minio`.
3. If it says the hostname does not resolve, add the one DNS record it prints (the tunnel has no wildcard record).

It uses ports 5001 (API), 8088 (nginx), 9000 and 9001 (file storage) and 5432 (database), all loopback-only, and
refuses to start if a neighbour already holds one. Logs: `journalctl -u admitflow -f` and `journalctl -u admitflow-minio -f`.

Two server-specific settings worth knowing about: `MINIO_PUBLIC_ENDPOINT` makes signed file links name the public
host (a browser cannot open `127.0.0.1:9000`), and nginx reads the visitor's real address from Cloudflare's
`CF-Connecting-IP` header, without which every visitor would share one login rate-limit bucket.

#### Backups and restore

`install.sh` sets up a nightly backup (02:30 India time, `admitflow-backup.timer`) into `/srv/nas/admitflow-backups`,
which only root can read because the dumps contain applicants' personal data:

- `db/admitflow-<date>.dump`: the whole database (`pg_dump` custom format), kept for 14 days.
- `files/<date>/`: the uploaded documents (the MinIO data directory). Unchanged files are hard links to the previous
  night, so each night only costs what changed.
- `db/pre-install-<date>.dump`: taken by every `install.sh` run on an existing database, before any migration.

Run one now with `sudo admitflow-backup`; see the schedule with `systemctl list-timers admitflow-backup.timer`.
The backups are on `/srv`, a different partition from the database but the same disk: copy the newest dump off the
machine now and then.

To restore the database from a dump (this replaces the current data):

```bash
sudo systemctl stop admitflow
sudo -u postgres dropdb admitflow && sudo -u postgres createdb -O admitflow admitflow
sudo -u postgres pg_restore --exit-on-error -d admitflow < /srv/nas/admitflow-backups/db/admitflow-<date>.dump
sudo systemctl start admitflow
```

To restore the uploaded files: `sudo systemctl stop admitflow-minio`, then
`sudo rsync -a --delete /srv/nas/admitflow-backups/files/<date>/ /srv/nas/admitflow/minio/`, then start it again.
Restore the files from the same night as the database dump, so the documents match the records.
