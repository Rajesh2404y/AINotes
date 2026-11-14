"""
Integration tests for Translation REST API Routes.
"""
import pytest
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.models.translation import Translation


@pytest.fixture
def trans_user(app):
    with app.app_context():
        user = User.query.filter_by(email="trans_student@example.com").first()
        if not user:
            user = User(
                full_name="Translation Student",
                email="trans_student@example.com",
                is_active=True
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def other_trans_user(app):
    with app.app_context():
        user = User.query.filter_by(email="other_trans_student@example.com").first()
        if not user:
            user = User(
                full_name="Other Translation Student",
                email="other_trans_student@example.com",
                is_active=True
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def trans_token(app, trans_user):
    with app.app_context():
        return create_access_token(identity=str(trans_user))


@pytest.fixture
def other_trans_token(app, other_trans_user):
    with app.app_context():
        return create_access_token(identity=str(other_trans_user))


@pytest.fixture
def summary_fixture(app, trans_user):
    with app.app_context():
        doc = Document(
            user_id=trans_user,
            original_filename="ai_lesson.txt",
            stored_filename="ai_lesson.txt",
            file_type="txt",
            file_size=1024,
            processing_status="COMPLETED",
            extraction_quality="HIGH",
            extracted_text="Machine learning models learn patterns from empirical training datasets.",
            total_words=10
        )
        db.session.add(doc)
        db.session.flush()

        summary = Summary(
            user_id=trans_user,
            document_id=doc.id,
            summary_type="medium",
            summary_text="Machine learning enables computer software to iteratively learn from data representations.",
            key_takeaways=["Models learn from data."],
            definitions=[{"term": "Machine Learning", "definition": "Learning from data."}],
            keywords=["Machine Learning", "Data"]
        )
        db.session.add(summary)
        db.session.commit()
        return summary.id


def test_get_supported_languages(client):
    res = client.get("/api/translations/languages")
    assert res.status_code == 200
    languages = res.get_json()["data"]
    assert len(languages) == 9
    codes = {l["code"] for l in languages}
    assert "en" in codes and "ta" in codes and "hi" in codes


def test_generate_translation_unauthorized(client):
    res = client.post("/api/translations/generate", json={"summary_id": 1})
    assert res.status_code == 401


def test_generate_translation_missing_summary_id(client, trans_token):
    res = client.post(
        "/api/translations/generate",
        json={"target_language": "ta"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    assert res.status_code == 400


def test_generate_translation_not_found(client, trans_token):
    res = client.post(
        "/api/translations/generate",
        json={"summary_id": 999999, "target_language": "ta"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    assert res.status_code == 404


def test_generate_translation_cross_user_forbidden(client, other_trans_token, summary_fixture):
    res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "ta"},
        headers={"Authorization": f"Bearer {other_trans_token}"}
    )
    assert res.status_code == 403


def test_generate_translation_success(client, trans_token, summary_fixture):
    res = client.post(
        "/api/translations/generate",
        json={
            "summary_id": summary_fixture,
            "source_language": "en",
            "target_language": "ta"
        },
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["id"] is not None
    assert data["target_language"] == "ta"
    assert len(data["translated_text"]) > 0


def test_get_translation_by_id(client, trans_token, summary_fixture):
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "fr"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    trans_id = gen_res.get_json()["data"]["id"]

    res = client.get(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {trans_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["id"] == trans_id
    assert data["target_language"] == "fr"


def test_get_translation_cross_user_forbidden(client, other_trans_token, summary_fixture, trans_token):
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "de"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    trans_id = gen_res.get_json()["data"]["id"]

    res = client.get(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {other_trans_token}"})
    assert res.status_code == 403


def test_list_translations(client, trans_token, summary_fixture):
    # Ensure at least 1 translation exists
    client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "es"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )

    res = client.get("/api/translations/history", headers={"Authorization": f"Bearer {trans_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["translations"]) >= 1


def test_delete_translation(client, trans_token, summary_fixture, app):
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "hi"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    trans_id = gen_res.get_json()["data"]["id"]

    del_res = client.delete(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {trans_token}"})
    assert del_res.status_code == 200

    # Ensure translation is deleted
    get_res = client.get(f"/api/translations/{trans_id}", headers={"Authorization": f"Bearer {trans_token}"})
    assert get_res.status_code == 404

    # Ensure summary is preserved
    with app.app_context():
        summary = db.session.get(Summary, summary_fixture)
        assert summary is not None


def test_export_translation_txt(client, trans_token, summary_fixture):
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "ta"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    trans_id = gen_res.get_json()["data"]["id"]

    export_res = client.get(
        f"/api/translations/{trans_id}/export?format=txt",
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    assert export_res.status_code == 200
    assert "text/plain" in export_res.content_type
    assert b"TRANSLATED STUDY NOTES" in export_res.data


def test_export_translation_pdf(client, trans_token, summary_fixture):
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": summary_fixture, "target_language": "ta"},
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    trans_id = gen_res.get_json()["data"]["id"]

    export_res = client.get(
        f"/api/translations/{trans_id}/export?format=pdf",
        headers={"Authorization": f"Bearer {trans_token}"}
    )
    assert export_res.status_code == 200
    assert "application/pdf" in export_res.content_type
    assert export_res.data.startswith(b"%PDF")

