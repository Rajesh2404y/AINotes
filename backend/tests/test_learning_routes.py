"""Integration tests for Learning, Recommendations, and Learning Path REST APIs.
"""

import pytest
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.learning_path import LearningPath, LearningPathActivity
from backend.app.models.recommendation import Recommendation
from backend.app.models.user import User


@pytest.fixture
def auth_headers(app):
    """Generates standard authorized student headers."""
    with app.app_context():
        user = User.query.filter_by(email="learning_student@example.com").first()
        if not user:
            user = User(
                full_name="Learning Student",
                email="learning_student@example.com",
                is_active=True,
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {token}"}


def test_learning_endpoints_unauthorized(client):
    """Verifies that unauthenticated requests to learning APIs return 401."""
    assert client.get("/api/learning/overview").status_code == 401
    assert client.get("/api/learning/topics").status_code == 401
    assert client.get("/api/recommendations").status_code == 401
    assert client.post("/api/recommendations/generate").status_code == 401
    assert client.get("/api/learning-paths").status_code == 401
    assert client.post("/api/learning-paths/generate", json={"topic": "Math"}).status_code == 401


def test_learning_overview_and_topics_success(client, auth_headers):
    """Verifies authenticated retrieval of learning overview and topic performance."""
    # 1. Overview
    res = client.get("/api/learning/overview", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "total_quizzes_attempted" in data
    assert "recommended_next_action" in data

    # 2. Topics
    res2 = client.get("/api/learning/topics", headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.get_json()["data"]
    assert "topics" in data2
    assert "difficulty_breakdown" in data2

    # 3. Adaptive Difficulty
    res3 = client.get("/api/learning/adaptive-difficulty", headers=auth_headers)
    assert res3.status_code == 200
    data3 = res3.get_json()["data"]
    assert "recommended_difficulty" in data3


def test_recommendation_routes_crud(client, auth_headers):
    """Verifies generating, listing, and updating recommendations via REST."""
    # Generate recommendations
    gen_res = client.post("/api/recommendations/generate", json={}, headers=auth_headers)
    assert gen_res.status_code == 200
    recs = gen_res.get_json()["data"]
    assert isinstance(recs, list)
    assert len(recs) >= 1
    rec_id = recs[0]["id"]

    # List recommendations with filtering
    list_res = client.get("/api/recommendations?status=pending", headers=auth_headers)
    assert list_res.status_code == 200
    assert "data" in list_res.get_json()
    assert "pagination" in list_res.get_json()

    # Update recommendation status
    patch_res = client.patch(
        f"/api/recommendations/{rec_id}",
        json={"status": "completed"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["data"]["status"] == "completed"


def test_learning_path_routes_crud_and_cross_user_isolation(app, client, auth_headers):
    """Verifies learning path generation, activity completion, and cross-user isolation."""
    # Generate Learning Path
    create_res = client.post(
        "/api/learning-paths/generate",
        json={"topic": "Quantum Computing"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    path_data = create_res.get_json()["data"]
    path_id = path_data["id"]
    act_id = path_data["activities"][0]["id"]

    # List learning paths
    list_res = client.get("/api/learning-paths", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.get_json()["data"]) >= 1

    # Get path details
    detail_res = client.get(f"/api/learning-paths/{path_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    assert detail_res.get_json()["data"]["target_topic"] == "Quantum Computing"

    # Complete Activity 1
    comp_res = client.post(
        f"/api/learning-paths/{path_id}/activities/{act_id}/complete",
        headers=auth_headers,
    )
    assert comp_res.status_code == 200
    assert comp_res.get_json()["data"]["activity"]["status"] == "completed"

    # Cross-User Isolation: Create User B and attempt to access or delete User A's path
    with app.app_context():
        user_b = User(full_name="Attacker", email="attacker@example.com")
        user_b.set_password("SecurePass123!")
        db.session.add(user_b)
        db.session.commit()

        token_b = create_access_token(identity=str(user_b.id))
        headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B tries to view User A's path -> 403 Forbidden
    cross_get = client.get(f"/api/learning-paths/{path_id}", headers=headers_b)
    assert cross_get.status_code == 403

    # User B tries to delete User A's path -> 403 Forbidden
    cross_del = client.delete(f"/api/learning-paths/{path_id}", headers=headers_b)
    assert cross_del.status_code == 403

    # User A successfully deletes their path -> 200
    del_res = client.delete(f"/api/learning-paths/{path_id}", headers=auth_headers)
    assert del_res.status_code == 200
