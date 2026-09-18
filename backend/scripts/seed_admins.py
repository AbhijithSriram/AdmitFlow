"""One-time script to seed the four admin accounts. Run manually: python -m scripts.seed_admins"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.extensions import bcrypt, db  # noqa: E402
from app.models import Admin  # noqa: E402

ADMIN_SEED_DATA = [
    {"name": "Admin One", "email": "admin1@admitflow.local", "password": "ChangeMe1!"},
    {"name": "Admin Two", "email": "admin2@admitflow.local", "password": "ChangeMe2!"},
    {"name": "Admin Three", "email": "admin3@admitflow.local", "password": "ChangeMe3!"},
    {"name": "Admin Four", "email": "admin4@admitflow.local", "password": "ChangeMe4!"},
]


def seed_admins() -> None:
    app = create_app()
    with app.app_context():
        for entry in ADMIN_SEED_DATA:
            if Admin.query.filter_by(email=entry["email"]).first():
                continue
            admin = Admin(
                name=entry["name"],
                email=entry["email"],
                password_hash=bcrypt.generate_password_hash(entry["password"]).decode("utf-8"),
            )
            db.session.add(admin)
        db.session.commit()
        print(f"Seeded {len(ADMIN_SEED_DATA)} admin accounts (skipping existing).")


if __name__ == "__main__":
    seed_admins()
