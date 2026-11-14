"""Automated Tests for Health, Root API, Database Connectivity, and Error Handlers.
"""

import pytest


def test_app_initialization(app):
    """Test 1: Verifies Flask application initializes successfully with testing config."""
    assert app is not None
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_api_root_endpoint(client):
    """Test 2: Verifies GET /api/ returns HTTP 200 with metadata and service info."""
    response = client.get("/api/")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data["status"] == "success"
    assert "service" in data
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_health_endpoint_success(client):
    """Test 3: Verifies GET /api/health returns HTTP 200 with running status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert data["status"] == "success"
    assert data["message"] == "AI Notes Summarizer API is running"


def test_database_connectivity_verified(client):
    """Test 4: Verifies the real database ping confirms 'connected' state."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["database"] == "connected"


def test_invalid_endpoint_returns_404(client):
    """Test 5: Verifies requests to non-existent routes return standardized 404 JSON."""
    response = client.get("/api/non-existent-endpoint-xyz")
    assert response.status_code == 404
    data = response.get_json()
    assert data is not None
    assert data["status"] == "error"
    assert data["status_code"] == 404
    assert data["error"] == "Not Found"
    assert "message" in data


def test_invalid_http_method_returns_405(client):
    """Test 6: Verifies unsupported HTTP methods return standardized 405 JSON."""
    # /api/health only accepts GET
    response = client.post("/api/health", json={"test": "data"})
    assert response.status_code == 405
    data = response.get_json()
    assert data is not None
    assert data["status"] == "error"
    assert data["status_code"] == 405
    assert data["error"] == "Method Not Allowed"
    assert "message" in data


def test_error_response_format_consistency(client):
    """Test 7: Verifies error response JSON structure is uniform across error codes."""
    # Trigger 404
    res_404 = client.get("/api/unknown_route")
    data_404 = res_404.get_json()
    
    # Trigger 405
    res_405 = client.delete("/api/health")
    data_405 = res_405.get_json()
    
    expected_keys = {"status", "error", "message", "status_code"}
    assert set(data_404.keys()) == expected_keys
    assert set(data_405.keys()) == expected_keys
    assert data_404["status"] == "error"
    assert data_405["status"] == "error"

