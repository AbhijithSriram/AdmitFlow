from flask import Flask

from app.config import get_config
from app.extensions import bcrypt, cors, db, limiter, session


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    bcrypt.init_app(app)
    session.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])

    register_blueprints(app)
    register_security_headers(app)

    return app


def register_blueprints(app: Flask) -> None:
    from app.blueprints.admin import admin_bp
    from app.blueprints.application import application_bp
    from app.blueprints.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(application_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response
