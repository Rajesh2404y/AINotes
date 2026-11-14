"""Quiz Answer Response Record Data Model.
"""

from backend.app.extensions import db


class QuizResponse(db.Model):
    """Stores a student's answer to a specific question during a quiz attempt."""

    __tablename__ = "quiz_responses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    attempt_id = db.Column(
        db.Integer, db.ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    attempt = db.relationship("QuizAttempt", back_populates="responses")
    question = db.relationship("Question", back_populates="responses")

    def to_dict(self) -> dict:
        """Serializes user response verification details."""
        return {
            "id": self.id,
            "attempt_id": self.attempt_id,
            "question_id": self.question_id,
            "selected_answer": self.selected_answer,
            "is_correct": self.is_correct,
            "question_text": self.question.question_text if self.question else None,
            "correct_answer": self.question.correct_answer if self.question else None,
            "explanation": self.question.explanation if self.question else None,
        }

    def __repr__(self):
        return f"<QuizResponse id={self.id} attempt_id={self.attempt_id} correct={self.is_correct}>"

