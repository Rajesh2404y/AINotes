"""
Integration tests for Summaries REST API Routes.
"""
import pytest
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary


@pytest.fixture
def test_user(app):
    """Creates a primary user and returns user.id."""
    with app.app_context():
        user = User.query.filter_by(email="summary_user@example.com").first()
        if not user:
            user = User(
                full_name="Summary Tester",
                email="summary_user@example.com",
                is_active=True
            )
            user.set_password("SecurePassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def other_user(app):
    """Creates a secondary user for cross-user permission tests."""
    with app.app_context():
        user = User.query.filter_by(email="other_summary_user@example.com").first()
        if not user:
            user = User(
                full_name="Other Tester",
                email="other_summary_user@example.com",
                is_active=True
            )
            user.set_password("SecurePassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def user_token(app, test_user):
    """JWT token for primary user."""
    with app.app_context():
        return create_access_token(identity=str(test_user))


@pytest.fixture
def other_token(app, other_user):
    """JWT token for secondary user."""
    with app.app_context():
        return create_access_token(identity=str(other_user))


@pytest.fixture
def processed_document(app, test_user):
    """Creates a processed document ready for summarization."""
    with app.app_context():
        doc = Document(
            user_id=test_user,
            original_filename="sample_chapter.txt",
            stored_filename="sample_chapter.txt",
            file_type="txt",
            file_size=1024,
            processing_status="COMPLETED",
            extraction_quality="HIGH",
            extracted_text=(
                "Operating systems coordinate hardware resources and offer an execution platform for applications. "
                "The kernel serves as the central control module managing CPU scheduling, memory allocation, and I/O devices. "
                "Virtual memory provides an illusion of vast contiguous memory using paging and segmentation tables. "
                "Process synchronization prevents race conditions when concurrent processes access shared memory. "
                "Deadlocks occur when processes hold resources while waiting for other held resources in a cyclic dependency."
            ),
            total_words=65
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id


def test_generate_summary_unauthorized(client):
    res = client.post("/api/summaries/generate", json={"document_id": 1})
    assert res.status_code == 401


def test_generate_summary_missing_doc_id(client, user_token):
    res = client.post(
        "/api/summaries/generate",
        json={"summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 400
    assert "Field 'document_id' is required" in res.get_json()["message"]


def test_generate_summary_invalid_type(client, user_token, processed_document):
    res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "invalid_mode"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 400
    assert "Invalid summary_type" in res.get_json()["message"]


def test_generate_summary_not_found(client, user_token):
    res = client.post(
        "/api/summaries/generate",
        json={"document_id": 999999, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 404


def test_generate_summary_cross_user_forbidden(client, other_token, processed_document):
    res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert res.status_code == 403


def test_generate_summary_success(client, user_token, processed_document):
    res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["summary_type"] == "medium"
    assert len(data["summary_text"]) > 0
    assert isinstance(data["key_takeaways"], list)
    assert isinstance(data["keywords"], list)
    assert "metadata" in data
    assert data["metadata"]["processing_duration"] >= 0


def test_list_summaries(client, user_token, processed_document):
    # First generate a summary
    client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "short"},
        headers={"Authorization": f"Bearer {user_token}"}
    )

    res = client.get("/api/summaries", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["summaries"]) >= 1
    assert "pagination" in data


def test_get_summary_by_id(client, user_token, processed_document):
    gen_res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "detailed"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    summary_id = gen_res.get_json()["data"]["id"]

    res = client.get(f"/api/summaries/{summary_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["id"] == summary_id
    assert data["summary_type"] == "detailed"
    assert "document" in data


def test_delete_summary(client, user_token, processed_document):
    gen_res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    summary_id = gen_res.get_json()["data"]["id"]

    del_res = client.delete(f"/api/summaries/{summary_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert del_res.status_code == 200

    # Ensure it is gone
    get_res = client.get(f"/api/summaries/{summary_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert get_res.status_code == 404


def test_export_summary_txt(client, user_token, processed_document):
    gen_res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    summary_id = gen_res.get_json()["data"]["id"]

    export_res = client.get(
        f"/api/summaries/{summary_id}/export?format=txt",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert export_res.status_code == 200
    assert "text/plain" in export_res.content_type
    assert b"STUDY NOTES" in export_res.data


def test_export_summary_pdf(client, user_token, processed_document):
    gen_res = client.post(
        "/api/summaries/generate",
        json={"document_id": processed_document, "summary_type": "medium"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    summary_id = gen_res.get_json()["data"]["id"]

    export_res = client.get(
        f"/api/summaries/{summary_id}/export?format=pdf",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert export_res.status_code == 200
    assert "application/pdf" in export_res.content_type
    assert export_res.data.startswith(b"%PDF")

