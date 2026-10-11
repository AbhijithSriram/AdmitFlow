import os
from flask import Blueprint, jsonify, make_response, request
from app.extensions import db, limiter
from app.services import minio_service

# url_prefix="/app" + main app's "/api" prefix = "/api/app"
application_bp = Blueprint("application", __name__, url_prefix="/app")

# Exempt blueprint from global Flask-Limiter rules (Fixes 403 Forbidden)
limiter.exempt(application_bp)

DEFAULT_STUDENT_ID = "00000000-0000-0000-0000-000000000001"

ALLOWED_DOC_TYPES = {
    'photo': {
        'max_bytes': 500 * 1024,
        'mimes': ['image/png', 'image/jpeg'],
        'col': 'photo_url',
    },
    'signature': {
        'max_bytes': 200 * 1024,
        'mimes': ['image/png', 'image/jpeg'],
        'col': 'signature_url',
    },
    'id_proof': {
        'max_bytes': 2 * 1024 * 1024,
        'mimes': ['application/pdf'],
        'col': 'id_proof_url',
    },
}

def make_cors_response(data, code=200):
    res = make_response(jsonify(data), code)
    res.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    res.headers["Access-Control-Allow-Credentials"] = "true"
    res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    res.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
    return res

@application_bp.after_request
def apply_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
    return response

@application_bp.route('/upload/<app_id>/<doc_type>', methods=['POST', 'OPTIONS'], strict_slashes=False)
def upload_document(app_id, doc_type):
    if request.method == 'OPTIONS':
        return make_cors_response({'success': True}, 200)

    if doc_type not in ALLOWED_DOC_TYPES:
        return make_cors_response({'success': False, 'error': 'Invalid document type'}, 400)

    file = request.files.get('file')
    if not file:
        return make_cors_response({'success': False, 'error': 'No file uploaded'}, 400)

    rules = ALLOWED_DOC_TYPES[doc_type]

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > rules['max_bytes']:
        return make_cors_response({
            'success': False,
            'error': f'File size exceeds limit of {rules["max_bytes"] // 1024}KB'
        }, 400)

    target_id = app_id if app_id and app_id != 'undefined' else DEFAULT_STUDENT_ID

    # Ensure application record exists in DB
    try:
        db.session.execute(
            db.text("""
                INSERT INTO applications (id, student_id, status)
                VALUES (:id, :id, 'draft')
                ON CONFLICT (id) DO NOTHING;
            """),
            {'id': target_id}
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    # MinIO storage upload
    object_name = f"{target_id}/{doc_type}_{file.filename}"
    file_url = minio_service.upload_file(
        file, object_name, file.content_type or 'application/octet-stream'
    )

    # Persist document URL into applications table
    try:
        db.session.execute(
            db.text(f"UPDATE applications SET {rules['col']} = :url WHERE id = :app_id"),
            {'url': file_url, 'app_id': target_id}
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        return make_cors_response({'success': False, 'error': 'Database update failed'}, 500)

    return make_cors_response({'success': True, 'url': file_url}, 200)