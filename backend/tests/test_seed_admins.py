import pytest


def _set_env(monkeypatch, **over):
    for i in range(1, 5):
        monkeypatch.setenv(f"ADMIN{i}_NAME", f"Admin {i}")
        monkeypatch.setenv(f"ADMIN{i}_EMAIL", f"a{i}@college.edu")
        monkeypatch.setenv(f"ADMIN{i}_PASSWORD", f"long-enough-pw{i}")
    for k, v in over.items():
        monkeypatch.setenv(k, v)


def _use_test_app(monkeypatch, app):
    # the script normally builds its own dev-config app; reuse the test app instead
    import scripts.seed_admins as mod
    monkeypatch.setattr(mod, "create_app", lambda: app)


def test_seeds_four_hashed_admins_and_is_idempotent(app, monkeypatch, capsys):
    from app.models import Admin
    from scripts.seed_admins import seed_admins
    _use_test_app(monkeypatch, app)
    _set_env(monkeypatch)
    seed_admins(); seed_admins()
    admins = Admin.query.all()
    assert len(admins) == 4
    assert all(a.password_hash.startswith("$2b$12$") for a in admins)  # bcrypt, cost 12
    assert "long-enough-pw" not in capsys.readouterr().out             # passwords never printed


def test_rejects_short_password_and_missing_values(app, monkeypatch):
    from scripts.seed_admins import seed_admins
    _use_test_app(monkeypatch, app)
    _set_env(monkeypatch, ADMIN2_PASSWORD="short")
    with pytest.raises(SystemExit):
        seed_admins()
    _set_env(monkeypatch, ADMIN3_EMAIL="")
    with pytest.raises(SystemExit):
        seed_admins()
