from datetime import datetime, timedelta

import pytest

from tests.test_auth_otp import EMAIL, outbox, pending  # noqa: F401  (shared fixtures)

GOOD = "sunrise-42!"


def _verified_session(client, pending, outbox):  # noqa: F811
    client.post("/api/auth/send-otp", json={"email": EMAIL})
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": outbox[0][2]})
    assert r.status_code == 200


def _set(client, password=GOOD, confirm=None):
    return client.post(
        "/api/auth/set-password",
        json={"password": password, "confirm_password": password if confirm is None else confirm},
    )


def test_set_password_hashes_with_bcrypt(client, pending, outbox):  # noqa: F811
    from app.extensions import bcrypt
    from app.models import Student

    _verified_session(client, pending, outbox)
    r = _set(client)
    assert r.status_code == 200
    student = Student.query.one()
    assert student.password_hash != GOOD and student.password_hash.startswith("$2")
    assert bcrypt.check_password_hash(student.password_hash, GOOD)


def test_requires_otp_verification_first(client, pending):  # noqa: F811
    r = _set(client)
    assert r.status_code == 403


def test_proof_is_single_use(client, pending, outbox):  # noqa: F811
    _verified_session(client, pending, outbox)
    assert _set(client).status_code == 200
    assert _set(client, "another-pw-9!").status_code == 403


def test_expired_proof_is_rejected(client, pending, outbox):  # noqa: F811
    _verified_session(client, pending, outbox)
    with client.session_transaction() as sess:
        sess["otp_verified"]["expires"] = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
        sess.modified = True
    assert _set(client).status_code == 403


@pytest.mark.parametrize(
    "password",
    ["short1!", "nodigits!!", "nospecial123", "a1!" + "x" * 80, "", None],
)
def test_weak_passwords_are_rejected_and_keep_proof(client, pending, outbox, password):  # noqa: F811
    from app.models import Student

    _verified_session(client, pending, outbox)
    r = _set(client, password, confirm=password)
    assert r.status_code == 400 and r.json["field"] == "password"
    assert Student.query.one().password_hash is None
    assert _set(client).status_code == 200  # user can retry without re-verifying


def test_mismatched_confirmation_is_400(client, pending, outbox):  # noqa: F811
    _verified_session(client, pending, outbox)
    r = _set(client, GOOD, confirm="different-1!")
    assert r.status_code == 400 and r.json["field"] == "confirm_password"
