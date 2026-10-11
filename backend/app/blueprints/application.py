from datetime import datetime, timezone
from io import BytesIO
from flask import Blueprint, jsonify, request, session
from PIL import Image
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models import Application, FormDraft, Student
from app.services import minio_service
from app.middleware.auth_guard import login_required

application_bp = Blueprint("application", __name__)


def make_envelope(success=True, data=None, error=None, code=200):
    payload = {"success": success}
    if success:
        payload["data"] = data if data is not None else {}
    else:
        payload["error"] = error or "An error occurred"
    return jsonify(payload), code


def _locked_after_payment(app):
    """Once paid, the application is final (see the guidelines) and the PDF/receipt have been
    generated from it, so editing answers or replacing documents would make them disagree."""
    if app.status == "PAID":
        return make_envelope(
            success=False,
            error="This application has been paid for and can no longer be edited.",
            code=409,
        )
    return None


@application_bp.route("/app/start", methods=["POST"])
@login_required
def start_application():
    student_id = session.get("student_id")
    student = Student.query.get(student_id)
    if not student:
        return make_envelope(success=False, error="Student account not found", code=404)

    app = Application.query.filter_by(student_id=student_id).first()
    if not app:
        app = Application(
            student_id=student_id,
            status="IN_PROGRESS",
            guidelines_accepted_at=datetime.now(timezone.utc),
        )
        db.session.add(app)
        db.session.commit()
    elif app.status == "NOT_STARTED":
        app.status = "IN_PROGRESS"
        app.guidelines_accepted_at = datetime.now(timezone.utc)
        db.session.commit()

    return make_envelope(success=True, data={"application_id": str(app.id)})


def _student_profile(student_id):
    s = Student.query.get(student_id)
    if not s:
        return None
    dob = getattr(s, "date_of_birth", None)
    return {
        "full_name": getattr(s, "full_name", None),
        "date_of_birth": dob.isoformat() if dob else None,
        "gender": getattr(s, "gender", None),
        "email": getattr(s, "email", None),
        "phone": getattr(s, "phone", None),
    }


@application_bp.route("/app/current", methods=["GET"])
@login_required
def current_application():
    student_id = session.get("student_id")
    profile = _student_profile(student_id)
    app = Application.query.filter_by(student_id=student_id).first()
    if not app:
        return make_envelope(
            success=True,
            data={
                "application_id": None,
                "status": None,
                "guidelines_accepted": False,
                "profile": profile,
            },
        )
    return make_envelope(
        success=True,
        data={
            "application_id": str(app.id),
            "status": app.status,
            "guidelines_accepted": app.guidelines_accepted_at is not None,
            "profile": profile,
        },
    )


@application_bp.route("/app/draft/<application_id>", methods=["GET"])
@login_required
def get_draft(application_id):
    student_id = session.get("student_id")
    app = Application.query.filter_by(id=application_id, student_id=student_id).first()
    if not app:
        return make_envelope(success=False, error="Application not found", code=404)

    drafts = (
        FormDraft.query.filter_by(application_id=app.id)
        .order_by(FormDraft.step_number)
        .all()
    )
    steps = {}
    for draft in drafts:
        steps[str(draft.step_number)] = draft.data if isinstance(draft.data, dict) else {}
    last_step = max((d.step_number for d in drafts), default=0)

    return make_envelope(
        success=True,
        data={
            "draft": steps,
            "last_step": last_step,
            "status": app.status,
            "documents": {
                "photo_url": app.photo_url,
                "signature_url": app.signature_url,
                "id_proof_url": app.id_proof_url,
            },
        },
    )


