"""Pytest Test Configuration and Fixtures.

Provides an isolated application instance using the TestingConfig profile (in-memory SQLite),
ensuring tests do not touch development or production databases.
"""

import sys
from pathlib import Path
import pytest

# Ensure root directory is on sys.path
TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
for p in [str(ROOT_DIR), str(BACKEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app import create_app
from backend.app.extensions import db


@pytest.fixture(scope="session")
def app():
    """Session-scoped Flask application instance configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Test client for dispatching HTTP requests against the application."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Test CLI runner for invoking click commands."""
    return app.test_cli_runner()

