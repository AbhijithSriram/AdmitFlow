# AdmitFlow — Implementation & Learning Plan

This document turns the [SRD](AdmitFlow_SRD.docx) into concrete, independent workstreams for a 4-person team. The scaffold (`backend/`, `frontend/`) is already committed — every person is filling in stub functions (currently returning `501 Not implemented` on the backend, or `{/* TODO */}` on the frontend) inside files that **no one else touches**. That's what makes this safe to parallelize: as long as everyone stays inside their own file list, nobody will hit a merge conflict.

This is an academic project, so each section below is written as **learn → build small → build real**, not "go implement FR-6.4". Don't skip the learning links just to get code working — the point of the project is to understand the stack, not just produce a repo that runs.

---

## 0. How to work in parallel without conflicts

1. **One branch per person**, created off `main`:
   ```bash
   git checkout -b person1-auth
   git checkout -b person2-application-form
   git checkout -b person3-payment-dashboard
   git checkout -b person4-admin-deployment
   ```
2. **Stay inside your file list** (given in each section below). If you think you need to touch a file outside your list, post in the group chat first — it's almost always a sign the task split needs a small adjustment, not that you should just edit it.
3. Commit small, working increments — don't sit on one giant commit for two weeks.
4. Open a PR into `main` when a feature is working end-to-end (backend route + frontend page actually talking to each other). Someone else on the team reviews it before merge.
5. **Merge order matters less than usual** here because the file lists don't overlap — but pull `main` before you start a new session so you have everyone else's model/schema changes if any got made.
6. Nobody touches `backend/migrations/schema.sql`, `backend/app/__init__.py`, `backend/app/extensions.py`, `backend/app/config.py`, `frontend/src/App.jsx`, or `frontend/src/api/client.js` unless the team agrees together — these are the shared backbone files everyone's code plugs into, and they're already scaffolded with everything each person needs.

---

## 1. Tech stack — what you actually need to learn

Don't try to learn "React" or "Flask" cover to cover. Read the specific pages below, then start writing code and come back to the docs when you get stuck — that's a much faster loop than reading everything up front.

### JavaScript (needed by everyone touching `frontend/`)
- [MDN: JavaScript basics](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting) — variables, functions, arrays/objects
- [MDN: Arrow functions](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/Arrow_functions)
- [MDN: Destructuring assignment](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Destructuring_assignment) — you'll see `const { data } = response` constantly
- [MDN: Promises](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises) and [async/await](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function) — every API call uses this
- [MDN: import/export modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)

