"""Automated Tests for Profile Discovery, Updates, and Password Changes.
"""

import pytest
from flask_jwt_extended import create_access_token
from backend.app.models.user import User
from backend.app.extensions import db


@pytest.fixture
def auth_headers(client, app):
    """Provides valid authentication headers for a dedicated user."""
    email = "profile_user@example.com"
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(full_name="Profile User", email=email)
            user.set_password("CorrectPassword123!")
            db.session.add(user)
            db.session.commit()
        else:
            user.set_password("CorrectPassword123!")
            db.session.commit()

        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_profile_access_rejected(client):
    """Test accessing /api/auth/me without token returns 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_authenticated_profile_access_success(client, auth_headers):
    """Test accessing /api/auth/me with token returns user data without password hash."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "profile_user@example.com"
    assert "password_hash" not in data["user"]


def test_update_profile_full_name(client, auth_headers):
    """Test updating user's display name."""
    response = client.put("/api/auth/profile", headers=auth_headers, json={
        "full_name": "Updated Name"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["full_name"] == "Updated Name"


def test_update_profile_duplicate_email_rejected(client, auth_headers, app):
    """Test attempting to update email to one already registered is rejected."""
    with app.app_context():
        other = User.query.filter_by(email="other_reg@example.com").first()
        if not other:
            other = User(full_name="Other User", email="other_reg@example.com")
            other.set_password("OtherPassword123!")
            db.session.add(other)
            db.session.commit()

    response = client.put("/api/auth/profile", headers=auth_headers, json={
        "email": "other_reg@example.com"
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["errors"]


def test_change_password_success(client, auth_headers):
    """Test successful password modification."""
    response = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "CorrectPassword123!",
        "new_password": "NewSecurePassword123!",
        "confirm_password": "NewSecurePassword123!"
    })
    assert response.status_code == 200
    assert response.get_json()["message"] == "Password changed successfully"

    # Verify user can log in with new password
    new_login = client.post("/api/auth/login", json={
        "email": "profile_user@example.com",
        "password": "NewSecurePassword123!"
    })
    assert new_login.status_code == 200


def test_change_password_invalid_current_password(client, auth_headers):
    """Test password change fails when current password is wrong."""
    response = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "WrongCurrentPassword123!",
        "new_password": "AnotherPassword123!",
        "confirm_password": "AnotherPassword123!"
    })
    assert response.status_code == 400
    assert "current password is incorrect" in response.get_json()["message"].lower()
