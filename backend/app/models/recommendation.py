"""Personalized Learning Recommendation Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Recommendation(db.Model):
    """Personalized learning activity recommendation tailored to user performance."""

    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic = db.Column(db.String(255), nullable=False, index=True)
    recommendation_type = db.Column(
        db.String(50), nullable=False
    )  # review_summary, review_takeaways, review_definitions, practice_quiz, retry_weak_topic, advanced_quiz, revisit_document, continue_path, insufficient_data
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    suggested_action = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    related_document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    related_summary_id = db.Column(
        db.Integer, db.ForeignKey("summaries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    related_quiz_id = db.Column(
        db.Integer, db.ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    priority = db.Column(db.String(20), default="medium", nullable=False)  # high, medium, low
    status = db.Column(
        db.String(30), default="pending", nullable=False
    )  # pending, in_progress, completed, dismissed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="recommendations")
    document = db.relationship("Document")
    summary = db.relationship("Summary")
    quiz = db.relationship("Quiz")

    def to_dict(self) -> dict:
        """Serializes recommendation into API-ready dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "recommendation_type": self.recommendation_type,
            "title": self.title,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "reason": self.reason,
            "related_document_id": self.related_document_id,
            "related_summary_id": self.related_summary_id,
            "related_quiz_id": self.related_quiz_id,
            "priority": self.priority,
            "status": self.status,
            "created_at": to_utc_iso(self.created_at),
            "completed_at": to_utc_iso(self.completed_at),
        }

    def __repr__(self):
        return f"<Recommendation id={self.id} user={self.user_id} topic='{self.topic}' type='{self.recommendation_type}'>"

