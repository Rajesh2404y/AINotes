"""Application Entry Point.

Starts the Flask WSGI application server with environment-based configuration.
Supports running from either the repository root or the backend/ subdirectory.
"""

import os
import sys
from pathlib import Path

# Ensure paths are configured for both root and backend directory execution
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
for p in [str(ROOT_DIR), str(BASE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.app import create_app
except ImportError:
    from app import create_app

env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = env == "development"
    print(f" * Starting AI Notes Summarizer Backend in '{env}' mode on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
