"""API Routes package.
"""

from backend.app.routes.health_routes import health_bp
from backend.app.routes.auth_routes import auth_bp
from backend.app.routes.dashboard_routes import dashboard_bp
from backend.app.routes.document_routes import document_bp
from backend.app.routes.summary_routes import summary_bp
from backend.app.routes.quiz_routes import quiz_bp
from backend.app.routes.translation_routes import translation_bp
from backend.app.routes.learning_routes import learning_bp
from backend.app.routes.recommendation_routes import recommendation_bp
from backend.app.routes.learning_path_routes import learning_path_bp
from backend.app.routes.history_routes import history_bp

__all__ = [
    "health_bp",
    "auth_bp",
    "dashboard_bp",
    "document_bp",
    "summary_bp",
    "quiz_bp",
    "translation_bp",
    "learning_bp",
    "recommendation_bp",
    "learning_path_bp",
    "history_bp",
]
