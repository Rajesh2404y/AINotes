"""
Unit and integration tests for Quiz Service and Attempt Service.
"""
import pytest
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.services.quiz_service import quiz_service, QuizServiceError
from backend.app.services.quiz_attempt_service import quiz_attempt_service


SAMPLE_SOURCE = """
Operating systems coordinate hardware resources and offer an execution platform for applications.
The kernel serves as the central control module managing CPU scheduling, memory allocation, and I/O devices.
Virtual memory provides an illusion of vast contiguous memory using paging and segmentation tables.
Process synchronization prevents race conditions when concurrent processes access shared memory.
Deadlocks occur when processes hold resources while waiting for other held resources in a cyclic dependency.
"""


@pytest.fixture
def service_user(app):
    with app.app_context():
        user = User.query.filter_by(email="quiz_service_user@example.com").first()
        if not user:
            user = User(
                full_name="Quiz Service User",
                email="quiz_service_user@example.com",
                is_active=True
            )
            user.set_password("SecurePass123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def service_doc(app, service_user):
    with app.app_context():
        doc = Document(
            user_id=service_user,
            original_filename="os_notes.txt",
            stored_filename="os_notes.txt",
            file_type="txt",
            file_size=1024,
            processing_status="COMPLETED",
            extraction_quality="HIGH",
            extracted_text=SAMPLE_SOURCE,
            total_words=65
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id


def test_create_quiz_from_document(app, service_user, service_doc):
    with app.app_context():
        quiz = quiz_service.create_quiz(
            user_id=service_user,
            document_id=service_doc,
            difficulty="medium",
            total_questions=5
        )
        assert quiz.id is not None
        assert quiz.user_id == service_user
        assert quiz.document_id == service_doc
        assert quiz.total_questions > 0
        assert quiz.questions.count() > 0


def test_create_quiz_missing_source(app, service_user):
    with app.app_context():
        with pytest.raises(QuizServiceError, match="Either 'document_id' or 'summary_id' must be provided"):
            quiz_service.create_quiz(user_id=service_user)


def test_submit_quiz_attempt(app, service_user, service_doc):
    with app.app_context():
        quiz = quiz_service.create_quiz(
            user_id=service_user,
            document_id=service_doc,
            difficulty="medium",
            total_questions=4
        )

        questions = quiz.questions.all()
        # Answer the first question correctly, rest empty
        responses_payload = [
            {"question_id": questions[0].id, "answer": questions[0].correct_answer}
        ]

        attempt_data = quiz_attempt_service.submit_attempt(
            quiz_id=quiz.id,
            user_id=service_user,
            responses_payload=responses_payload
        )

        assert attempt_data["score"] >= 1
        assert attempt_data["total_questions"] == len(questions)
        assert 0 <= attempt_data["percentage"] <= 100.0
        assert "results" in attempt_data

