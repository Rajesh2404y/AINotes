"""Multilingual Translation Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Translation(db.Model):
    """Stores multilingual translations of summarized notes."""

    __tablename__ = "translations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary_id = db.Column(
        db.Integer, db.ForeignKey("summaries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_language = db.Column(db.String(50), default="en", nullable=False)
    target_language = db.Column(db.String(50), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    translated_text = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(100), nullable=True)
    total_chunks = db.Column(db.Integer, default=1, nullable=True)
    processing_duration = db.Column(db.Float, default=0.0, nullable=True)
    translation_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="translations")
    summary = db.relationship("Summary", back_populates="translations")

    def to_dict(self) -> dict:
        """Serializes translation record."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "summary_id": self.summary_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "model_name": self.model_name or "facebook/nllb-200-distilled-600M",
            "total_chunks": self.total_chunks or 1,
            "processing_duration": round(self.processing_duration or 0.0, 2),
            "metadata": self.translation_metadata or {},
            "created_at": to_utc_iso(self.created_at),
        }

    def __repr__(self):
        return f"<Translation id={self.id} lang='{self.target_language}' user_id={self.user_id}>"

