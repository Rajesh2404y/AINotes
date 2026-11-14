# Production-ready Dockerfile for AI Notes Summarizer Backend
FROM python:3.11-slim

# Set environment flags
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Install system dependencies (build tools, libmupdf support, sqlite)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-all \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application source
COPY backend /app/backend
COPY frontend /app/frontend
COPY .env.example /app/.env

# Create non-root user for security
RUN useradd -m appuser && \
    mkdir -p /app/backend/uploads /app/backend/logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Run with Gunicorn WSGI server in production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "backend.run:app"]

