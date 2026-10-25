"""The extension-module routes (aptitude test, statistics, export) are scaffolded as 501 stubs.
These tests pin what must stay true while the owners replace the stubs: every route exists, and
none of them is reachable without the right kind of session. Keep them when a route is implemented
(change the "stub" test to the real behaviour, never delete the guard test)."""
import pytest

ADMIN_ROUTES = [
    ("GET", "/api/admin/tests"),
    ("POST", "/api/admin/tests"),
    ("GET", "/api/admin/tests/p1"),
    ("PUT", "/api/admin/tests/p1"),
    ("DELETE", "/api/admin/tests/p1"),
    ("POST", "/api/admin/tests/p1/publish"),
    ("POST", "/api/admin/tests/p1/assign"),
    ("GET", "/api/admin/tests/p1/results"),
    ("POST", "/api/admin/tests/p1/reset/a1"),
    ("GET", "/api/admin/stats/summary"),
    ("GET", "/api/admin/stats/programmes"),
    ("GET", "/api/admin/stats/registrations"),
    ("GET", "/api/admin/seats"),
    ("PUT", "/api/admin/seats"),
    ("GET", "/api/admin/export/applicants.csv"),
    ("GET", "/api/admin/export/applicants.pdf"),
]

STUDENT_ROUTES = [
    ("GET", "/api/student/tests"),
    ("POST", "/api/student/tests/p1/start"),
    ("PUT", "/api/student/tests/p1/answers"),
    ("POST", "/api/student/tests/p1/submit"),
]

# Admin routes whose 501 stub has been replaced by a real implementation. Their real behaviour is
# tested in the owner's own test file (for example test_admin_stats.py); the guard tests above still
# cover them. Add a route here in the same commit that implements it.
IMPLEMENTED_ADMIN_ROUTES = {
    ("GET", "/api/admin/seats"),
    ("PUT", "/api/admin/seats"),
    ("GET", "/api/admin/stats/summary"),
    ("GET", "/api/admin/stats/programmes"),
    ("GET", "/api/admin/stats/registrations"),
    ("GET", "/api/admin/export/applicants.csv"),
    ("GET", "/api/admin/export/applicants.pdf"),
}


@pytest.mark.parametrize("method, path", ADMIN_ROUTES)
def test_admin_routes_need_an_admin_session(client, method, path):
    resp = client.open(path, method=method)
    assert resp.status_code == 401
    assert resp.json["success"] is False


@pytest.mark.parametrize("method, path", STUDENT_ROUTES)
def test_student_routes_need_a_student_session(client, method, path):
    resp = client.open(path, method=method)
    assert resp.status_code == 401
    assert resp.json["success"] is False


@pytest.mark.parametrize("method, path", ADMIN_ROUTES)
def test_a_student_session_is_not_enough_for_admin_routes(client, make_student, method, path):
    student = make_student()
    with client.session_transaction() as sess:
        sess["student_id"] = student.id
    client.set_cookie("session", "x")  # the student cookie name is what the guard looks for
    assert client.open(path, method=method).status_code in (401, 403)


@pytest.mark.parametrize(
    "method, path", [r for r in ADMIN_ROUTES if r not in IMPLEMENTED_ADMIN_ROUTES]
)
def test_admin_stubs_answer_501_to_an_admin(logged_in, method, path):
    resp = logged_in.open(path, method=method)
    assert resp.status_code == 501
    assert resp.json == {"success": False, "error": "Not implemented"}


@pytest.mark.parametrize("method, path", STUDENT_ROUTES)
def test_student_stubs_answer_501_to_a_student(client, make_student, method, path):
    student = make_student()
    with client.session_transaction() as sess:
        sess["student_id"] = student.id
    resp = client.open(path, method=method)
    assert resp.status_code == 501
    assert resp.json == {"success": False, "error": "Not implemented"}
