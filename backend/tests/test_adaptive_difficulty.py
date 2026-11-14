"""Unit tests for Adaptive Difficulty Recommendation Service.
"""

from backend.app.ai.adaptive_difficulty_service import adaptive_difficulty_service
from backend.app.extensions import db
from backend.app.models.user import User


def test_adaptive_difficulty_for_empty_profile(app):
    """Verifies default easy baseline recommendation for a new student."""
    with app.app_context():
        user = User(full_name="Diff Student", email="diff_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        rec = adaptive_difficulty_service.recommend_difficulty(user.id)
        assert rec["recommended_difficulty"] == "easy"
        assert rec["confidence"] == "low"
        assert "Baseline" in rec["reason"]

