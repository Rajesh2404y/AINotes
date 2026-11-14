"""Automated Tests for User Login API and Token Issuance.
"""

import pytest
from backend.app.models.user import User
from backend.app.extensions import db


@pytest.fixture(autouse=True)
def setup_user(app):
    """Seed test user for login authentication tests."""
    with app.app_context():
        user = User.query.filter_by(email="login_test@example.com").first()
        if not user:
            user = User(
                full_name="Login Test User",
                email="login_test@example.com",
                is_active=True
            )
            user.set_password("CorrectPassword123!")
            db.session.add(user)
            db.session.commit()


def test_valid_login_returns_token(client):
    """Test valid credentials return 200 and a JWT access token."""
    response = client.post("/api/auth/login", json={
        "email": "login_test@example.com",
        "password": "CorrectPassword123!"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert len(data["access_token"]) > 20
    assert data["user"]["email"] == "login_test@example.com"


def test_invalid_password_rejected(client):
    """Test wrong password returns 401 without specific enumeration details."""
    response = client.post("/api/auth/login", json={
        "email": "login_test@example.com",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert "Invalid email or password" in data["message"]


def test_unknown_email_rejected(client):
    """Test non-existent email returns 401 with identical generic error."""
    response = client.post("/api/auth/login", json={
        "email": "does_not_exist@example.com",
        "password": "CorrectPassword123!"
    })
    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "error"
    assert "Invalid email or password" in data["message"]


def test_inactive_user_rejected(client, app):
    """Test deactivated account is denied login."""
    with app.app_context():
        inactive = User.query.filter_by(email="inactive@example.com").first()
        if not inactive:
            inactive = User(
                full_name="Inactive User",
                email="inactive@example.com",
                is_active=False
            )
            inactive.set_password("CorrectPassword123!")
            db.session.add(inactive)
            db.session.commit()

    response = client.post("/api/auth/login", json={
        "email": "inactive@example.com",
        "password": "CorrectPassword123!"
    })
    assert response.status_code == 401
    data = response.get_json()
    assert "deactivated" in data["message"].lower()


def test_missing_credentials_rejected(client):
    """Test blank login body returns error."""
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 400

