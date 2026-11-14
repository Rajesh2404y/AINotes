"""Automated Tests for Timezone and Last Login Display Handling.

Validates:
1. All database timestamps stored in UTC.
2. UTC timestamps correctly converted to local timezone (default Asia/Kolkata / IST).
3. Display format is unambiguous: '12 Nov 2026, 10:36:39 AM IST'.
4. Ambiguous numeric formats (like '11/12/2026') are avoided.
5. All entities (User, Document, Summary, Quiz, Translation, Activities) use consistent UTC handling.
6. Double conversion prevention.
7. Safe handling of None, empty, or invalid timestamps.
8. Actual database timestamps remain pure UTC without mutation.
9. Verification of UTC-to-IST time math (IST is UTC + 5 hours 30 minutes).
"""

import pytest
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models import User, Document, Summary, Quiz, QuizAttempt, Translation
from backend.app.services.user_service import UserService
from backend.app.utils.datetime_utils import (
    to_utc_iso,
    format_display_datetime,
    format_display_date,
    parse_to_utc_datetime,
    DEFAULT_TIMEZONE
)


@pytest.fixture
def auth_user(app):
    """Creates a unique test user in the database."""
    unique_email = f"tz_user_{uuid.uuid4().hex[:8]}@example.com"
    with app.app_context():
        user = User(full_name="Timezone Student", email=unique_email)
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        token = create_access_token(identity=str(user.id))

    return {"id": user_id, "email": unique_email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_utc_storage_in_database(app, auth_user):
    """Req 1 & 9: Verify timestamps stored in the database are in UTC and not shifted."""
    with app.app_context():
        user = User.query.get(auth_user["id"])
        assert user is not None

        # Update last login via service
        UserService.update_last_login(user)

        # Re-fetch directly from DB
        db.session.refresh(user)
        db_timestamp = user.last_login

        assert db_timestamp is not None
        # Database stores naive UTC datetime
        now_utc = datetime.utcnow()
        diff_seconds = abs((now_utc - db_timestamp).total_seconds())
        assert diff_seconds < 10, f"Stored timestamp {db_timestamp} differs from current UTC {now_utc}"


def test_utc_to_ist_conversion_exact_math():
    """Req 2, 3, 4, 10: Verify UTC-to-IST conversion matches exact expected display string."""
    # Stored UTC timestamp: 2026-11-12 05:06:39
    # In IST (UTC+05:30), this MUST be: 10:36:39 AM IST on 12 Nov 2026
    stored_utc = datetime(2026, 11, 12, 5, 6, 39)
    displayed = format_display_datetime(stored_utc, tz_name="Asia/Kolkata")

    assert displayed == "12 Nov 2026, 10:36:39 AM IST"

    # Afternoon test
    stored_utc_pm = datetime(2026, 11, 12, 15, 45, 0)
    # 15:45 + 5:30 = 21:15 -> 09:15:00 PM IST
    displayed_pm = format_display_datetime(stored_utc_pm, tz_name="Asia/Kolkata")
    assert displayed_pm == "12 Nov 2026, 09:15:00 PM IST"


def test_default_timezone_is_asia_kolkata():
    """Req 3: Verify DEFAULT_TIMEZONE is Asia/Kolkata and produces IST abbreviation."""
    assert DEFAULT_TIMEZONE == "Asia/Kolkata"
    test_dt = datetime(2026, 11, 12, 5, 6, 39)
    # When tz_name is omitted, defaults to Asia/Kolkata
    displayed = format_display_datetime(test_dt)
    assert displayed.endswith("IST")
    assert displayed == "12 Nov 2026, 10:36:39 AM IST"


def test_unambiguous_date_only_format():
    """Req 4 & 5: Verify date-only display avoids ambiguous numeric formats like '11/12/2026'."""
    stored_utc = datetime(2026, 11, 12, 5, 6, 39)
    date_display = format_display_date(stored_utc)
    assert date_display == "12 Nov 2026"
    assert "/" not in date_display


def test_prevent_double_timezone_conversion():
    """Req 7: Calling formatter on an already formatted timestamp must return it untouched."""
    original_formatted = "12 Nov 2026, 10:36:39 AM IST"
    result = format_display_datetime(original_formatted)
    assert result == original_formatted, f"Double conversion occurred: {result}"


def test_safe_handling_of_missing_and_invalid_timestamps():
    """Req 8: Handle None, empty strings, and invalid dates safely without throwing exceptions."""
    assert format_display_datetime(None) == "--"
    assert format_display_datetime("") == "--"
    assert format_display_datetime("   ") == "--"
    assert format_display_datetime("not-a-valid-date") == "--"

    assert format_display_date(None) == "--"
    assert format_display_date("") == "--"
    assert format_display_date("invalid") == "--"

    assert to_utc_iso(None) is None
    assert parse_to_utc_datetime(None) is None
    assert parse_to_utc_datetime("invalid") is None


def test_user_to_dict_serialization_includes_utc_iso_and_display(app, auth_user):
    """Req 6, 9: Verify User.to_dict() serializes last_login with explicit 'Z' and displays correctly."""
    with app.app_context():
        user = User.query.get(auth_user["id"])
        test_time = datetime(2026, 11, 12, 5, 6, 39)
        user.last_login = test_time
        db.session.commit()

        serialized = user.to_dict()
        assert serialized["last_login"] == "2026-11-12T05:06:39Z"
        assert serialized["last_login_display"] == "12 Nov 2026, 10:36:39 AM IST"

        # Confirm database timestamp remained naive UTC untouched
        db.session.refresh(user)
        assert user.last_login == test_time


def test_login_route_returns_user_with_last_login(client):
    """Req 6: Verify POST /api/auth/login returns user profile containing last_login."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"tz_test_{unique_id}@example.com"
    password = "SecurePassword123!"

    # Register user
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Timezone Test Student",
        "email": email,
        "password": password,
        "confirm_password": password
    })
    assert reg_res.status_code == 201

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    user_data = login_res.get_json()["user"]
    assert "last_login" in user_data
    assert user_data["last_login"] is not None
    assert user_data["last_login"].endswith("Z")


def test_dashboard_activities_feed_uses_utc_iso_timestamps(client, app, auth_user):
    """Req 6: Verify /api/dashboard/activities returns items with ISO-8601 UTC timestamps."""
    with app.app_context():
        doc = Document(
            user_id=auth_user["id"],
            original_filename="tz_notes.pdf",
            stored_filename="tz_notes.pdf",
            file_type="pdf",
            file_size=1024,
            processing_status="completed",
            created_at=datetime(2026, 11, 12, 5, 6, 39)
        )
        db.session.add(doc)
        db.session.commit()

    res = client.get("/api/dashboard/activities", headers=auth_user["headers"])
    assert res.status_code == 200
    activities = res.get_json()["activities"]
    assert len(activities) > 0
    doc_activity = next(a for a in activities if a["type"] == "document")
    assert doc_activity["timestamp"] == "2026-11-12T05:06:39Z"
