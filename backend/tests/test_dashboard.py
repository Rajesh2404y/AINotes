"""Automated Tests for Dashboard Aggregation and Activity Timeline APIs.
"""

import pytest
import uuid
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.extensions import db


from flask_jwt_extended import create_access_token

@pytest.fixture
def auth_client(client, app):
    """Creates a unique user, seeds test documents & quiz attempts, and returns auth headers."""
    unique_email = f"dash_{uuid.uuid4().hex[:8]}@example.com"
    with app.app_context():
        user = User(full_name="Dashboard User", email=unique_email)
        user.set_password("DashPassword123!")
        db.session.add(user)
        db.session.commit()

        # Seed document for this specific user
        doc = Document(
            user_id=user.id,
            original_filename="biology.pdf",
            file_type="pdf",
            file_size=5000,
            extracted_text="Cell biology notes.",
            processing_status="completed"
        )
        db.session.add(doc)
        db.session.commit()

        # Seed quiz and attempt for this specific user
        quiz = Quiz(user_id=user.id, document_id=doc.id, quiz_type="mcq", total_questions=5)
        db.session.add(quiz)
        db.session.commit()

        attempt = QuizAttempt(
            user_id=user.id, quiz_id=quiz.id, score=4, total_questions=5, percentage=80.0
        )
        db.session.add(attempt)
        db.session.commit()

        token = create_access_token(identity=str(user.id))

    return client, {"Authorization": f"Bearer {token}"}


def test_dashboard_stats_authenticated(auth_client):
    """Test /api/dashboard/stats returns real counts from seeded database data."""
    client, headers = auth_client
    response = client.get("/api/dashboard/stats", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    stats = data["stats"]
    assert stats["total_documents"] >= 1
    assert stats["quizzes_attempted"] >= 1
    assert stats["total_quizzes_completed"] >= 1
    assert stats["average_quiz_score"] == 80.0
    assert stats["learning_activities"] >= 2
    assert "study_streak_days" in stats
    assert stats["study_streak_days"] >= 1


def test_dashboard_activities_timeline(auth_client):
    """Test /api/dashboard/activities returns sorted timeline events."""
    client, headers = auth_client
    response = client.get("/api/dashboard/activities", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    activities = data["activities"]
    assert len(activities) >= 1
    assert any(a["type"] == "document" for a in activities)


def test_dashboard_performance_chart_data(auth_client):
    """Test /api/dashboard/performance returns series arrays for Chart.js."""
    client, headers = auth_client
    response = client.get("/api/dashboard/performance", headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    perf = data["performance"]
    assert "labels" in perf
    assert "percentages" in perf
    assert "distribution" in perf
    assert perf["distribution"]["documents"] >= 1
    assert "weekly_activity" in perf
    assert len(perf["weekly_activity"]["labels"]) == 7
    assert len(perf["weekly_activity"]["documents"]) == 7
    assert "quiz_trends" in perf
    assert "category_distribution" in perf


def test_dashboard_unauthenticated_rejected(client):
    """Test unauthenticated calls are rejected with 401."""
    res_stats = client.get("/api/dashboard/stats")
    assert res_stats.status_code == 401
