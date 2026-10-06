"""One-time script to seed the four admin accounts (SRD FR-7.1).

Run from backend/:   python -m scripts.seed_admins

Credentials come from .env (ADMIN1_NAME / ADMIN1_EMAIL / ADMIN1_PASSWORD ... ADMIN4_*),
never from source code. Re-running is safe: existing emails are skipped. Passwords are
bcrypt-hashed and never printed. Remove the ADMIN*_PASSWORD lines from .env afterwards.
"""

import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import bcrypt, db  # noqa: E402
from app.models import Admin  # noqa: E402

MIN_PASSWORD_LENGTH = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def seed_admins() -> None:
    app = create_app()
    with app.app_context():
        created = skipped = 0
        for i in range(1, 5):
            name = os.environ.get(f"ADMIN{i}_NAME", "").strip()
            email = os.environ.get(f"ADMIN{i}_EMAIL", "").strip().lower()
            password = os.environ.get(f"ADMIN{i}_PASSWORD", "")
            if not (name and email and password):
                sys.exit(f"ADMIN{i}_NAME, ADMIN{i}_EMAIL and ADMIN{i}_PASSWORD must all be set in .env")
            if not EMAIL_RE.match(email):
                sys.exit(f"ADMIN{i}_EMAIL is not a valid email address")
            if len(password) < MIN_PASSWORD_LENGTH:
                sys.exit(f"ADMIN{i}_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters")

            if Admin.query.filter_by(email=email).first():
                print(f"skip    {email} (already exists)")
                skipped += 1
                continue
            db.session.add(Admin(name=name, email=email,
                                 password_hash=bcrypt.generate_password_hash(password).decode("utf-8")))
            print(f"created {email}")
            created += 1
        db.session.commit()
        print(f"Done: {created} created, {skipped} skipped.")
        if created:
            print("Now delete the ADMIN*_PASSWORD lines from .env.")


if __name__ == "__main__":
    seed_admins()
