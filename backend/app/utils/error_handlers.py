"""Centralized API Error Handlers.

Provides standard JSON error responses across all HTTP error codes,
preventing sensitive stack traces from leaking to clients while logging
actionable error details for server diagnostics.
"""

import logging
from flask import jsonify

logger = logging.getLogger("ainotes.errors")


def register_error_handlers(app):
    """Registers standard HTTP and exception error handlers onto the Flask application."""

    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", "The request payload or parameters are invalid.")
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": str(message),
            "status_code": 400
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        message = getattr(error, "description", "Authentication is required to access this resource.")
        return jsonify({
            "status": "error",
            "error": "Unauthorized",
            "message": str(message),
            "status_code": 401
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        message = getattr(error, "description", "You do not have permission to access this resource.")
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": str(message),
            "status_code": 403
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        message = getattr(error, "description", "The requested API endpoint or resource was not found.")
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": str(message),
            "status_code": 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        message = getattr(error, "description", "The HTTP method is not allowed for this endpoint.")
        return jsonify({
            "status": "error",
            "error": "Method Not Allowed",
            "message": str(message),
            "status_code": 405
        }), 405

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            "status": "error",
            "error": "Payload Too Large",
            "message": "The uploaded file exceeds the configured maximum upload limit.",
            "status_code": 413
        }), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.exception("Unhandled server exception: %s", error)
        return jsonify({
            "status": "error",
            "error": "Internal Server Error",
            "message": "An unexpected server error occurred. Please try again later.",
            "status_code": 500
        }), 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        # If it's an HTTP exception from werkzeug, let the specific handler or fallback handle it
        code = getattr(error, "code", 500)
        name = getattr(error, "name", "Internal Server Error")
        description = getattr(error, "description", "An unexpected error occurred.")
        
        logger.exception("Server encountered exception [Code %s]: %s", code, error)
        
        # Don't leak raw internal Python exceptions in production
        if code == 500:
            description = "An unexpected server error occurred. Please try again later."
            
        return jsonify({
            "status": "error",
            "error": name,
            "message": description,
            "status_code": code
        }), code

