"""User and Token Revocation Data Models.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso, format_display_datetime


class User(db.Model):
    """User account entity for students and platform members."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships with cascading deletes
    documents = db.relationship(
        "Document", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    summaries = db.relationship(
        "Summary", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    quizzes = db.relationship(
        "Quiz", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    quiz_attempts = db.relationship(
        "QuizAttempt", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    translations = db.relationship(
        "Translation", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    learning_progress = db.relationship(
        "LearningProgress", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    recommendations = db.relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    learning_paths = db.relationship(
        "LearningPath", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )
    revoked_tokens = db.relationship(
        "TokenBlocklist", back_populates="user", cascade="all, delete-orphan", lazy="dynamic"
    )

    def set_password(self, password: str):
        """Hashes password using secure PBKDF2:SHA256 algorithm."""
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        """Verifies supplied password against stored cryptographic hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Serializes user entity into safe dictionary format with explicit UTC timestamps."""
        data = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
            "last_login": to_utc_iso(self.last_login),
            "last_login_display": format_display_datetime(self.last_login) if self.last_login else None,
        }
        if include_sensitive:
            data["has_password"] = bool(self.password_hash)
        return data

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}'>"


class TokenBlocklist(db.Model):
    """Stores revoked JWT token identifiers (JTI) for logout enforcement."""

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False, default="access")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="revoked_tokens")

    def __repr__(self):
        return f"<TokenBlocklist id={self.id} jti='{self.jti}'>"

