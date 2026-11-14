"""Authentication and Authorization Guard Middleware.

Provides JWT validation decorators, current user resolution,
and cross-tenant ownership verification to guarantee tenant data isolation.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, current_user


def get_current_user():
    """Resolves the currently authenticated active User instance from Flask-JWT-Extended."""
    if current_user and getattr(current_user, "is_active", False):
        return current_user
    return None


def jwt_authenticated(fn):
    """Decorator ensuring request possesses a valid, non-revoked JWT access token

    and loads the authenticated active user.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user:
            return jsonify({
                "status": "error",
                "error": "Unauthorized",
                "message": "User account not found or deactivated.",
                "status_code": 401
            }), 401
        return fn(*args, **kwargs)
    return wrapper


def validate_resource_ownership(resource, user_id: int) -> bool:
    """Verifies that the target database resource belongs to the requesting user.

    Prevents Horizontal Privilege Escalation / cross-user data leakage.
    """
    if not resource:
        return False
    resource_user_id = getattr(resource, "user_id", None)
    return resource_user_id == user_id
