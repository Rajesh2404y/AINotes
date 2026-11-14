"""AI Summarization Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Summary(db.Model):
    """AI-generated summary record with extracted keywords, definitions, and takeaways."""

    __tablename__ = "summaries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary_type = db.Column(db.String(50), nullable=False)  # short, medium, detailed
    summary_text = db.Column(db.Text, nullable=False)
    key_takeaways = db.Column(db.JSON, nullable=True)  # List of bullet takeaway points
    definitions = db.Column(db.JSON, nullable=True)  # List of {term, definition}
    keywords = db.Column(db.JSON, nullable=True)  # List of keyword strings
    model_name = db.Column(db.String(100), nullable=True)
    model_version = db.Column(db.String(50), nullable=True)
    source_token_count = db.Column(db.Integer, default=0, nullable=True)
    generated_token_count = db.Column(db.Integer, default=0, nullable=True)
    total_chunks = db.Column(db.Integer, default=1, nullable=True)
    processing_duration = db.Column(db.Float, default=0.0, nullable=True)
    summary_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="summaries")
    document = db.relationship("Document", back_populates="summaries")
    quizzes = db.relationship(
        "Quiz", back_populates="summary", cascade="all, delete-orphan", lazy="dynamic"
    )
    translations = db.relationship(
        "Translation", back_populates="summary", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self) -> dict:
        """Serializes summary attributes."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "summary_type": self.summary_type,
            "summary_text": self.summary_text,
            "key_takeaways": self.key_takeaways or [],
            "definitions": self.definitions or [],
            "keywords": self.keywords or [],
            "metadata": {
                "model_name": self.model_name or "sshleifer/distilbart-cnn-12-6",
                "model_version": self.model_version or "1.0.0",
                "source_token_count": self.source_token_count or 0,
                "generated_token_count": self.generated_token_count or 0,
                "total_chunks": self.total_chunks or 1,
                "processing_duration": round(self.processing_duration or 0.0, 2),
                **(self.summary_metadata or {})
            },
            "created_at": to_utc_iso(self.created_at),
        }

    def __repr__(self):
        return f"<Summary id={self.id} type='{self.summary_type}' doc_id={self.document_id}>"
