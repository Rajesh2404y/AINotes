"""SQLAlchemy Database Models Package.

Exports all relational database models for application entities:
User, Document, Summary, Quiz, Question, QuizAttempt, QuizResponse, Translation,
and TokenBlocklist.
"""

from backend.app.models.user import User, TokenBlocklist
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.models.quiz import Quiz
from backend.app.models.question import Question
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.quiz_response import QuizResponse
from backend.app.models.translation import Translation
from backend.app.models.learning_progress import LearningProgress
from backend.app.models.recommendation import Recommendation
from backend.app.models.learning_path import LearningPath, LearningPathActivity

__all__ = [
    "User",
    "TokenBlocklist",
    "Document",
    "Summary",
    "Quiz",
    "Question",
    "QuizAttempt",
    "QuizResponse",
    "Translation",
    "LearningProgress",
    "Recommendation",
    "LearningPath",
    "LearningPathActivity",
]
