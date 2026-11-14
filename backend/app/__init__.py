"""Flask Application Factory Package.

Configures the Flask instance, initializes extensions, configures logging (file + console),
registers blueprints, and binds centralized error handlers.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from backend.app.config import config_by_name
from backend.app.extensions import db, migrate, jwt, cors
from backend.app.routes import (
    health_bp,
    auth_bp,
    dashboard_bp,
    document_bp,
    summary_bp,
    quiz_bp,
    translation_bp,
    learning_bp,
    recommendation_bp,
    learning_path_bp,
    history_bp,
)
from backend.app.utils.error_handlers import register_error_handlers
import backend.app.models  # Ensure all SQLAlchemy models are registered


def setup_logging(app):
    """Configures console and rotating file logging."""
    log_folder = app.config.get("LOG_FOLDER")
    if log_folder:
        os.makedirs(log_folder, exist_ok=True)

    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(name)s [%(filename)s:%(lineno)d]: %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)

    # File Handler
    log_file = app.config.get("LOG_FILE")
    if log_file and not app.config.get("TESTING"):
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB per log file
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)


def create_app(config_name=None):
    """Factory function creating and configuring the Flask application instance."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app_config = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(app_config)

    # Ensure required folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Setup Logging
    setup_logging(app)

    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Register Centralized HTTP and Exception Error Handlers
    register_error_handlers(app)

    # JWT Specific Error Callbacks
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({
            "status": "error",
            "error": "Unauthorized",
            "message": "Missing authorization token in request header.",
            "status_code": 401
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({
            "status": "error",
            "error": "Invalid Token",
            "message": "Signature verification failed or token is malformed.",
            "status_code": 401
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "status": "error",
            "error": "Token Expired",
            "message": "The authorization token has expired. Please log in again.",
            "status_code": 401
        }), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
        from backend.app.models.user import TokenBlocklist
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "status": "error",
            "error": "Token Revoked",
            "message": "The authorization token has been revoked. Please log in again.",
            "status_code": 401
        }), 401

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from backend.app.models.user import User
        identity = jwt_data["sub"]
        try:
            return db.session.get(User, int(identity))
        except (ValueError, TypeError):
            return None

    # Register API Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(summary_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(learning_path_bp)
    app.register_blueprint(history_bp)

    # Frontend Static Serving with Performance Optimization
    frontend_dir = os.path.abspath(os.path.join(app.root_path, "..", "..", "frontend"))
    if os.path.exists(frontend_dir):
        from flask import send_from_directory, abort, request
        import gzip

        @app.route("/", defaults={"filename": "index.html"})
        @app.route("/<path:filename>")
        def serve_frontend(filename):
            if filename.startswith("api"):
                abort(404)
            file_path = os.path.join(frontend_dir, filename)
            if os.path.isfile(file_path):
                return send_from_directory(frontend_dir, filename)
            html_path = os.path.join(frontend_dir, f"{filename}.html")
            if os.path.isfile(html_path):
                return send_from_directory(frontend_dir, f"{filename}.html")
            abort(404)

        @app.after_request
        def add_caching_and_compression(response):
            # 1. Caching Headers
            path = request.path.lower()
            if any(path.endswith(ext) for ext in [".ttf", ".woff", ".woff2", ".otf"]):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif any(path.endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico"]):
                response.headers["Cache-Control"] = "public, max-age=86400"
            elif path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            else:
                response.headers["Cache-Control"] = "no-cache"

            # 2. Transparent Gzip Compression
            accept_encoding = request.headers.get("Accept-Encoding", "")
            if (
                "gzip" in accept_encoding
                and response.status_code == 200
                and not response.direct_passthrough
                and response.mimetype in ["text/html", "text/css", "application/javascript", "application/json", "image/svg+xml"]
                and response.content_length
                and response.content_length > 400
                and "Content-Encoding" not in response.headers
            ):
                response.direct_passthrough = False
                compressed_data = gzip.compress(response.get_data())
                response.set_data(compressed_data)
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = len(compressed_data)
                response.headers["Vary"] = "Accept-Encoding"

            return response

    app.logger.info("Application initialized successfully in %s mode", config_name)
    return app
