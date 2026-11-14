"""Automated Tests for Frontend Static Assets and HTML View Serving.

Verifies that the Flask application correctly serves all 13 educational SaaS
frontend pages and static CSS/JS assets.
"""

import pytest


def test_root_serves_landing_page(client):
    """Verifies GET / serves index.html with HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"AI Notes" in response.data
    assert b"Designed for Academic Excellence" in response.data


@pytest.mark.parametrize("page_name", [
    "index.html",
    "login.html",
    "register.html",
    "dashboard.html",
    "upload.html",
    "summary.html",
    "quiz-config.html",
    "quiz.html",
    "quiz-results.html",
    "translate.html",
    "history.html",
    "profile.html",
    "settings.html",
])
def test_all_13_html_pages_exist_and_serve(client, page_name):
    """Verifies every required Phase 4 HTML view loads with HTTP 200."""
    response = client.get(f"/{page_name}", follow_redirects=True)
    assert response.status_code == 200
    assert len(response.data) > 100


def test_static_css_assets_serve(client):
    """Verifies core CSS stylesheets serve with HTTP 200."""
    css_files = ["style.css", "components.css", "dashboard.css", "pages.css", "auth.css", "responsive.css"]
    for css in css_files:
        response = client.get(f"/css/{css}")
        assert response.status_code == 200
        assert len(response.data) > 0


def test_static_js_assets_serve(client):
    """Verifies core JavaScript modules serve with HTTP 200."""
    js_files = [
        "config.js", "theme.js", "api.js", "auth.js", "navigation.js",
        "dashboard.js", "upload.js", "summary.js", "quiz.js",
        "quiz-results.js", "translation.js", "history.js", "profile.js", "settings.js"
    ]
    for js in js_files:
        response = client.get(f"/js/{js}")
        assert response.status_code == 200
        assert len(response.data) > 0


def test_nonexistent_frontend_file_returns_404(client):
    """Verifies requests for missing files return HTTP 404."""
    response = client.get("/nonexistent_page_12345.html")
    assert response.status_code == 404
