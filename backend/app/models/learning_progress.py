"""Learning Progress Tracking Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class LearningProgress(db.Model):
    """Tracks persistent or cached topic-level mastery and question performance per user."""

    __tablename__ = "learning_progress"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic = db.Column(db.String(255), nullable=False, index=True)
    attempted_questions = db.Column(db.Integer, default=0, nullable=False)
    correct_answers = db.Column(db.Integer, default=0, nullable=False)
    accuracy = db.Column(db.Float, default=0.0, nullable=False)
    performance_status = db.Column(db.String(50), default="Insufficient Data", nullable=False)
    last_attempted_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="learning_progress")

    def to_dict(self) -> dict:
        """Serializes learning progress record into dictionary format."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "attempted_questions": self.attempted_questions,
            "correct_answers": self.correct_answers,
            "accuracy": round(self.accuracy, 2),
            "performance_status": self.performance_status,
            "last_attempted_at": to_utc_iso(self.last_attempted_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

    def __repr__(self):
        return f"<LearningProgress user={self.user_id} topic='{self.topic}' acc={self.accuracy}%>"

