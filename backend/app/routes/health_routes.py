"""Health Check and Root API Routes.

Provides diagnostic health inspection including real database connectivity
verification and general API metadata discovery.
"""

import logging
from flask import Blueprint, jsonify
from sqlalchemy import text
from backend.app.extensions import db

logger = logging.getLogger("ainotes.health")
health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/", methods=["GET"])
def api_root():
    """Returns basic API welcome message, version, and documentation status."""
    return jsonify({
        "status": "success",
        "service": "AI Notes Summarizer with Quiz Generation and Multilingual Translator API",
        "version": "1.0.0",
        "environment": "active",
        "documentation": "/api/docs"
    }), 200


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Checks service health and executes a live database ping.

    Expected response:
    {
      "status": "success",
      "message": "AI Notes Summarizer API is running",
      "database": "connected"
    }
    """
    db_status = "disconnected"
    try:
        # Perform real query execution on the configured database engine
        result = db.session.execute(text("SELECT 1")).scalar()
        if result == 1:
            db_status = "connected"
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return jsonify({
            "status": "error",
            "message": "AI Notes Summarizer API is running but database is unreachable",
            "database": "disconnected",
            "error_detail": str(exc)
        }), 503

    return jsonify({
        "status": "success",
        "message": "AI Notes Summarizer API is running",
        "database": db_status
    }), 200

