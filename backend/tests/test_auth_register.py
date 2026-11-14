"""Automated Tests for User Registration API and Validation Rules.
"""

import pytest
from backend.app.models.user import User


def test_valid_registration(client, app):
    """Test successful user registration with compliant payload."""
    payload = {
        "full_name": "Rajesh Y",
        "email": "rajesh@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["status"] == "success"
    assert data["message"] == "Registration successful"
    assert data["user"]["email"] == "rajesh@example.com"
    assert data["user"]["full_name"] == "Rajesh Y"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]

    # Verify user exists in database and password is encrypted
    with app.app_context():
        user = User.query.filter_by(email="rajesh@example.com").first()
        assert user is not None
        assert user.full_name == "Rajesh Y"
        assert user.password_hash != "SecurePassword123!"
        assert user.check_password("SecurePassword123!") is True


def test_duplicate_email_registration_rejected(client):
    """Test duplicate registration attempts are rejected with 400 error."""
    payload = {
        "full_name": "Rajesh Y",
        "email": "rajesh@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }
    # Second registration with same email
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "error"
    assert "already exists" in data["errors"]["email"].lower()


def test_invalid_email_format_rejected(client):
    """Test invalid email formats are rejected."""
    payload = {
        "full_name": "Test User",
        "email": "invalid-email-no-at-sign",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "email" in data["errors"]


def test_missing_fields_rejected(client):
    """Test empty/missing payload attributes are caught."""
    response = client.post("/api/auth/register", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "full_name" in data["errors"]
    assert "email" in data["errors"]
    assert "password" in data["errors"]


def test_weak_password_rejected(client):
    """Test passwords failing security complexity rules are rejected."""
    # Too short
    res_short = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com",
        "password": "Sh1!", "confirm_password": "Sh1!"
    })
    assert res_short.status_code == 400
    assert "at least 8 characters" in res_short.get_json()["errors"]["password"]

    # Missing uppercase
    res_no_upper = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com",
        "password": "securepassword123!", "confirm_password": "securepassword123!"
    })
    assert res_no_upper.status_code == 400
    assert "uppercase" in res_no_upper.get_json()["errors"]["password"]

    # Missing number
    res_no_num = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com",
        "password": "SecurePassword!", "confirm_password": "SecurePassword!"
    })
    assert res_no_num.status_code == 400
    assert "digit" in res_no_num.get_json()["errors"]["password"]

    # Missing special character
    res_no_special = client.post("/api/auth/register", json={
        "full_name": "Alice", "email": "alice@example.com",
        "password": "SecurePassword123", "confirm_password": "SecurePassword123"
    })
    assert res_no_special.status_code == 400
    assert "special character" in res_no_special.get_json()["errors"]["password"]


def test_password_mismatch_rejected(client):
    """Test non-matching confirm_password triggers error."""
    payload = {
        "full_name": "Bob",
        "email": "bob@example.com",
        "password": "SecurePassword123!",
        "confirm_password": "DifferentPassword123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "do not match" in data["errors"]["confirm_password"]


def test_whitespace_only_values_rejected(client):
    """Test strings consisting purely of whitespace are rejected as empty."""
    payload = {
        "full_name": "   ",
        "email": "   ",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "full_name" in data["errors"]
    assert "email" in data["errors"]

