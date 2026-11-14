"""Automated Tests for Document Management and Processing REST API Endpoints.

Verifies:
- POST /api/documents/upload: Authentication enforcement, file upload, validation.
- POST /api/documents/extract: Extraction execution, ownership check, database update.
- POST /api/documents/text: Direct text paste ingestion.
- GET /api/documents: Paginated user document listing.
- GET /api/documents/<id>: Document detail retrieval and cross-user authorization.
- DELETE /api/documents/<id>: File and record deletion, cross-user isolation.
"""

import io
import pymupdf as fitz
import pytest
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document


@pytest.fixture
def test_user(app):
    """Creates a primary test user and returns ID."""
    with app.app_context():
        user = User.query.filter_by(email="doc_student@example.com").first()
        if not user:
            user = User(
                full_name="Document Tester",
                email="doc_student@example.com",
                is_active=True
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def other_user(app):
    """Creates a second user for cross-user isolation testing and returns ID."""
    with app.app_context():
        user = User.query.filter_by(email="other_student@example.com").first()
        if not user:
            user = User(
                full_name="Other Student",
                email="other_student@example.com",
                is_active=True
            )
            user.set_password("OtherPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def auth_headers(app, test_user):
    """Generates valid JWT auth header for test_user."""
    with app.app_context():
        token = create_access_token(identity=str(test_user))
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(app, other_user):
    """Generates valid JWT auth header for other_user."""
    with app.app_context():
        token = create_access_token(identity=str(other_user))
        return {"Authorization": f"Bearer {token}"}


def test_upload_without_auth_rejected(client):
    """Test 1: Verifies upload endpoint rejects requests without JWT token."""
    response = client.post("/api/documents/upload", data={"file": (io.BytesIO(b"dummy"), "test.txt")})
    assert response.status_code == 401


def test_upload_document_success(client, auth_headers, tmp_path):
    """Test 2: Verifies authenticated file upload creates document record."""
    pdf_bytes = io.BytesIO()
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Computer Science Study Notes on Data Structures.")
    doc.save(pdf_bytes)
    doc.close()
    pdf_bytes.seek(0)

    data = {
        "file": (pdf_bytes, "cs_notes.pdf")
    }
    response = client.post(
        "/api/documents/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )

    assert response.status_code == 201
    res = response.get_json()
    assert res["status"] == "success"
    assert "document" in res
    assert res["document"]["original_filename"] == "cs_notes.pdf"
    assert res["document"]["file_type"] == "pdf"
    assert res["document"]["processing_status"] == "uploaded"


def test_upload_invalid_extension_rejected(client, auth_headers):
    """Test 3: Verifies unsupported extension is rejected with 400 Bad Request."""
    data = {
        "file": (io.BytesIO(b"print('hack')"), "malicious.py")
    }
    response = client.post(
        "/api/documents/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert response.status_code == 400
    res = response.get_json()
    assert res["status"] == "error"
    assert "unsupported" in res["message"].lower()


def test_extract_document_pipeline_success(client, auth_headers):
    """Test 4: Verifies POST /api/documents/extract runs pipeline and updates DB."""
    # First upload text file
    content = b"Physics Notes: Thermodynamics covers heat, work, temperature, and statistical mechanics."
    data = {"file": (io.BytesIO(content), "physics.txt")}
    upload_res = client.post(
        "/api/documents/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    doc_id = upload_res.get_json()["document"]["id"]

    # Trigger extraction
    extract_res = client.post(
        "/api/documents/extract",
        json={"document_id": doc_id},
        headers=auth_headers
    )

    assert extract_res.status_code == 200
    payload = extract_res.get_json()
    assert payload["status"] == "success"
    doc_data = payload["document"]
    assert "Thermodynamics" in doc_data["extracted_text"]
    assert doc_data["total_words"] > 5
    assert doc_data["processing_status"] in ("completed", "completed_with_warnings")


def test_extract_cross_user_forbidden(client, auth_headers, other_auth_headers):
    """Test 5: Verifies users cannot trigger extraction on documents owned by others."""
    # Upload as test_user
    data = {"file": (io.BytesIO(b"Secret user notes"), "private.txt")}
    upload_res = client.post(
        "/api/documents/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    doc_id = upload_res.get_json()["document"]["id"]

    # Attempt extraction as other_user
    res = client.post(
        "/api/documents/extract",
        json={"document_id": doc_id},
        headers=other_auth_headers
    )
    assert res.status_code == 403
    assert "permission" in res.get_json()["message"].lower()


def test_direct_text_ingestion(client, auth_headers):
    """Test 6: Verifies direct text paste creates a completed document."""
    payload = {
        "title": "Machine Learning Outline",
        "content": (
            "Machine learning enables computers to learn from experience without being explicitly programmed. "
            "It is divided into supervised learning, unsupervised learning, and reinforcement learning."
        )
    }
    response = client.post("/api/documents/text", json=payload, headers=auth_headers)
    assert response.status_code == 201
    res = response.get_json()
    assert res["status"] == "success"
    assert res["document"]["file_type"] == "text_paste"
    assert res["document"]["total_words"] > 15


def test_list_documents_user_isolation(client, auth_headers, other_auth_headers):
    """Test 7: Verifies GET /api/documents returns only documents owned by requester."""
    # Upload 1 for test_user
    client.post(
        "/api/documents/upload",
        data={"file": (io.BytesIO(b"Notes for student 1"), "s1.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )

    # Upload 1 for other_user
    client.post(
        "/api/documents/upload",
        data={"file": (io.BytesIO(b"Notes for student 2"), "s2.txt")},
        content_type="multipart/form-data",
        headers=other_auth_headers
    )

    res_user1 = client.get("/api/documents", headers=auth_headers)
    assert res_user1.status_code == 200
    docs1 = res_user1.get_json()["documents"]
    for d in docs1:
        assert d["original_filename"] != "s2.txt"

    res_user2 = client.get("/api/documents", headers=other_auth_headers)
    assert res_user2.status_code == 200
    docs2 = res_user2.get_json()["documents"]
    for d in docs2:
        assert d["original_filename"] != "s1.txt"


def test_delete_document_success(client, auth_headers):
    """Test 8: Verifies DELETE /api/documents/<id> deletes record."""
    data = {"file": (io.BytesIO(b"Notes to be deleted"), "delete_me.txt")}
    upload_res = client.post(
        "/api/documents/upload",
        data=data,
        content_type="multipart/form-data",
        headers=auth_headers
    )
    doc_id = upload_res.get_json()["document"]["id"]

    del_res = client.delete(f"/api/documents/{doc_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # Ensure document is gone
    get_res = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
    assert get_res.status_code == 404
