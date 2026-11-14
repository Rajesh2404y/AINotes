"""Unit and integration tests for Adaptive Learning Paths and Activity Progression.
"""

import pytest
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.learning_path import LearningPath, LearningPathActivity
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.summary import Summary
from backend.app.models.user import User
from backend.app.services.learning_path_service import (
    LearningPathServiceError,
    learning_path_service,
)


def test_create_learning_path_with_milestones(app):
    """Verifies that creating a learning path initializes 4 ordered milestones."""
    with app.app_context():
        user = User(full_name="Path Student", email="path_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        path_data = learning_path_service.create_learning_path(
            user_id=user.id, target_topic="Operating Systems"
        )
        assert path_data["target_topic"] == "Operating Systems"
        assert path_data["status"] == "not_started"
        assert path_data["progress_percentage"] == 0.0
        assert len(path_data["activities"]) == 4

        # Verify activity sequences
        seqs = [a["sequence_number"] for a in path_data["activities"]]
        assert seqs == [1, 2, 3, 4]

        types = [a["activity_type"] for a in path_data["activities"]]
        assert types == ["summary_review", "takeaways_study", "definitions_review", "quiz_practice"]


def test_learning_path_progress_and_verification(app):
    """Verifies activity completion verification and percentage progress updates."""
    with app.app_context():
        user = User(full_name="Verify Student", email="verify_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        doc = Document(user_id=user.id, original_filename="ml.pdf", file_type="pdf")
        db.session.add(doc)
        db.session.commit()

        summary = Summary(
            user_id=user.id,
            document_id=doc.id,
            summary_type="medium",
            summary_text="ML summary notes",
        )
        db.session.add(summary)
        db.session.commit()

        path = learning_path_service.create_learning_path(
            user_id=user.id,
            target_topic="Machine Learning",
            document_id=doc.id,
            summary_id=summary.id,
        )
        path_id = path["id"]
        act1_id = path["activities"][0]["id"]
        act4_id = path["activities"][3]["id"]

        # Complete Activity 1 (summary_review)
        res = learning_path_service.complete_activity(user.id, path_id, act1_id)
        assert res["activity"]["status"] == "completed"
        assert res["path"]["progress_percentage"] == 25.0
        assert res["path"]["status"] == "in_progress"

        # Attempt to complete Activity 4 (quiz_practice) without any completed quiz attempt -> should fail
        with pytest.raises(LearningPathServiceError) as exc:
            learning_path_service.complete_activity(user.id, path_id, act4_id)
        assert exc.value.status_code == 422
        assert "no completed quiz attempt" in exc.value.message

        # Now simulate a completed quiz attempt
        quiz = Quiz(user_id=user.id, document_id=doc.id, summary_id=summary.id, quiz_type="mcq", total_questions=5)
        db.session.add(quiz)
        db.session.commit()

        att = QuizAttempt(user_id=user.id, quiz_id=quiz.id, score=4, total_questions=5, percentage=80.0)
        db.session.add(att)
        db.session.commit()

        # Now completing Activity 4 succeeds!
        res4 = learning_path_service.complete_activity(user.id, path_id, act4_id)
        assert res4["activity"]["status"] == "completed"
        assert res4["path"]["progress_percentage"] == 50.0


def test_learning_path_pause_resume_and_deletion(app):
    """Verifies pausing, resuming, and deleting a learning path."""
    with app.app_context():
        user = User(full_name="Lifecycle Student", email="life_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        path = learning_path_service.create_learning_path(
            user_id=user.id, target_topic="Cloud Computing"
        )
        path_id = path["id"]

        # Pause
        paused = learning_path_service.update_path_status(user.id, path_id, "paused")
        assert paused["status"] == "paused"

        # Resume
        resumed = learning_path_service.update_path_status(user.id, path_id, "in_progress")
        assert resumed["status"] == "in_progress"

        # Delete
        success = learning_path_service.delete_learning_path(user.id, path_id)
        assert success is True

        # Ensure deleted
        with pytest.raises(LearningPathServiceError):
            learning_path_service.get_path_details(user.id, path_id)
