"""Quiz Attempt and Scoring Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class QuizAttempt(db.Model):
    """User submission record containing scores and performance metrics."""

    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False, default=0.0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="quiz_attempts")
    quiz = db.relationship("Quiz", back_populates="attempts")
    responses = db.relationship(
        "QuizResponse", back_populates="attempt", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_responses: bool = False) -> dict:
        """Serializes score summary and optional individual answer evaluations."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "quiz_id": self.quiz_id,
            "score": self.score,
            "total_questions": self.total_questions,
            "percentage": round(self.percentage, 2),
            "completed_at": to_utc_iso(self.completed_at),
        }
        if include_responses:
            data["responses"] = [r.to_dict() for r in self.responses.all()]
        return data

    def __repr__(self):
        return f"<QuizAttempt id={self.id} user_id={self.user_id} score={self.score}/{self.total_questions}>"

