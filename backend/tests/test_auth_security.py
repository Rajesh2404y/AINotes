"""Automated Tests for Security Protections, Hashing, and Rate Limiting.
"""

import pytest
from werkzeug.security import check_password_hash
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.middleware.auth_guard import validate_resource_ownership
from backend.app.utils.rate_limiter import clear_rate_limits


def test_password_hashing_security(app):
    """Verifies passwords use salted hashes and never store plaintext."""
    with app.app_context():
        user = User(full_name="Crypt Test", email="crypto@example.com")
        raw_pw = "SuperSecret123!"
        user.set_password(raw_pw)

        # Hash must not contain plaintext password
        assert raw_pw not in user.password_hash
        assert user.password_hash.startswith("pbkdf2:sha256:")

        # Two hashes for same password must differ due to unique salts
        user2 = User(full_name="Crypt Test 2", email="crypto2@example.com")
        user2.set_password(raw_pw)
        assert user.password_hash != user2.password_hash

        # Verifications
        assert check_password_hash(user.password_hash, raw_pw) is True
        assert check_password_hash(user.password_hash, "wrong") is False


def test_rate_limiting_on_login(client, app):
    """Test excess login attempts trigger 429 Too Many Requests."""
    clear_rate_limits()
    app.enable_test_rate_limit = True
    try:
        responses = []
        for _ in range(17):
            res = client.post("/api/auth/login", json={
                "email": "rate_test@example.com",
                "password": "WrongPassword123!"
            })
            responses.append(res.status_code)

        assert 429 in responses
    finally:
        app.enable_test_rate_limit = False
        clear_rate_limits()


def test_resource_ownership_validation():
    """Test tenant isolation utility prevents cross-user access."""
    doc = Document(id=10, user_id=1, original_filename="test.pdf", file_type="pdf", extracted_text="test")

    # Access by owner (user 1)
    assert validate_resource_ownership(doc, user_id=1) is True

    # Access by attacker / different user (user 2)
    assert validate_resource_ownership(doc, user_id=2) is False

    # Non-existent resource
    assert validate_resource_ownership(None, user_id=1) is False
