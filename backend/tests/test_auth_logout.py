"""Automated Tests for Token Revocation and Logout Invalidation.
"""

import pytest
from backend.app.models.user import User
from backend.app.extensions import db


@pytest.fixture(autouse=True)
def setup_logout_user(app):
    """Seed dedicated user for logout tests."""
    with app.app_context():
        user = User.query.filter_by(email="logout_test@example.com").first()
        if not user:
            user = User(full_name="Logout User", email="logout_test@example.com")
            user.set_password("CorrectPassword123!")
            db.session.add(user)
            db.session.commit()


def test_logout_revokes_token(client):
    """Test user can log out and their token is recorded in blocklist."""
    # 1. Log in to acquire a fresh JWT
    login_res = client.post("/api/auth/login", json={
        "email": "logout_test@example.com",
        "password": "CorrectPassword123!"
    })
    token = login_res.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify token works before logout
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200

    # 3. Call logout endpoint
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.get_json()["status"] == "success"

    # 4. Attempt to use the same token after logout -> must be rejected with 401 Revoked
    post_logout_res = client.get("/api/auth/me", headers=headers)
    assert post_logout_res.status_code == 401
    assert "revoked" in post_logout_res.get_json()["message"].lower()


def test_logout_without_token_returns_401(client):
    """Test logout endpoint requires valid token."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 401
