from sqlalchemy import text

from app.extensions import db
from app.models import Application, AuditLog, FormDraft, OtpToken, Payment, Student


def _delete(c, sid, confirmation="DELETE"):
    return c.delete(f"/api/admin/students/{sid}", json={"confirmation": confirmation})


def _counts():
    return {m.__name__: m.query.count() for m in (Student, OtpToken, Application, FormDraft, Payment)}


def test_requires_literal_DELETE(logged_in, make_student, fake_minio):
    s = make_student(status="PAID", payment="SUCCESS")
    for bad in ("delete", "DELETE ", "", None):
        assert _delete(logged_in, s.id, bad).status_code == 400
    assert logged_in.delete(f"/api/admin/students/{s.id}").status_code == 400  # no body at all
    assert Student.query.count() == 1 and fake_minio.deleted == [] and AuditLog.query.count() == 0


def test_full_delete_cascades_cleans_files_and_audits(logged_in, make_student, fake_minio, admin):
    s = make_student("Gone Soon", status="PAID", payment="SUCCESS")
    other = make_student("Bystander", status="PAID", payment="SUCCESS")
    sid, email = s.id, s.email

    r = _delete(logged_in, sid)
    assert r.status_code == 200
    data = r.json["data"]
    assert sorted(data["files_removed"]) == sorted(fake_minio.deleted) and len(data["files_removed"]) == 4
    assert data["cascaded"] == {"otp_tokens": 1, "applications": 1, "form_drafts": 2, "payments": 2, "test_submissions": 0}

    # one DELETE cascaded: no orphans for this student, and the other student is untouched
    assert db.session.get(Student, sid) is None
    assert Application.query.filter_by(student_id=sid).count() == 0
    assert _counts() == {"Student": 1, "OtpToken": 1, "Application": 1, "FormDraft": 2, "Payment": 2}
    assert db.session.get(Student, other.id) is not None

    row = AuditLog.query.one()
    assert (row.action_type, row.target_student_id, row.target_email, row.admin_id) == (
        "HARD_DELETE_STUDENT", sid, email, admin.id)  # email survives the student's deletion


def test_delete_student_with_no_application(logged_in, make_student, fake_minio):
    s = make_student(status=None)
    r = _delete(logged_in, s.id)
    assert r.status_code == 200 and r.json["data"]["files_removed"] == []
    assert Student.query.count() == 0


def test_unknown_student_404_and_writes_no_audit(logged_in, fake_minio):
    assert _delete(logged_in, "00000000-0000-4000-8000-000000000000").status_code == 404
    assert _delete(logged_in, "not-a-uuid").status_code == 404
    assert AuditLog.query.count() == 0


def test_minio_failure_aborts_and_deletes_nothing(logged_in, make_student, fake_minio):
    s = make_student(status="PAID", payment="SUCCESS")
    fake_minio.fail_on = {f"applications/1/id.pdf"}
    r = _delete(logged_in, s.id)
    assert r.status_code == 502
    assert Student.query.count() == 1 and Application.query.count() == 1  # DB untouched
    assert [a.action_type for a in AuditLog.query.all()] == ["HARD_DELETE_ABORTED"]
    # retrying after MinIO recovers works
    fake_minio.fail_on = set()
    assert _delete(logged_in, s.id).status_code == 200 and Student.query.count() == 0


def test_audit_entry_survives_when_the_db_delete_fails(logged_in, make_student, fake_minio, monkeypatch):
    """The point of 'audit before delete': kill the delete and the record must still exist."""
    from app.services import admin_service
    s = make_student(status="PAID", payment="SUCCESS")

    def boom(_sid):
        raise RuntimeError("connection lost")
    monkeypatch.setattr(admin_service, "_delete_student_row", boom)

    r = _delete(logged_in, s.id)
    assert r.status_code == 500 and "audit log" in r.json["error"]
    assert Student.query.count() == 1
    kinds = [a.action_type for a in AuditLog.query.order_by(AuditLog.created_at)]
    assert kinds == ["HARD_DELETE_STUDENT", "HARD_DELETE_STUDENT_FAILED"]


def test_audit_log_is_append_only_in_the_database(logged_in, make_student, fake_minio):
    _delete(logged_in, make_student(status=None).id)
    for stmt in ("UPDATE audit_log SET action_type='X'", "DELETE FROM audit_log"):
        try:
            db.session.execute(text(stmt))
            raise AssertionError("trigger did not block: " + stmt)
        except Exception as e:  # noqa: BLE001
            assert "append-only" in str(e)
            db.session.rollback()
    assert AuditLog.query.count() == 1


def test_other_admins_actions_are_attributed_correctly(app, client, make_admin, make_student, fake_minio):
    second = make_admin(email="ravi@college.edu", name="Ravi")
    client.post("/api/admin/login", json={"email": "ravi@college.edu", "password": "correct-horse-9"})
    _delete(client, make_student(status=None).id)
    assert AuditLog.query.one().admin_id == second.id
