#!/usr/bin/env bash
# Sets a new random password on each of the admin accounts and prints them once.
#
# install.sh creates the four admins on first install and prints their passwords exactly once;
# they are stored nowhere else (only as bcrypt hashes in the database). If that output was missed,
# run this:   sudo bash /home/abhijith/admitflow/deploy/homeserver/reset-admins.sh
#
# Every existing admin session is signed out. Student accounts are not touched.
set -euo pipefail

APP_USER=abhijith
APP_DIR=/home/abhijith/admitflow
ENV_FILE=/etc/admitflow.env

[ "$(id -u)" -eq 0 ] || { echo "run this with sudo" >&2; exit 1; }
[ -r "$ENV_FILE" ] || { echo "$ENV_FILE not found: has install.sh been run?" >&2; exit 1; }

PYCODE=$(cat <<'PY'
import secrets

from app import create_app
from app.extensions import bcrypt, db
from app.models import Admin

app = create_app()
with app.app_context():
    admins = Admin.query.order_by(Admin.email).all()
    if not admins:
        raise SystemExit("There are no admin accounts to reset.")
    print()
    print("New admin passwords (shown once, copy them now):")
    for admin in admins:
        password = secrets.token_urlsafe(12)
        admin.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        print(f"      {admin.email}   {password}")
    db.session.execute(db.text("DELETE FROM admin_sessions"))
    db.session.commit()
    print()
PY
)

# The app's own environment (database URL, Flask secret), read as root and handed to the app user
# as KEY=VALUE arguments, so values containing spaces or symbols are passed through untouched.
mapfile -t APP_ENV < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")

runuser -u "$APP_USER" -- env -C "$APP_DIR/backend" "${APP_ENV[@]}" .venv/bin/python -c "$PYCODE"
