"""Quiz Question Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Question(db.Model):
    """Individual assessment question belonging to a quiz."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(
        db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(
        db.String(50), nullable=False
    )  # true_false, one_word, mcq, fill_in_blank
    options = db.Column(db.JSON, nullable=True)  # List of choices for MCQ / T-F
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quiz = db.relationship("Quiz", back_populates="questions")
    responses = db.relationship(
        "QuizResponse", back_populates="question", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_answer: bool = False) -> dict:
        """Serializes question data. Does NOT reveal the correct answer unless explicitly specified."""
        data = {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "options": self.options or [],
            "source_reference": self.source_reference,
            "created_at": to_utc_iso(self.created_at),
        }
        if include_answer:
            data["correct_answer"] = self.correct_answer
            data["explanation"] = self.explanation
        return data

    def __repr__(self):
        return f"<Question id={self.id} quiz_id={self.quiz_id} type='{self.question_type}'>"

