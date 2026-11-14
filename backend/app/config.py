"""Application Configuration Module.

Provides configuration profiles for Development, Testing, and Production environments
with explicit validation of environment variables and fallback defaults.
"""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy.pool import StaticPool

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

# Load environment variables (.env in workspace root or backend dir)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def resolve_database_uri():
    """Resolves database URI, ensuring relative SQLite paths resolve cleanly to BASE_DIR."""
    uri = os.getenv("DATABASE_URL")
    if not uri or uri.strip() == "":
        return f"sqlite:///{BASE_DIR / 'ainotes.db'}"
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////") and not (":" in uri[10:]):
        # Handle relative SQLite path e.g. sqlite:///ainotes.db
        db_filename = uri.replace("sqlite:///", "")
        return f"sqlite:///{BASE_DIR / db_filename}"
    return uri


class Config:
    """Base configuration settings shared across all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-secret-key-32chars-minimum")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-super-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24))
    )
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    JWT_COOKIE_SECURE = False  # Set to True in production HTTPS
    JWT_COOKIE_CSRF_PROTECT = False

    # Uploads
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", os.getenv("MAX_CONTENT_LENGTH_MB", 20)))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = set(
        os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,txt,png,jpg,jpeg").lower().split(",")
    )

    # Logging Configuration
    LOG_FOLDER = BASE_DIR / "logs"
    LOG_FILE = BASE_DIR / "logs" / "app.log"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # AI Model Settings
    AI_DEVICE = os.getenv("AI_DEVICE", "cpu")
    MODEL_DEVICE = os.getenv("MODEL_DEVICE", "auto")
    MODEL_CACHE_DIR = BASE_DIR / os.getenv("MODEL_CACHE_DIR", "model_cache")
    SUMMARIZATION_MODEL = os.getenv("SUMMARIZATION_MODEL", "sshleifer/distilbart-cnn-12-6")
    STRUCTURED_EXTRACTION_MODEL = os.getenv("STRUCTURED_EXTRACTION_MODEL", "google/flan-t5-base")
    QUIZ_MODEL = os.getenv("QUIZ_MODEL", "google/flan-t5-base")
    TRANSLATION_ENGINE = os.getenv("TRANSLATION_ENGINE", "deep-translator")
    SUMMARIZATION_ENABLED = os.getenv("SUMMARIZATION_ENABLED", "true").lower() in ("true", "1", "yes")
    MAX_SUMMARY_INPUT_TOKENS = int(os.getenv("MAX_SUMMARY_INPUT_TOKENS", 900))
    SUMMARY_CHUNK_OVERLAP = int(os.getenv("SUMMARY_CHUNK_OVERLAP", 100))

    # Translation Settings
    TRANSLATION_ENABLED = os.getenv("TRANSLATION_ENABLED", "true").lower() in ("true", "1", "yes")
    TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "facebook/nllb-200-distilled-600M")
    TRANSLATION_DEVICE = os.getenv("TRANSLATION_DEVICE", "auto")
    TRANSLATION_CACHE_DIR = BASE_DIR / os.getenv("TRANSLATION_CACHE_DIR", "model_cache")
    TRANSLATION_MAX_INPUT_TOKENS = int(os.getenv("TRANSLATION_MAX_INPUT_TOKENS", 900))
    TRANSLATION_CHUNK_OVERLAP = int(os.getenv("TRANSLATION_CHUNK_OVERLAP", 80))
    TRANSLATION_BATCH_SIZE = int(os.getenv("TRANSLATION_BATCH_SIZE", 4))
    TRANSLATION_MAX_RETRIES = int(os.getenv("TRANSLATION_MAX_RETRIES", 2))

    # OCR Settings
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
    TESSERACT_LANGUAGES = os.getenv("TESSERACT_LANGUAGES", "eng+tam")

    # Phase 9: Personalized Recommendations & Learning Analytics
    WEAK_TOPIC_THRESHOLD = float(os.getenv("WEAK_TOPIC_THRESHOLD", 50.0))
    MODERATE_TOPIC_THRESHOLD = float(os.getenv("MODERATE_TOPIC_THRESHOLD", 70.0))
    STRONG_TOPIC_THRESHOLD = float(os.getenv("STRONG_TOPIC_THRESHOLD", 85.0))
    MIN_ATTEMPTS_FOR_CLASSIFICATION = int(os.getenv("MIN_ATTEMPTS_FOR_CLASSIFICATION", 3))

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    JWT_SECRET_KEY = "test-jwt-secret-key-for-testing-purposes-32-bytes"
    SECRET_KEY = "test-secret-key-for-testing-purposes-32-bytes"
    UPLOAD_FOLDER = BASE_DIR / "uploads" / "test"
    LOG_LEVEL = "WARNING"


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    JWT_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
