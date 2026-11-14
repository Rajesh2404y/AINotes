"""Quiz Configuration and Question Bank Data Model.
"""

from datetime import datetime
from backend.app.extensions import db
from backend.app.utils.datetime_utils import to_utc_iso


class Quiz(db.Model):
    """Quiz assessment session tied to source notes or summary."""

    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    summary_id = db.Column(
        db.Integer, db.ForeignKey("summaries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quiz_type = db.Column(
        db.String(50), nullable=False
    )  # true_false, one_word, mcq, fill_in_blank, mixed
    difficulty = db.Column(db.String(20), default="medium", nullable=False)  # easy, medium, hard
    total_questions = db.Column(db.Integer, default=5, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="quizzes")
    document = db.relationship("Document", back_populates="quizzes")
    summary = db.relationship("Summary", back_populates="quizzes")
    questions = db.relationship(
        "Question", back_populates="quiz", cascade="all, delete-orphan", lazy="dynamic"
    )
    attempts = db.relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan", lazy="dynamic"
    )

    def to_dict(self, include_questions: bool = False, include_answers: bool = False) -> dict:
        """Serializes quiz information, safely omitting correct answers during practice."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "summary_id": self.summary_id,
            "quiz_type": self.quiz_type,
            "difficulty": self.difficulty,
            "total_questions": self.total_questions,
            "created_at": to_utc_iso(self.created_at),
        }
        if include_questions:
            data["questions"] = [
                q.to_dict(include_answer=include_answers) for q in self.questions.all()
            ]
        return data

    def __repr__(self):
        return f"<Quiz id={self.id} type='{self.quiz_type}' total={self.total_questions}>"

