"""Unit and integration tests for Personalized Recommendation Engine and Service.
"""

from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.question import Question
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.quiz_response import QuizResponse
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User
from backend.app.services.recommendation_service import recommendation_service


def test_generate_recommendations_insufficient_data(app):
    """Verifies baseline recommendation generation when student has no quiz attempts."""
    with app.app_context():
        user = User(full_name="Rec Student", email="rec_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        recs = recommendation_service.generate_user_recommendations(user.id)
        assert len(recs) >= 1
        assert recs[0]["recommendation_type"] == "insufficient_data"
        assert recs[0]["priority"] == "medium"


def test_generate_recommendations_for_weak_topic(app):
    """Verifies that low topic accuracy generates a high-priority retry_weak_topic recommendation."""
    with app.app_context():
        user = User(full_name="Weak Student", email="weak_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        doc = Document(user_id=user.id, original_filename="Database_Systems.pdf", file_type="pdf")
        db.session.add(doc)
        db.session.commit()

        quiz = Quiz(user_id=user.id, document_id=doc.id, quiz_type="mcq", difficulty="medium", total_questions=4)
        db.session.add(quiz)
        db.session.commit()

        questions = [
            Question(quiz_id=quiz.id, question_text=f"Question {i} about Indexing", question_type="mcq", correct_answer="B", source_reference="Document: Database Systems")
            for i in range(4)
        ]
        db.session.add_all(questions)
        db.session.commit()

        # Score 1 out of 4 (25%) -> Weak topic (< 50%)
        att = QuizAttempt(user_id=user.id, quiz_id=quiz.id, score=1, total_questions=4, percentage=25.0)
        db.session.add(att)
        db.session.commit()

        for idx, q in enumerate(questions):
            is_c = (idx == 0)
            db.session.add(QuizResponse(attempt_id=att.id, question_id=q.id, selected_answer="B" if is_c else "A", is_correct=is_c))
        db.session.commit()

        recs = recommendation_service.generate_user_recommendations(user.id)
        assert len(recs) >= 1
        weak_rec = next((r for r in recs if r["recommendation_type"] == "retry_weak_topic"), None)
        assert weak_rec is not None
        assert weak_rec["priority"] == "high"
        assert "Database Systems" in weak_rec["topic"]
        assert "below the 50%" in weak_rec["reason"]


def test_recommendation_status_lifecycle_and_duplicate_prevention(app):
    """Verifies status transitions (pending -> completed) and duplicate prevention."""
    with app.app_context():
        user = User(full_name="Status Student", email="status_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        rec = Recommendation(
            user_id=user.id,
            topic="Operating Systems",
            recommendation_type="review_summary",
            title="Review Notes",
            reason="Low score",
            priority="high",
            status="pending",
        )
        db.session.add(rec)
        db.session.commit()

        # Update status
        updated = recommendation_service.update_recommendation_status(user.id, rec.id, "completed")
        assert updated["status"] == "completed"
        assert updated["completed_at"] is not None

        # Change to dismissed
        dismissed = recommendation_service.update_recommendation_status(user.id, rec.id, "dismissed")
        assert dismissed["status"] == "dismissed"