### React (needed by everyone touching `frontend/`)
- [React: Describing the UI](https://react.dev/learn/describing-the-ui) — JSX, components, props
- [React: Adding Interactivity](https://react.dev/learn/adding-interactivity) — `useState`, event handlers
- [React: Managing State](https://react.dev/learn/managing-state)
- [React: `useEffect`](https://react.dev/reference/react/useEffect) — used in `useFormRehydrate.js` and dashboard data loading
- [React Router: Tutorial](https://reactrouter.com/en/main/start/tutorial) — how `App.jsx`'s routes work
- [Axios docs](https://axios-http.com/docs/intro) — how `src/api/client.js` makes HTTP calls

### Python / Flask (needed by everyone touching `backend/`)
- [Flask Quickstart](https://flask.palletsprojects.com/en/latest/quickstart/) — routes, request/response
- [Flask: Blueprints](https://flask.palletsprojects.com/en/latest/blueprints/) — how `auth.py`, `application.py` etc. plug into the app
- [Flask-SQLAlchemy Quickstart](https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/) — how the `models/` files map to DB tables
- [Real Python: Flask by Example](https://realpython.com/flask-by-example-part-1-project-setup/) — good if you've never built an API before

### Tool-specific (read the relevant one when you reach that task)
- [Razorpay: Standard Checkout integration](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/) — Person 3
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html) — Person 2
- [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/) — Person 3 (PDF generation)
- [Flask-Limiter docs](https://flask-limiter.readthedocs.io/) — Person 1 (rate limiting) and Person 4 (admin routes)
- [bcrypt / Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/) — Person 1

---

## 2. Task split

Each person owns a full vertical slice — backend route + service + model + frontend page — so you can build and test your own feature end-to-end without waiting on anyone else. Where you need something from another slice (e.g. Person 3's payment step needs a completed application from Person 2), **stub it locally** first (hardcode a fake application object) and swap in the real integration once both sides are ready — don't block on it.

---

### Person 1 — Authentication & Student Onboarding

**Covers:** SRD §3 FR-1, FR-2, FR-3, FR-4 · §4 NFR-1 (auth-related items) · §7.3 auth endpoints

**Your files (only these):**
```
backend/app/blueprints/auth.py
backend/app/services/otp_service.py
backend/app/services/email_service.py        (OTP + password-reset functions only)
backend/app/models/student.py
backend/app/models/otp_token.py
backend/app/middleware/auth_guard.py
frontend/src/pages/Landing.jsx
frontend/src/pages/Signup.jsx
frontend/src/pages/OtpVerification.jsx
frontend/src/pages/SetPassword.jsx
frontend/src/pages/Login.jsx
frontend/src/context/AuthContext.jsx
```

**Build order (small steps, in this order):**
1. **Landing page UI** — static, no backend needed. Good first task to get comfortable with JSX + Tailwind classes.
2. **Signup form UI** — controlled inputs (`useState` per field), client-side validation (email format, 10-digit phone). No API call yet — just `console.log` the form data on submit.
3. **`POST /api/auth/signup` backend** — validate input server-side, check email/phone uniqueness against `Student`, hash nothing yet (no password at signup), create the `Student` row, return the new student id.
4. **Wire Signup form → `authApi.signup()`** (already stubbed in `api/client.js`) — handle the real request, show validation errors returned by the server.
5. **Google reCAPTCHA v2** — add the widget to the signup form, send the token to the backend, verify server-side via Google's verify endpoint before creating the student.
6. **OTP generation + email** — implement `otp_service.create_otp_token` (already has a working reference implementation — read it, understand the bcrypt-hash-not-raw-OTP pattern) and `email_service.send_otp_email` using `smtplib`.
7. **`POST /api/auth/send-otp` and `/verify-otp`** backend routes, then the OtpVerification page frontend.
8. **`POST /api/auth/set-password`** — bcrypt hash, min-8-chars + 1 number + 1 special-char validation (do this validation in **both** JS and Python — client-side for UX, server-side because client-side is never trusted).
9. **`POST /api/auth/login`** — email+password check, 5-failed-attempts → 15-minute lockout (`Student.failed_login_attempts` / `locked_until` columns already exist in the model), create a Flask session.
10. **`AuthContext.jsx`** — after login succeeds, store the student in context so other pages know the user is authenticated.
11. **Forgot password flow** — reuses your OTP machinery with `purpose="password_reset"`.
12. **Logout** — invalidate the session server-side, clear `AuthContext` client-side.

**Definition of done:** a brand-new user can sign up, get a real OTP email, verify it, set a password, and log in — and a wrong password 5 times locks the account for 15 minutes.

---

### Person 2 — Application Form Engine (Steps 1–6)

**Covers:** SRD §3 FR-6.1 through FR-6.8 · §7.3 draft/upload endpoints

**Your files (only these):**
```
backend/app/blueprints/application.py
backend/app/services/minio_service.py
backend/app/models/application.py
backend/app/models/form_draft.py
frontend/src/pages/ApplicationForm.jsx
frontend/src/components/FormStep1.jsx  ... FormStep6.jsx
frontend/src/components/FormStepNav.jsx
frontend/src/components/UploadBox.jsx
frontend/src/hooks/useAutoSave.js
frontend/src/hooks/useFormRehydrate.js
```

**Build order:**
1. **Guidelines step (FR-6.1)** — a scrollable instructions page as `FormStep1`'s "step 0" (or a separate component you add to `ApplicationForm.jsx`'s step list — that file is yours). Detect scroll-to-bottom in JS (`element.scrollHeight - element.scrollTop === element.clientHeight`) before enabling "I Agree & Proceed".
2. **`POST /api/app/start`** — creates the `Application` row for the logged-in student, records the guidelines-acceptance timestamp.
3. **Build Step 1 (Personal Details) form fields as plain React state first** — no auto-save yet, just get the fields rendering and validating.
4. **`PATCH /api/app/draft/:id/step/:n`** backend — this is the most important endpoint in the whole app. Read SRD §NFR-2 on the **upsert pattern** (`INSERT ... ON CONFLICT DO UPDATE`) before writing it — SQLAlchemy's `db.session.merge()` or an explicit `ON CONFLICT` via `sqlalchemy.dialects.postgresql.insert` both work; pick one and understand *why* naive insert would break on a second save.
5. **`useAutoSave` hook** (already scaffolded — read it) — wire it into Step 1's fields via `onBlur`. Watch the debounce work in the Network tab.
6. **`GET /api/app/draft/:id`** + **`useFormRehydrate`** — reload the page and confirm your Step 1 data comes back.
7. Repeat steps 3–6 for **Steps 2–5** (address with pincode auto-fill via the free [Indian Post Office API](https://api.postalpincode.in/pincode/<pincode>), academic details, programme preference, conditional entrance-test fields).
8. **Step 6 — document upload.** Implement `minio_service.py` (a working reference pattern is already in the file — read it), then `POST /api/app/upload/:id/:doc_type` doing **server-side** MIME/size/dimension validation with Pillow (never trust the client's `accept` attribute alone).
9. **Synchronous step-save on Next/Back** — per FR-6.2, the UI must not advance until the save confirms; use `useAutoSave`'s `saveNow` (already exported) and `await` it before calling `onNext`.

**Definition of done:** starting from Guidelines, a student can fill Steps 1–6, refresh the browser mid-form and see their data still there, and end up with three uploaded documents referenced in `applications.photo_url` / `signature_url` / `id_proof_url`.

---

### Person 3 — Payment, PDF, Email Confirmation & Dashboard

**Covers:** SRD §3 FR-5, FR-6.9, FR-8, FR-9 (payment-triggered emails) · §7.3 payment/dashboard/receipt endpoints

**Your files (only these):**
```
backend/app/blueprints/payment.py
backend/app/services/payment_service.py
backend/app/services/pdf_service.py
backend/app/services/email_service.py         (payment-confirmation function only)
backend/app/models/payment.py
frontend/src/pages/Dashboard.jsx
frontend/src/components/StatusBadge.jsx
frontend/src/components/FormStep7.jsx
frontend/src/hooks/usePayment.js
```

> Note: `email_service.py` is shared with Person 1 — you're each adding a different function to the same file (`send_otp_email`/`send_password_reset_email` are theirs, `send_payment_confirmation_email` is yours, already stubbed). Add your function, don't touch theirs. If you both need to edit the same lines at the same time, coordinate — this is the one intentional exception to "no shared files."

**Build order:**
1. **Stub the summary data** — since Step 7 needs the previous 6 steps' data and you don't want to block on Person 2, hardcode a fake application object first and build the read-only summary UI against that.
2. **`POST /api/app/payment/create-order`** — implement `payment_service.create_order` (already has a working reference — read it) and call it from the route, persisting a `Payment` row with `status="CREATED"`.
3. **Razorpay Checkout on the frontend** — add the Razorpay checkout script (`https://checkout.razorpay.com/v1/checkout.js`) to `index.html`, then wire `usePayment.js` (already scaffolded) to your create-order endpoint.
4. **`POST /api/app/payment/confirm`** — this is the most security-sensitive endpoint in the app. Read SRD §NFR-1: verify the HMAC-SHA256 signature server-side using `payment_service.verify_signature` (already implemented — read it and understand *why* trusting the frontend callback alone would let someone fake a payment). On success, update `Payment.status`, `Application.status = "PAID"`, **in a single DB transaction** (SRD §NFR-2) — look up SQLAlchemy's session/transaction docs for this.
5. **`POST /api/app/payment/failed`** — mark `status="PAYMENT_PENDING"`, add a "Retry Payment" path.
6. **PDF generation** — build out `pdf_service._application_template` (currently a minimal placeholder) into the real layout from FR-8 (institution header, photo, all form data, payment ref, declaration, signature), triggered right after payment confirms.
7. **Email confirmation** — `send_payment_confirmation_email`, attaching the generated PDF + a separate receipt.
8. **`GET /api/app/receipt/:id`** — return a MinIO presigned URL (reuse Person 2's `minio_service.get_presigned_url` — you can *call* their finished service function, you just don't edit their file).
9. **`GET /api/student/dashboard`** + `Dashboard.jsx` — status badge (`StatusBadge` is already built), quick-action buttons, receipt download link.

**Definition of done:** a paid-up application produces a real PDF stored in MinIO, an email with that PDF lands in the applicant's inbox, and the dashboard shows "Submitted & Paid" with a working receipt download.

---

### Person 4 — Admin Portal, Security Hardening & Deployment

**Covers:** SRD §3 FR-7 · §4 NFR-1 (app-wide: headers, rate limiting, CORS) · §4 NFR-6 (audit log) · §5 architecture · §10/§11 deployment & security checklist

**Your files (only these):**
```
backend/app/blueprints/admin.py
backend/app/models/admin.py
backend/app/models/audit_log.py
backend/app/middleware/admin_guard.py
backend/scripts/seed_admins.py
nginx/nginx.conf
frontend/src/pages/Admin/AdminLogin.jsx
frontend/src/pages/Admin/AdminDashboard.jsx
```
Plus, once the other three tracks have working routes, you're the one who adds the **security headers / rate limiting to their endpoints** — but that's applied via the shared `app/__init__.py`'s `register_security_headers` (already done) and `@limiter.limit(...)` decorators added to *your own* `admin.py` routes; for other blueprints, open a PR suggestion rather than editing their files directly.

**Build order:**
1. **`scripts/seed_admins.py`** — already has a working reference implementation; run it against your local DB and confirm 4 admin rows exist with bcrypt-hashed passwords.
2. **`POST /api/admin/login`** — separate from student login: different cookie name (`ADMIN_SESSION_COOKIE_NAME`, already in `config.py`), no registration flow, no lockout logic needed (small, trusted user set).
3. **`admin_guard.py`** (already scaffolded — read it) — apply `@admin_required` to the rest of your routes.
4. **`AdminLogin.jsx`** at route `/admin/auth` (already wired in `App.jsx`).
5. **`GET /api/admin/students`** — paginated (20/page per NFR-3), sortable, searchable, filterable by stage/payment status. Read up on SQLAlchemy's `.paginate()` and `.filter()`.
6. **`AdminDashboard.jsx`** — the table UI consuming that endpoint.
7. **`GET /api/admin/students/:id`** — full detail view (click a row).
8. **`DELETE /api/admin/students/:id`** — the hard-delete flow from FR-7.3: frontend confirmation modal requiring the literal text "DELETE" to be typed, backend does MinIO cleanup → **audit log write** → cascading DB delete, in that order (SRD §6.2 explains why the audit log write happens *before* the delete — so it survives even if the delete fails). `AuditLog` model already exists; this is where you use it.
9. **Security headers + rate limiting audit** — `register_security_headers` in `app/__init__.py` is already applied globally; verify it with browser devtools (Network tab → Response Headers) rather than re-adding it. Add `@limiter.limit(...)` to your own admin routes as appropriate.
10. **Deployment** — flesh out `nginx/nginx.conf` (already has a working starting point) for the real project paths, write `systemd` unit files for Gunicorn (`backend/deploy/admitflow.service` — new file, this is fine since nothing else lives there), and document the deployment steps in the README's Deployment section.

**Definition of done:** an admin can log in at `/admin/auth` (isolated from student sessions), see a paginated/filterable applicant table, view one applicant's full detail, and hard-delete a test record with the confirmation modal — with an audit log entry that survives even if you kill the DB connection mid-delete.

---

## 3. Extension modules (bonus, after core is done)

These are explicitly out of the MVP critical path (SRD §2, Modules 2 & 3) — only start these once all four core tracks above are merged and demoed working end-to-end.

- **Module 2 (Online Aptitude Test, FR-10)** — natural extension of Person 2's form-building skills (admin creates MCQs, timed UI) + Person 4's admin patterns (assigning tests to filtered applicants). Suggest Person 2 + Person 4 pair on this.
- **Module 3 (Admin ERP View, FR-11)** — natural extension of Person 3's dashboard/stats work + Person 4's admin table patterns. Suggest Person 3 + Person 4 pair on this.

Models for both (`test_papers`, `test_questions`, `test_submissions`) already exist in `backend/app/models/` and `schema.sql` — no schema work needed to start.

---

## 4. Suggested timeline (loosely following SRD §9)

| Weeks | Everyone |
|---|---|
| 1 | Work through the learning links for your track. Build your first 1-2 UI-only / stub-only steps (no real backend wiring yet) so you're comfortable with the syntax before it matters. |
| 2–3 | Real backend routes + real frontend wiring, in the build-order lists above. Test your own slice in isolation (Postman/curl for backend, hardcoded stub data for frontend). |
| 4 | Integration: swap stubbed data for real cross-slice calls (e.g. Person 3's payment step now reads Person 2's real application draft). Fix the seams. |
| 5 | Person 4 leads a full run-through on a real local deployment (Nginx + Gunicorn). Everyone fixes bugs found in that environment. |

---

## 5. When you're stuck

- Read the error message fully before searching — Flask and React error messages are usually specific about the file/line.
- Check the `Not implemented` stub you're replacing — it already shows the correct route signature, decorators, and imports; you're filling in the body, not designing the endpoint from scratch.
- Several service files (`otp_service.py`, `minio_service.py`, `payment_service.py`) already contain **working reference implementations**, not just stubs — read those before writing similar code elsewhere, they show the pattern the rest of the app expects (e.g. always reading secrets from `current_app.config`, never hardcoding).
