"""User Management and Persistence Service.
"""

from datetime import datetime
from typing import Optional
from backend.app.extensions import db
from backend.app.models.user import User


class UserService:
    """Encapsulates CRUD operations and business logic for User accounts."""

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """Retrieves a user by primary key ID."""
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        """Retrieves a user by normalized lowercase email address."""
        if not email:
            return None
        normalized_email = email.strip().lower()
        return User.query.filter_by(email=normalized_email).first()

    @staticmethod
    def create_user(full_name: str, email: str, password: str) -> User:
        """Instantiates, hashes password, and persists a new User."""
        normalized_email = email.strip().lower()
        user = User(
            full_name=full_name.strip(),
            email=normalized_email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
            email_verified=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_profile(user: User, full_name: Optional[str] = None, email: Optional[str] = None) -> User:
        """Updates profile attributes ensuring email uniqueness constraint."""
        if full_name and full_name.strip():
            user.full_name = full_name.strip()

        if email and email.strip():
            normalized_email = email.strip().lower()
            if normalized_email != user.email:
                existing = User.query.filter_by(email=normalized_email).first()
                if existing and existing.id != user.id:
                    raise ValueError(f"Email '{normalized_email}' is already in use by another account.")
                user.email = normalized_email

        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user

    @staticmethod
    def update_last_login(user: User) -> None:
        """Updates the last_login timestamp upon successful authentication."""
        user.last_login = datetime.utcnow()
        db.session.commit()

    @staticmethod
    def change_password(user: User, new_password: str) -> None:
        """Hashes and updates user password."""
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()

