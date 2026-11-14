"""Authentication Business Logic Service.

Manages registration validation, password complexity enforcement,
credential verification, and JWT token issuance and revocation.
"""

import re
from typing import Tuple, Dict, Any, Optional
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User, TokenBlocklist
from backend.app.services.user_service import UserService

# Email RFC 5322 standard regex pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthService:
    """Authentication and validation orchestrator."""

    @staticmethod
    def validate_password_complexity(password: str) -> Optional[str]:
        """Validates password against enterprise complexity standards.

        Rules:
        - Minimum 8 characters.
        - At least one uppercase letter.
        - At least one lowercase letter.
        - At least one numeric digit.
        - At least one special character.
        """
        if not password or len(password) < 8:
            return "Password must be at least 8 characters in length."
        if not re.search(r"[A-Z]", password):
            return "Password must contain at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return "Password must contain at least one lowercase letter."
        if not re.search(r"\d", password):
            return "Password must contain at least one numeric digit."
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\\[\]/]", password):
            return "Password must contain at least one special character (e.g. !@#$%^&*)."
        return None

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Verifies email structure meets standard format."""
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    @classmethod
    def register_user(cls, data: Dict[str, Any]) -> Tuple[Optional[User], Optional[Dict[str, str]]]:
        """Validates user registration payload and creates user record."""
        errors: Dict[str, str] = {}

        full_name = data.get("full_name", "").strip() if isinstance(data.get("full_name"), str) else ""
        email = data.get("email", "").strip().lower() if isinstance(data.get("email"), str) else ""
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        # 1. Full Name Validation
        if not full_name:
            errors["full_name"] = "Full name is required and cannot be empty."

        # 2. Email Validation
        if not email:
            errors["email"] = "Email address is required."
        elif not cls.validate_email_format(email):
            errors["email"] = "Invalid email format. Please provide a valid email address."
        elif UserService.get_by_email(email) is not None:
            errors["email"] = "An account with this email address already exists."

        # 3. Password Validation
        if not password:
            errors["password"] = "Password is required."
        else:
            pw_error = cls.validate_password_complexity(password)
            if pw_error:
                errors["password"] = pw_error

        # 4. Confirm Password Match
        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return None, errors

        # Create user via UserService
        user = UserService.create_user(full_name=full_name, email=email, password=password)
        return user, None

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> Tuple[Optional[User], Optional[str], Optional[str]]:
        """Verifies credentials, checks active status, and generates JWT access token.

        Returns:
            Tuple of (user, access_token, error_message)
        """
        if not email or not password:
            return None, None, "Email and password are required."

        normalized_email = email.strip().lower()
        user = UserService.get_by_email(normalized_email)

        # Constant-time comparison / generic failure message prevents user enumeration
        if not user or not user.check_password(password):
            return None, None, "Invalid email or password."

        if not user.is_active:
            return None, None, "Your account has been deactivated. Please contact support."

        # Update last login timestamp
        UserService.update_last_login(user)

        # Generate JWT with string user ID as identity
        access_token = create_access_token(identity=str(user.id))
        return user, access_token, None

    @staticmethod
    def revoke_token(jti: str, user_id: int) -> None:
        """Stores token unique JTI in revocation blocklist."""
        revoked = TokenBlocklist(jti=jti, user_id=user_id, token_type="access")
        db.session.add(revoked)
        db.session.commit()

    @staticmethod
    def is_token_revoked(jti: str) -> bool:
        """Checks if a token JTI has been revoked."""
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None

