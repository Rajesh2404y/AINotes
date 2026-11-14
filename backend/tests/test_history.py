"""
Automated Tests for History View and Delete Functionality across all 4 categories:
Documents, Summaries, Quiz Attempts, and Translations.
"""

import pytest
import uuid
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.translation import Translation


@pytest.fixture
def history_user(app):
    with app.app_context():
        unique_email = f"history_{uuid.uuid4().hex[:8]}@example.com"
        user = User(full_name="History User", email=unique_email, is_active=True)
        user.set_password("HistoryPass123!")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def other_user(app):
    with app.app_context():
        unique_email = f"other_{uuid.uuid4().hex[:8]}@example.com"
        user = User(full_name="Other User", email=unique_email, is_active=True)
        user.set_password("HistoryPass123!")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def user_token(app, history_user):
    with app.app_context():
        return create_access_token(identity=str(history_user))


@pytest.fixture
def other_token(app, other_user):
    with app.app_context():
        return create_access_token(identity=str(other_user))


@pytest.fixture
def seeded_history_items(app, history_user):
    with app.app_context():
        # 1. Document
        doc = Document(
            user_id=history_user,
            original_filename="cs_theory.pdf",
            stored_filename="cs_theory.pdf",
            file_type="pdf",
            file_size=2048,
            processing_status="completed",
            extracted_text="Automata theory explores abstract machines and formal languages.",
            total_words=45
        )
        db.session.add(doc)
        db.session.commit()

        # 2. Summary
        summary = Summary(
            user_id=history_user,
            document_id=doc.id,
            summary_type="medium",
            summary_text="Automata theory covers regular and context-free languages.",
            key_takeaways=["Automata are mathematical models", "Languages have strict grammars"],
            definitions=[{"term": "Automaton", "definition": "An abstract self-operating machine"}],
            keywords=["Automata", "Grammar", "Language"]
        )
        db.session.add(summary)
        db.session.commit()

        # 3. Quiz & Quiz Attempt
        quiz = Quiz(user_id=history_user, document_id=doc.id, quiz_type="mcq", total_questions=5)
        db.session.add(quiz)
        db.session.commit()

        attempt = QuizAttempt(
            user_id=history_user,
            quiz_id=quiz.id,
            score=4,
            total_questions=5,
            percentage=80.0
        )
        db.session.add(attempt)
        db.session.commit()

        # 4. Translation
        trans = Translation(
            user_id=history_user,
            summary_id=summary.id,
            source_language="en",
            target_language="fr",
            original_text=summary.summary_text,
            translated_text="La theorie des automates couvre les langages reguliers."
        )
        db.session.add(trans)
        db.session.commit()

        return {
            "doc_id": doc.id,
            "summary_id": summary.id,
            "quiz_id": quiz.id,
            "attempt_id": attempt.id,
            "trans_id": trans.id
        }


def test_history_feed_returns_all_categories(client, user_token, seeded_history_items):
    """Verifies that /api/dashboard/activities returns items across all 4 categories with valid raw_id."""
    res = client.get("/api/dashboard/activities", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    activities = res.get_json()["activities"]

    types_found = {a["type"] for a in activities}
    assert "document" in types_found
    assert "summary" in types_found
    assert "quiz" in types_found
    assert "translation" in types_found

    for item in activities:
        assert "raw_id" in item
        assert isinstance(item["raw_id"], int)


def test_view_document(client, user_token, seeded_history_items):
    """Verifies GET /api/documents/<id> retrieves full document metadata and text preview."""
    doc_id = seeded_history_items["doc_id"]
    res = client.get(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["document"]
    assert data["original_filename"] == "cs_theory.pdf"
    assert data["file_type"] == "pdf"
    assert "extracted_text" in data
    assert len(data["extracted_text"]) > 0


def test_view_summary(client, user_token, seeded_history_items):
    """Verifies GET /api/summaries/<id> retrieves summary text, takeaways, definitions, and keywords."""
    sum_id = seeded_history_items["summary_id"]
    res = client.get(f"/api/summaries/{sum_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["summary_type"] == "medium"
    assert len(data["key_takeaways"]) >= 1
    assert len(data["definitions"]) >= 1
    assert "Automata" in data["keywords"]


def test_view_quiz_attempt(client, user_token, seeded_history_items):
    """Verifies GET /api/quizzes/attempts/<id> retrieves attempt score, percentage, and details."""
    att_id = seeded_history_items["attempt_id"]
    res = client.get(f"/api/quizzes/attempts/{att_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["id"] == att_id
    assert data["score"] == 4
    assert data["total_questions"] == 5
    assert data["percentage"] == 80.0


def test_view_translation(client, user_token, seeded_history_items):
    """Verifies GET /api/translations/<id> retrieves source, target, original and translated text."""
    trans_id = seeded_history_items["trans_id"]
    res = client.get(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["source_language"] == "en"
    assert data["target_language"] == "fr"
    assert "original_text" in data
    assert "translated_text" in data


def test_delete_translation(client, user_token, other_token, seeded_history_items):
    """Verifies deleting a translation with ownership validation."""
    trans_id = seeded_history_items["trans_id"]

    # 1. Other user forbidden
    res_other = client.delete(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_other.status_code == 403

    # 2. Owner deletes
    res_owner = client.delete(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_owner.status_code == 200

    # 3. Verify deletion
    res_check = client.get(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.status_code == 404


def test_delete_quiz_attempt(client, user_token, other_token, seeded_history_items):
    """Verifies deleting a quiz attempt with ownership validation."""
    att_id = seeded_history_items["attempt_id"]

    # 1. Other user forbidden
    res_other = client.delete(f"/api/quizzes/attempts/{att_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_other.status_code == 403

    # 2. Owner deletes
    res_owner = client.delete(f"/api/quizzes/attempts/{att_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_owner.status_code == 200

    # 3. Verify deletion
    res_check = client.get(f"/api/quizzes/attempts/{att_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.status_code == 404


def test_delete_summary(client, user_token, other_token, seeded_history_items):
    """Verifies deleting a summary with ownership validation."""
    sum_id = seeded_history_items["summary_id"]

    res_other = client.delete(f"/api/summaries/{sum_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_other.status_code == 403

    res_owner = client.delete(f"/api/summaries/{sum_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_owner.status_code == 200

    res_check = client.get(f"/api/summaries/{sum_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.status_code == 404


def test_delete_document(client, user_token, other_token, seeded_history_items):
    """Verifies deleting a document with ownership validation."""
    doc_id = seeded_history_items["doc_id"]

    res_other = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_other.status_code == 403

    res_owner = client.delete(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_owner.status_code == 200

    res_check = client.get(f"/api/documents/{doc_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res_check.status_code == 404
