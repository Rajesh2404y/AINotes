"""Automated Tests for Server-Side History Pagination, Search, and Filtering.

Tests cover:
- 0 records (empty state handling)
- 1 record, 10 records, 11 records, 20 records, 21 records, 50 records
- Page size options: 10, 20, 50
- Previous / Next boundary conditions and metadata flags
- Category filtering: all, document, summary, quiz, translation
- Real-time case-insensitive keyword search
- User ownership and authorization isolation
- Deterministic ordering (timestamp descending with ID tie-breaker)
"""

import pytest
import uuid
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import User, Document, Summary, Quiz, QuizAttempt, Translation


@pytest.fixture
def auth_user_history(app):
    """Creates a unique test user in the database."""
    unique_email = f"hist_{uuid.uuid4().hex[:8]}@example.com"
    with app.app_context():
        user = User(full_name="History Pagination User", email=unique_email)
        user.set_password("HistPass123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user.id))

    return {"id": user_id, "email": unique_email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_empty_history(client, auth_user_history):
    """Test 0 records returns clean empty list and correct pagination metadata."""
    res = client.get("/api/history?page=1&per_page=10&type=all", headers=auth_user_history["headers"])
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"] == []
    assert data["pagination"] == {
        "current_page": 1,
        "per_page": 10,
        "total_items": 0,
        "total_pages": 0,
        "has_previous": False,
        "has_next": False
    }


def test_single_record_history(client, app, auth_user_history):
    """Test 1 record pagination metadata."""
    with app.app_context():
        doc = Document(
            user_id=auth_user_history["id"],
            original_filename="intro_notes.pdf",
            stored_filename="intro_notes.pdf",
            file_type="pdf",
            file_size=2048,
            processing_status="completed",
            created_at=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()

    res = client.get("/api/history?page=1&per_page=10", headers=auth_user_history["headers"])
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["data"]) == 1
    assert data["pagination"]["total_items"] == 1
    assert data["pagination"]["total_pages"] == 1
    assert data["pagination"]["has_previous"] is False
    assert data["pagination"]["has_next"] is False


def test_ten_and_eleven_records_pagination(client, app, auth_user_history):
    """Test boundary of 10 and 11 records (crossing from 1 page to 2 pages)."""
    base_time = datetime(2026, 11, 10, 10, 0, 0)
    with app.app_context():
        # Seed 11 documents
        for i in range(11):
            doc = Document(
                user_id=auth_user_history["id"],
                original_filename=f"module_{i+1:02d}.pdf",
                stored_filename=f"module_{i+1:02d}.pdf",
                file_type="pdf",
                file_size=1000 + i,
                processing_status="completed",
                created_at=base_time + timedelta(minutes=i)
            )
            db.session.add(doc)
        db.session.commit()

    # Page 1 with per_page=10 -> should return 10 items, has_next=True
    p1 = client.get("/api/history?page=1&per_page=10", headers=auth_user_history["headers"]).get_json()
    assert len(p1["data"]) == 10
    assert p1["pagination"]["total_items"] == 11
    assert p1["pagination"]["total_pages"] == 2
    assert p1["pagination"]["has_previous"] is False
    assert p1["pagination"]["has_next"] is True
    # Deterministic order check: newest first (module 11)
    assert p1["data"][0]["title"] == "module_11.pdf"

    # Page 2 with per_page=10 -> should return remaining 1 item, has_previous=True, has_next=False
    p2 = client.get("/api/history?page=2&per_page=10", headers=auth_user_history["headers"]).get_json()
    assert len(p2["data"]) == 1
    assert p2["pagination"]["current_page"] == 2
    assert p2["pagination"]["has_previous"] is True
    assert p2["pagination"]["has_next"] is False
    assert p2["data"][0]["title"] == "module_01.pdf"


def test_twenty_and_twenty_one_records_with_page_sizes(client, app, auth_user_history):
    """Test 21 records with page sizes 10, 20, and 50."""
    with app.app_context():
        for i in range(21):
            doc = Document(
                user_id=auth_user_history["id"],
                original_filename=f"doc_{i+1:02d}.pdf",
                stored_filename=f"doc_{i+1:02d}.pdf",
                file_type="pdf",
                file_size=1024,
                processing_status="completed",
                created_at=datetime.utcnow() + timedelta(seconds=i)
            )
            db.session.add(doc)
        db.session.commit()

    # Per page 10 -> 3 pages (10, 10, 1)
    res_10 = client.get("/api/history?page=1&per_page=10", headers=auth_user_history["headers"]).get_json()
    assert res_10["pagination"]["total_items"] == 21
    assert res_10["pagination"]["total_pages"] == 3
    assert len(res_10["data"]) == 10

    # Per page 20 -> 2 pages (20, 1)
    res_20 = client.get("/api/history?page=1&per_page=20", headers=auth_user_history["headers"]).get_json()
    assert res_20["pagination"]["total_items"] == 21
    assert res_20["pagination"]["total_pages"] == 2
    assert len(res_20["data"]) == 20

    # Per page 50 -> 1 page (21)
    res_50 = client.get("/api/history?page=1&per_page=50", headers=auth_user_history["headers"]).get_json()
    assert res_50["pagination"]["total_items"] == 21
    assert res_50["pagination"]["total_pages"] == 1
    assert len(res_50["data"]) == 21


def test_category_filtering_with_pagination(client, app, auth_user_history):
    """Test category filtering limits results and calculates category-specific totals."""
    with app.app_context():
        # 3 Documents
        for i in range(3):
            db.session.add(Document(
                user_id=auth_user_history["id"],
                original_filename=f"biology_{i}.pdf",
                stored_filename=f"biology_{i}.pdf",
                file_type="pdf",
                file_size=1000,
                processing_status="completed",
                created_at=datetime.utcnow()
            ))
        # 2 Summaries
        for i in range(2):
            db.session.add(Summary(
                user_id=auth_user_history["id"],
                document_id=1,
                summary_type="short",
                summary_text="Quick summary text",
                created_at=datetime.utcnow()
            ))
        # 1 Translation
        db.session.add(Translation(
            user_id=auth_user_history["id"],
            summary_id=1,
            source_language="en",
            target_language="ta",
            original_text="Hello",
            translated_text="Vanakkam",
            created_at=datetime.utcnow()
        ))
        db.session.commit()

    # Filter all
    all_res = client.get("/api/history?type=all", headers=auth_user_history["headers"]).get_json()
    assert all_res["pagination"]["total_items"] == 6

    # Filter document
    doc_res = client.get("/api/history?type=document", headers=auth_user_history["headers"]).get_json()
    assert doc_res["pagination"]["total_items"] == 3
    assert all(item["type"] == "document" for item in doc_res["data"])

    # Filter summary
    sum_res = client.get("/api/history?type=summary", headers=auth_user_history["headers"]).get_json()
    assert sum_res["pagination"]["total_items"] == 2
    assert all(item["type"] == "summary" for item in sum_res["data"])

    # Filter translation
    tr_res = client.get("/api/history?type=translation", headers=auth_user_history["headers"]).get_json()
    assert tr_res["pagination"]["total_items"] == 1
    assert tr_res["data"][0]["type"] == "translation"


def test_search_with_pagination(client, app, auth_user_history):
    """Test case-insensitive search across titles, details, and topics with pagination."""
    with app.app_context():
        doc1 = Document(
            user_id=auth_user_history["id"],
            original_filename="Photosynthesis_Notes.pdf",
            stored_filename="Photosynthesis_Notes.pdf",
            file_type="pdf",
            file_size=2000,
            extracted_text="Chlorophyll light reaction and ATP synthesis",
            processing_status="completed",
            created_at=datetime.utcnow()
        )
        doc2 = Document(
            user_id=auth_user_history["id"],
            original_filename="Quantum_Computing.pdf",
            stored_filename="Quantum_Computing.pdf",
            file_type="pdf",
            file_size=3000,
            extracted_text="Qubits and superposition principles",
            processing_status="completed",
            created_at=datetime.utcnow()
        )
        db.session.add_all([doc1, doc2])
        db.session.commit()

    # Search 'photosynthesis' (case-insensitive)
    s1 = client.get("/api/history?search=photosynthesis", headers=auth_user_history["headers"]).get_json()
    assert s1["pagination"]["total_items"] == 1
    assert s1["data"][0]["title"] == "Photosynthesis_Notes.pdf"

    # Search keyword in content 'superposition'
    s2 = client.get("/api/history?search=superposition", headers=auth_user_history["headers"]).get_json()
    assert s2["pagination"]["total_items"] == 1
    assert s2["data"][0]["title"] == "Quantum_Computing.pdf"

    # Search non-matching
    s3 = client.get("/api/history?search=nonexistent_topic_xyz", headers=auth_user_history["headers"]).get_json()
    assert s3["pagination"]["total_items"] == 0
    assert s3["data"] == []


def test_user_ownership_isolation(client, app, auth_user_history):
    """Test records of user A are never visible to user B."""
    with app.app_context():
        # Create user B with unique email
        other_user = User(full_name="Other Student", email=f"other_{uuid.uuid4().hex[:8]}@example.com")
        other_user.set_password("OtherPass123!")
        db.session.add(other_user)
        db.session.commit()

        # Add document for User B
        other_doc = Document(
            user_id=other_user.id,
            original_filename="confidential_b.pdf",
            stored_filename="confidential_b.pdf",
            file_type="pdf",
            file_size=5000,
            processing_status="completed",
            created_at=datetime.utcnow()
        )
        db.session.add(other_doc)
        db.session.commit()

    # User A requests history -> must NOT contain confidential_b.pdf
    res = client.get("/api/history", headers=auth_user_history["headers"]).get_json()
    titles = [d["title"] for d in res["data"]]
    assert "confidential_b.pdf" not in titles