@application_bp.route("/app/draft/<application_id>/step/<int:step_number>", methods=["PATCH"])
@login_required
def save_draft_step(application_id, step_number):
    student_id = session.get("student_id")
    app = Application.query.filter_by(id=application_id, student_id=student_id).first()
    if not app:
        return make_envelope(success=False, error="Application not found", code=404)

    if step_number < 1 or step_number > 6:
        return make_envelope(success=False, error="Step number must be between 1 and 6", code=400)

    locked = _locked_after_payment(app)
    if locked:
        return locked

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return make_envelope(success=False, error="Request body must be a JSON object", code=400)

    try:
        # Step 4: Sync programme & specialisation directly to application record
        if step_number == 4:
            if "programme" in payload:
                app.programme = payload["programme"]
            if "specialisation" in payload:
                app.specialisation = payload["specialisation"]

        # Upsert form_drafts row: REPLACE the step's data (no merge), so stale
        # hidden fields cannot survive (FR-6.7).
        stmt = insert(FormDraft).values(
            application_id=app.id,
            step_number=step_number,
            data=payload,
            updated_at=func.now(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["application_id", "step_number"],
            set_={"data": stmt.excluded.data, "updated_at": func.now()},
        )
        db.session.execute(stmt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_envelope(success=False, error=f"Failed to save draft: {str(e)}", code=500)

    return make_envelope(success=True, data={"step_number": step_number, "saved": True})


@application_bp.route("/app/upload/<application_id>/<doc_type>", methods=["POST"])
@login_required
def upload_document(application_id, doc_type):
    student_id = session.get("student_id")
    app = Application.query.filter_by(id=application_id, student_id=student_id).first()
    if not app:
        return make_envelope(success=False, error="Application not found", code=404)

    if doc_type not in ["photo", "signature", "id_proof"]:
        return make_envelope(success=False, error="Invalid document type", code=400)

    locked = _locked_after_payment(app)
    if locked:
        return locked

    file = request.files.get("file")
    if not file:
        return make_envelope(success=False, error="No file provided", code=400)

    file_bytes = file.read()
    file_size = len(file_bytes)

    # Server-Side Validation per SRD FR-6.8
    if doc_type == "photo":
        if file_size > 500 * 1024:
            return make_envelope(success=False, error="Photo must be under 500 KB", code=400)
        try:
            img = Image.open(BytesIO(file_bytes))
            img.verify()
            img = Image.open(BytesIO(file_bytes))
            if img.format != "PNG":
                return make_envelope(success=False, error="Photo must be PNG format", code=400)
            w, h = img.size
            if not (150 <= w <= 600 and 200 <= h <= 800):
                return make_envelope(
                    success=False,
                    error="Photo dimensions must be between 150x200 and 600x800 px",
                    code=400,
                )
        except Exception:
            return make_envelope(success=False, error="Invalid photo image file", code=400)
        ext = "png"
        content_type = "image/png"

    elif doc_type == "signature":
        if file_size > 200 * 1024:
            return make_envelope(success=False, error="Signature must be under 200 KB", code=400)
        try:
            img = Image.open(BytesIO(file_bytes))
            img.verify()
            img = Image.open(BytesIO(file_bytes))
            if img.format != "PNG":
                return make_envelope(success=False, error="Signature must be PNG format", code=400)
        except Exception:
            return make_envelope(success=False, error="Invalid signature image file", code=400)
        ext = "png"
        content_type = "image/png"

    elif doc_type == "id_proof":
        if file_size > 2 * 1024 * 1024:
            return make_envelope(success=False, error="ID proof must be under 2 MB", code=400)
        if not file_bytes.startswith(b"%PDF"):
            return make_envelope(
                success=False, error="ID proof must be a valid PDF document", code=400
            )
        ext = "pdf"
        content_type = "application/pdf"

    # Standard object name, grouped under applications/<id>/ (helps FR-7.3 cleanup)
    object_name = f"applications/{app.id}/{doc_type}.{ext}"
    previous_object = getattr(app, f"{doc_type}_url", None)

    # Upload the NEW file first so a failed upload never loses the old one.
    try:
        minio_service.upload_object(object_name, file_bytes, content_type)
    except Exception as e:
        return make_envelope(
            success=False, error=f"Storage upload failed: {str(e)}", code=502
        )

    # Store object_name in DB
    try:
        setattr(app, f"{doc_type}_url", object_name)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return make_envelope(success=False, error=f"Failed to record upload: {str(e)}", code=500)

    # Remove the old object only if it has a different name (same name was
    # already overwritten by the upload). A cleanup failure must not fail the request.
    if previous_object and previous_object != object_name:
        try:
            minio_service.delete_object(previous_object)
        except Exception:
            pass

    return make_envelope(success=True, data={"object_name": object_name})
