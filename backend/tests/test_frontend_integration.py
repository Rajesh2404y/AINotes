"""Integration tests verifying Frontend API Configuration and Summarization Endpoints.
"""

import json
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.user import User


def test_cors_configuration(client):
    """Verifies that CORS headers are present on API responses."""
    res = client.get("/api/health", headers={"Origin": "http://localhost:5000"})
    assert res.status_code == 200
    assert "Access-Control-Allow-Origin" in res.headers


def test_document_list_and_summary_generation_integration(app, client):
    """Verifies document list retrieval and AI summary generation with takeaways, definitions, keywords."""
    with app.app_context():
        user = User(
            full_name="Frontend Test Student",
            email="frontend_integration@example.com",
            is_active=True,
        )
        user.set_password("StudentPassword123!")
        db.session.add(user)
        db.session.commit()

        token = create_access_token(identity=str(user.id))
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Ingest sample document text
        text_content = (
            "An operating system acts as an intermediary between the user of a computer and the computer hardware. "
            "Operating systems manage hardware resources such as CPU scheduling, virtual memory, file systems, and input/output devices. "
            "Key concepts include process synchronization, deadlock prevention, paging, and kernel architectures."
        )
        ingest_res = client.post(
            "/api/documents/text",
            json={"title": "Operating Systems Architecture", "content": text_content},
            headers=auth_headers,
        )
        assert ingest_res.status_code == 201
        doc_data = ingest_res.get_json()["document"]
        doc_id = doc_data["id"]

        # 2. Test Document List API with limit / per_page
        list_res = client.get("/api/documents?limit=10", headers=auth_headers)
        assert list_res.status_code == 200
        docs = list_res.get_json()["documents"]
        assert len(docs) >= 1
        assert any(d["id"] == doc_id for d in docs)

        list_res_per_page = client.get("/api/documents?per_page=50", headers=auth_headers)
        assert list_res_per_page.status_code == 200
        assert len(list_res_per_page.get_json()["documents"]) >= 1

        # 3. Test Summary Generation API with document_id and summary_type
        sum_res = client.post(
            "/api/summaries/generate",
            json={"document_id": doc_id, "summary_type": "medium"},
            headers=auth_headers,
        )
        assert sum_res.status_code == 201
        sum_body = sum_res.get_json()
        assert sum_body["status"] == "success"
        summary = sum_body["data"]

        # 4. Verify all components required by frontend appear in the response
        assert summary["document_id"] == doc_id
        assert summary["summary_type"] == "medium"
        assert len(summary["summary_text"]) > 20
        assert isinstance(summary.get("key_takeaways"), list)
        assert len(summary["key_takeaways"]) >= 1
        assert isinstance(summary.get("definitions"), list)
        assert isinstance(summary.get("keywords"), list)
        assert len(summary["keywords"]) >= 1

        # 5. Verify Document retrieval endpoint
        single_doc_res = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
        assert single_doc_res.status_code == 200
        assert "document" in single_doc_res.get_json()


def test_summary_generation_validation_and_auth_errors(client):
    """Verifies error handling for missing authentication, missing document_id, and invalid summary_type."""
    # 1. Missing authentication header -> 401
    unauth_res = client.post("/api/summaries/generate", json={"document_id": 1, "summary_type": "medium"})
    assert unauth_res.status_code == 401

    # 2. With auth but missing document_id -> 400
    from flask_jwt_extended import create_access_token
    token = create_access_token(identity="1")
    headers = {"Authorization": f"Bearer {token}"}

    no_doc_res = client.post("/api/summaries/generate", json={"summary_type": "medium"}, headers=headers)
    assert no_doc_res.status_code == 400
    assert "document_id" in no_doc_res.get_json()["message"]

    # 3. Invalid summary_type -> 400
    invalid_type_res = client.post(
        "/api/summaries/generate",
        json={"document_id": 1, "summary_type": "invalid_mode"},
        headers=headers,
    )
    assert invalid_type_res.status_code == 400
    assert "Invalid summary_type" in invalid_type_res.get_json()["message"]

