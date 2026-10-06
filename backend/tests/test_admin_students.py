from datetime import datetime, timedelta


def _list(c, **params):
    return c.get("/api/admin/students", query_string=params).json["data"]


def test_pagination_is_20_per_page(logged_in, make_student):
    for i in range(45):
        make_student(name=f"Student {i:02d}", created=datetime(2026, 8, 1) + timedelta(minutes=i))
    p1, p3 = _list(logged_in), _list(logged_in, page=3)
    assert (p1["total"], p1["total_pages"], len(p1["students"])) == (45, 3, 20)
    assert len(p3["students"]) == 5
    assert p1["students"][0]["name"] == "Student 44"  # newest first by default
    assert _list(logged_in, page=99)["page"] == 3      # out-of-range page is clamped


def test_stage_defaults_to_not_started_without_application(logged_in, make_student):
    make_student(status=None)
    assert _list(logged_in)["students"][0]["stage"] == "NOT_STARTED"


def test_filters_stage_and_payment(logged_in, make_student):
    make_student("A", status="IN_PROGRESS")
    make_student("B", status="PAYMENT_PENDING", payment="FAILED")
    make_student("C", status="PAID", payment="SUCCESS")
    assert [s["name"] for s in _list(logged_in, stage="PAID")["students"]] == ["C"]
    assert [s["name"] for s in _list(logged_in, payment_status="PENDING")["students"]] == ["B"]
    assert [s["name"] for s in _list(logged_in, payment_status="PAID")["students"]] == ["C"]
    assert [s["name"] for s in _list(logged_in, payment_status="NONE")["students"]] == ["A"]


def test_search_name_email_phone_and_escapes_wildcards(logged_in, make_student):
    s = make_student("Karthik Subramanian")
    make_student("Someone Else")
    assert [x["name"] for x in _list(logged_in, q="karth")["students"]] == ["Karthik Subramanian"]
    assert len(_list(logged_in, q=s.email)["students"]) == 1
    assert len(_list(logged_in, q=s.phone)["students"]) == 1
    assert _list(logged_in, q="%")["total"] == 0  # a literal %, not "match everything"


def test_sorting(logged_in, make_student):
    for n in ("Charlie", "Alice", "Bob"):
        make_student(n)
    names = lambda **kw: [s["name"] for s in _list(logged_in, **kw)["students"]]
    assert names(sort="name", order="asc") == ["Alice", "Bob", "Charlie"]
    assert names(sort="name", order="desc") == ["Charlie", "Bob", "Alice"]


def _bad(logged_in, **p):
    return logged_in.get("/api/admin/students", query_string=p).status_code


def test_invalid_params_are_400(logged_in):
    assert _bad(logged_in, sort="password_hash") == 400   # sort is a whitelist, not a column name
    assert _bad(logged_in, order="sideways") == 400
    assert _bad(logged_in, stage="HACKED") == 400
    assert _bad(logged_in, payment_status="X") == 400
    assert _bad(logged_in, page="abc") == 400


def test_list_never_exposes_password_hash(logged_in, make_student):
    make_student()
    assert "password" not in logged_in.get("/api/admin/students").get_data(as_text=True).lower()


def test_detail_has_steps_payments_and_presigned_urls(logged_in, make_student, fake_minio):
    s = make_student("Detail Person", status="PAID", payment="SUCCESS")
    d = logged_in.get(f"/api/admin/students/{s.id}").json["data"]
    assert d["student"]["email"] == s.email and "password_hash" not in d["student"]
    assert d["steps"] == {"1": {"father_name": "R"}, "2": {"city": "Chennai"}}
    assert [p["status"] for p in d["payments"]] == ["FAILED", "SUCCESS"]
    assert "razorpay_signature" not in d["payments"][0]
    photo = d["application"]["documents"]["photo"]
    assert photo["present"] and photo["url"].startswith("http://minio.test/") and "sig=" in photo["url"]


def test_detail_survives_minio_outage(logged_in, make_student, monkeypatch):
    from app.services import minio_service
    monkeypatch.setattr(minio_service, "get_presigned_url", lambda n: (_ for _ in ()).throw(RuntimeError("down")))
    s = make_student(status="IN_PROGRESS")
    r = logged_in.get(f"/api/admin/students/{s.id}")
    assert r.status_code == 200 and r.json["data"]["application"]["documents"]["photo"]["url"] is None


def test_detail_without_application(logged_in, make_student):
    s = make_student(status=None)
    d = logged_in.get(f"/api/admin/students/{s.id}").json["data"]
    assert d["application"] is None and d["steps"] == {} and d["payments"] == []


def test_detail_404_for_unknown_and_malformed_ids(logged_in):
    assert logged_in.get("/api/admin/students/00000000-0000-4000-8000-000000000000").status_code == 404
    assert logged_in.get("/api/admin/students/not-a-uuid").status_code == 404  # not a 500
