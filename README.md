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
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python scripts/seed_admins.py
python run.py                # http://localhost:5000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                  # http://localhost:3000
```

## Deployment

Production serves the React build and proxies `/api/*` through Nginx to Gunicorn — see [nginx/nginx.conf](nginx/nginx.conf). No cloud dependency; runs entirely on a local server.
