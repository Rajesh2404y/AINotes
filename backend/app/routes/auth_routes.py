"""Authentication and User Profile REST API Endpoints.

Handles user registration, login, logout, profile discovery/update,
and password modification with JWT token management and rate limiting.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.app.services.auth_service import AuthService
from backend.app.services.user_service import UserService
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.utils.rate_limiter import rate_limit

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60)
def register():
    """POST /api/auth/register

    Registers a new student account with validated name, email, and password complexity.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid request payload. Expected JSON body.",
            "status_code": 400
        }), 400

    user, errors = AuthService.register_user(data)
    if errors:
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "errors": errors,
            "status_code": 400
        }), 400

    return jsonify({
        "status": "success",
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
@rate_limit(max_requests=15, window_seconds=60)
def login():
    """POST /api/auth/login

    Authenticates user credentials and issues a JWT access token.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid request payload. Expected JSON body.",
            "status_code": 400
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required.",
            "status_code": 400
        }), 400

    user, access_token, error_message = AuthService.authenticate_user(email, password)
    if error_message:
        return jsonify({
            "status": "error",
            "message": error_message,
            "status_code": 401
        }), 401

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": access_token
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_authenticated
def logout():
    """POST /api/auth/logout

    Invalidates the current session by placing the active token's JTI into the blocklist.
    """
    jwt_payload = get_jwt()
    jti = jwt_payload["jti"]
    user = get_current_user()

    AuthService.revoke_token(jti, user.id)

    return jsonify({
        "status": "success",
        "message": "Successfully logged out. Session invalidated."
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_authenticated
def get_current_user_profile():
    """GET /api/auth/me

    Returns the safe profile data of the currently authenticated user.
    """
    user = get_current_user()
    return jsonify({
        "status": "success",
        "user": user.to_dict()
    }), 200


@auth_bp.route("/profile", methods=["PUT"])
@jwt_authenticated
def update_profile():
    """PUT /api/auth/profile

    Updates the full_name and/or email address of the authenticated user.
    Protected against modifying user_id, password_hash, or active status.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid request payload. Expected JSON body.",
            "status_code": 400
        }), 400

    user = get_current_user()
    full_name = data.get("full_name")
    email = data.get("email")

    if email and not AuthService.validate_email_format(email):
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "errors": {"email": "Invalid email address format."},
            "status_code": 400
        }), 400

    try:
        updated_user = UserService.update_profile(user, full_name=full_name, email=email)
        return jsonify({
            "status": "success",
            "message": "Profile updated successfully",
            "user": updated_user.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "errors": {"email": str(ve)},
            "status_code": 400
        }), 400


@auth_bp.route("/change-password", methods=["POST"])
@jwt_authenticated
def change_password():
    """POST /api/auth/change-password

    Verifies the user's current password and securely updates to a new validated password.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid request payload. Expected JSON body.",
            "status_code": 400
        }), 400

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    user = get_current_user()

    # 1. Verify current password
    if not user.check_password(current_password):
        return jsonify({
            "status": "error",
            "message": "Current password is incorrect.",
            "status_code": 400
        }), 400

    # 2. Validate new password complexity
    pw_error = AuthService.validate_password_complexity(new_password)
    if pw_error:
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "errors": {"new_password": pw_error},
            "status_code": 400
        }), 400

    # 3. Confirm password matching
    if new_password != confirm_password:
        return jsonify({
            "status": "error",
            "message": "Validation failed",
            "errors": {"confirm_password": "New passwords do not match."},
            "status_code": 400
        }), 400

    # 4. Perform update
    UserService.change_password(user, new_password)

    return jsonify({
        "status": "success",
        "message": "Password changed successfully"
    }), 200

