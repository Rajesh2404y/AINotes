"""Document Ingestion and Text Extraction Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Document(db.Model):
    """Uploaded study document containing extracted textual content and extraction quality metrics."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=True)
    file_type = db.Column(db.String(30), nullable=False)  # pdf, docx, txt, png, jpg, jpeg, text_paste
    file_size = db.Column(db.Integer, nullable=False, default=0)  # bytes
    extracted_text = db.Column(db.Text, nullable=True, default="")
    cleaned_text = db.Column(db.Text, nullable=True, default="")
    processing_status = db.Column(db.String(50), default="uploaded", nullable=False)
    extraction_quality = db.Column(db.String(20), default="PENDING", nullable=True)
    total_pages = db.Column(db.Integer, default=1, nullable=False)
    total_words = db.Column(db.Integer, default=0, nullable=False)
    total_characters = db.Column(db.Integer, default=0, nullable=False)
    ocr_used = db.Column(db.Boolean, default=False, nullable=False)
    extraction_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="documents")
    summaries = db.relationship(
        "Summary", back_populates="document", cascade="all, delete-orphan", lazy="dynamic"
    )
    quizzes = db.relationship(
        "Quiz", back_populates="document", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_text: bool = True) -> dict:
        """Serializes document metadata and text payload."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "processing_status": self.processing_status,
            "extraction_quality": self.extraction_quality,
            "total_pages": self.total_pages,
            "total_words": self.total_words,
            "total_characters": self.total_characters,
            "ocr_used": self.ocr_used,
            "extraction_metadata": self.extraction_metadata or {},
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }
        if include_text:
            data["extracted_text"] = self.extracted_text or ""
            data["cleaned_text"] = self.cleaned_text or ""
            data["word_count"] = self.total_words or (len(self.extracted_text.split()) if self.extracted_text else 0)
        return data

    def __repr__(self):
        return f"<Document id={self.id} user_id={self.user_id} filename='{self.original_filename}'>"
