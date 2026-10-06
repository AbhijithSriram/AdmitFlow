from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import get_config
from app.extensions import bcrypt, cors, db, limiter, session
from app.logging_config import setup_logging


def create_app(config_name: str | None = None) -> Flask:
    setup_logging()  # redacting log handler (NFR-6); must run before the app is built

    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # Behind Nginx every request would otherwise appear to come from 127.0.0.1, so all
    # users would share one rate-limit bucket. Trust exactly one proxy hop in production.
    if not app.config.get("DEBUG") and not app.config.get("TESTING"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    bcrypt.init_app(app)
    # Flask-Session's SQLAlchemy backend creates its own SQLAlchemy instance unless
    # told to reuse an existing one — without this line it collides with `db` above
    # ("A 'SQLAlchemy' instance has already been registered on this Flask app").
    app.config["SESSION_SQLALCHEMY"] = db
    session.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])

    register_blueprints(app)
    register_security_headers(app)
    register_error_handlers(app)

    return app


def register_blueprints(app: Flask) -> None:
    from app.blueprints.admin import admin_bp
    from app.blueprints.application import application_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.payment import payment_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(application_bp, url_prefix="/api")
    app.register_blueprint(payment_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(429)
    def rate_limited(_err):
        # Keep the {success, error} envelope (SRD 7.1) instead of Flask-Limiter's HTML page.
        return jsonify({"success": False, "error": "Too many requests. Please wait a minute and try again."}), 429
