"""Document Management and Processing API Routes.

Implements authenticated endpoints for:
- POST /api/documents/upload: Secure multipart file upload & validation
- POST /api/documents/extract: Text extraction, OCR, cleaning & quality scoring
- POST /api/documents/text: Direct text paste ingestion
- GET /api/documents: Paginated user document listing
- GET /api/documents/<int:doc_id>: Full document details and extracted text
- DELETE /api/documents/<int:doc_id>: Secure document and filesystem cleanup
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, current_user

from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.services.file_validation_service import (
    FileValidationService,
    FileValidationError,
)
from backend.app.services.document_processing_service import document_processor
from backend.app.services.text_cleaning_service import clean_text
from backend.app.services.text_quality_service import assess_text_quality

logger = logging.getLogger("ainotes.document_routes")

document_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


def _get_user_upload_dir(user_id: int) -> Path:
    """Returns and ensures the isolated storage folder for a user's uploaded documents."""
    upload_base = Path(current_app.config["UPLOAD_FOLDER"])
    user_dir = upload_base / f"user_{user_id}"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


# ============================================================================
# 1. UPLOAD DOCUMENT (POST /api/documents/upload)
# ============================================================================
@document_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    """Accepts multipart/form-data upload, validates file integrity, and saves to storage."""
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": "Missing required 'file' field in multipart form-data.",
            "status_code": 400
        }), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": "No file was selected for upload.",
            "status_code": 400
        }), 400

    max_mb = current_app.config.get("MAX_UPLOAD_SIZE_MB", 20)
    allowed_exts = current_app.config.get("ALLOWED_EXTENSIONS")
    validator = FileValidationService(max_size_mb=max_mb, allowed_extensions=allowed_exts)

    try:
        is_valid, meta = validator.validate_file(uploaded_file)
    except FileValidationError as fve:
        logger.warning("File validation rejected file '%s': %s", uploaded_file.filename, fve.message)
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "code": fve.code,
            "message": fve.message,
            "status_code": fve.status_code
        }), fve.status_code
    except Exception as exc:
        logger.error("Unexpected error during file validation: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": f"Could not validate uploaded file: {str(exc)}",
            "status_code": 400
        }), 400

    user_dir = _get_user_upload_dir(current_user.id)
    stored_path = user_dir / meta["stored_filename"]

    try:
        uploaded_file.save(str(stored_path))
    except Exception as exc:
        logger.error("Failed to save file '%s' to storage: %s", stored_path, exc)
        return jsonify({
            "status": "error",
            "error": "Storage Error",
            "message": "Failed to persist uploaded document to server disk.",
            "status_code": 500
        }), 500

    # Create Document record
    try:
        doc = Document(
            user_id=current_user.id,
            original_filename=meta["original_filename"],
            stored_filename=meta["stored_filename"],
            file_type=meta["file_type"],
            file_size=meta["file_size"],
            extracted_text="",
            cleaned_text="",
            processing_status="uploaded",
            extraction_quality="PENDING",
            total_pages=1,
            total_words=0,
            total_characters=0,
            ocr_used=False,
            extraction_metadata={"sha256": meta["sha256"], "mime_type": meta["mime_type"]},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        # Clean up stored file if DB commit fails
        if stored_path.exists():
            stored_path.unlink()
        logger.error("Database error saving document record: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Database Error",
            "message": "Could not record document in database.",
            "status_code": 500
        }), 500

    logger.info("Document #%d uploaded by user #%d: '%s'", doc.id, current_user.id, doc.original_filename)

    return jsonify({
        "status": "success",
        "message": "File uploaded and validated successfully. Ready for extraction.",
        "document": doc.to_dict(include_text=False)
    }), 201


# ============================================================================
# 2. EXTRACT DOCUMENT TEXT (POST /api/documents/extract)
# ============================================================================
@document_bp.route("/extract", methods=["POST"])
@jwt_required()
def extract_document():
    """Runs the unified extraction, OCR, cleaning, and quality pipeline on a stored document."""
    data = request.get_json(silent=True) or {}
    document_id = data.get("document_id")

    if not document_id:
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": "Field 'document_id' is required.",
            "status_code": 400
        }), 400

    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Document #{document_id} was not found.",
            "status_code": 404
        }), 404

    # Authorization Guard: Verify Ownership
    if doc.user_id != current_user.id:
        logger.warning(
            "Unauthorized extraction attempt: User #%d tried to access document #%d owned by User #%d",
            current_user.id, doc.id, doc.user_id
        )
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to access or extract this document.",
            "status_code": 403
        }), 403

    user_dir = _get_user_upload_dir(doc.user_id)
    stored_path = user_dir / (doc.stored_filename or "")

    if not stored_path.exists() and doc.file_type != "text_paste":
        doc.processing_status = "failed"
        doc.extraction_quality = "FAILED"
        db.session.commit()
        return jsonify({
            "status": "error",
            "error": "File Missing",
            "message": "Underlying storage file could not be located on disk.",
            "status_code": 404
        }), 404

    # Update state to processing
    doc.processing_status = "processing"
    db.session.commit()

    # Execute Document Processor
    extraction_res = document_processor.process_document(
        file_path=str(stored_path),
        file_type=doc.file_type,
        original_filename=doc.original_filename
    )

    if not extraction_res.get("success"):
        doc.processing_status = "failed"
        doc.extraction_quality = "FAILED"
        doc.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "status": "error",
            "error": "Extraction Failed",
            "message": extraction_res.get("error", "Failed to extract readable content from document."),
            "warnings": extraction_res.get("warnings", []),
            "document": doc.to_dict(include_text=False),
            "status_code": 422
        }), 422

    # Save extraction results to database
    try:
        doc.extracted_text = extraction_res["raw_text"]
        doc.cleaned_text = extraction_res["cleaned_text"]
        doc.total_pages = extraction_res["total_pages"]
        doc.total_words = extraction_res["total_words"]
        doc.total_characters = extraction_res["total_characters"]
        doc.ocr_used = extraction_res["ocr_used"]
        doc.extraction_quality = extraction_res["extraction_quality"]
        doc.processing_status = extraction_res["processing_status"]

        meta = doc.extraction_metadata or {}
        meta.update(extraction_res.get("metadata", {}))
        meta["ocr_confidence"] = extraction_res.get("ocr_confidence", 0.0)
        meta["warnings"] = extraction_res.get("warnings", [])
        doc.extraction_metadata = meta
        doc.updated_at = datetime.utcnow()

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to commit extracted text to database: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Database Error",
            "message": "Failed to store extracted document content.",
            "status_code": 500
        }), 500

    logger.info(
        "Document #%d extracted successfully: %d words, quality=%s, ocr=%s",
        doc.id, doc.total_words, doc.extraction_quality, doc.ocr_used
    )

    return jsonify({
        "status": "success",
        "message": "Your document has been successfully processed and is ready for AI summarization.",
        "document": doc.to_dict(include_text=True),
        "warnings": extraction_res.get("warnings", [])
    }), 200


# ============================================================================
# 3. DIRECT TEXT INGESTION (POST /api/documents/text)
# ============================================================================
@document_bp.route("/text", methods=["POST"])
@jwt_required()
def ingest_direct_text():
    """Allows direct pasting of study notes without file upload."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "Pasted Study Notes").strip()
    raw_content = data.get("content", "").strip()

    if not raw_content:
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": "Content field cannot be empty.",
            "status_code": 400
        }), 400

    if len(raw_content) < 50:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": "Content is too short for meaningful educational processing (minimum 50 characters required).",
            "status_code": 400
        }), 400

    cleaned = clean_text(raw_content)
    quality_res = assess_text_quality(cleaned, total_pages=1, ocr_pages_count=0)

    try:
        doc = Document(
            user_id=current_user.id,
            original_filename=title[:200],
            stored_filename=None,
            file_type="text_paste",
            file_size=len(raw_content.encode("utf-8")),
            extracted_text=raw_content,
            cleaned_text=cleaned,
            processing_status="completed" if not quality_res["warnings"] else "completed_with_warnings",
            extraction_quality=quality_res["quality"],
            total_pages=1,
            total_words=quality_res["total_words"],
            total_characters=quality_res["total_characters"],
            ocr_used=False,
            extraction_metadata={
                "direct_paste": True,
                "warnings": quality_res["warnings"]
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to save direct text document: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Database Error",
            "message": "Could not save direct text document to database.",
            "status_code": 500
        }), 500

    return jsonify({
        "status": "success",
        "message": "Your text notes have been ingested and are ready for AI summarization.",
        "document": doc.to_dict(include_text=True),
        "warnings": quality_res["warnings"]
    }), 201


# ============================================================================
# 4. GET DOCUMENT LIST (GET /api/documents)
# ============================================================================
@document_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    """Returns paginated list of documents owned by the authenticated user."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit_param = request.args.get("limit") or request.args.get("per_page") or 10
        limit = min(50, max(1, int(limit_param)))
    except ValueError:
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "message": "Query parameters 'page' and 'limit' must be positive integers.",
            "status_code": 400
        }), 400

    sort_order = request.args.get("sort", "newest").lower()

    query = Document.query.filter_by(user_id=current_user.id)
    if sort_order == "oldest":
        query = query.order_by(Document.created_at.asc())
    else:
        query = query.order_by(Document.created_at.desc())

    paginated = query.paginate(page=page, per_page=limit, error_out=False)

    documents_data = [doc.to_dict(include_text=False) for doc in paginated.items]

    return jsonify({
        "status": "success",
        "documents": documents_data,
        "pagination": {
            "total_items": paginated.total,
            "current_page": paginated.page,
            "total_pages": paginated.pages,
            "limit": limit,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev
        }
    }), 200


# ============================================================================
# 5. GET DOCUMENT DETAILS (GET /api/documents/<int:document_id>)
# ============================================================================
@document_bp.route("/<int:document_id>", methods=["GET"])
@jwt_required()
def get_document_details(document_id: int):
    """Retrieves metadata and full extracted content for a specific document."""
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Document #{document_id} was not found.",
            "status_code": 404
        }), 404

    # Ownership check
    if doc.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to view this document.",
            "status_code": 403
        }), 403

    include_text = request.args.get("include_text", "true").lower() in ("true", "1", "yes")
    return jsonify({
        "status": "success",
        "document": doc.to_dict(include_text=include_text)
    }), 200


# ============================================================================
# 6. DELETE DOCUMENT (DELETE /api/documents/<int:document_id>)
# ============================================================================
@document_bp.route("/<int:document_id>", methods=["DELETE"])
@jwt_required()
def delete_document(document_id: int):
    """Deletes a document record and safely removes its stored file from disk."""
    doc = db.session.get(Document, document_id)
    if not doc:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Document #{document_id} was not found.",
            "status_code": 404
        }), 404

    # Ownership check
    if doc.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to delete this document.",
            "status_code": 403
        }), 403

    # Remove file from disk if present
    if doc.stored_filename:
        user_dir = _get_user_upload_dir(doc.user_id)
        file_path = user_dir / doc.stored_filename
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as exc:
            logger.warning("Failed to remove file from disk '%s': %s", file_path, exc)

    try:
        db.session.delete(doc)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to delete document #%d: %s", document_id, exc)
        return jsonify({
            "status": "error",
            "error": "Database Error",
            "message": "Failed to delete document from database.",
            "status_code": 500
        }), 500

    logger.info("Document #%d deleted by user #%d", document_id, current_user.id)
    return jsonify({
        "status": "success",
        "message": "Document and associated files deleted successfully."
    }), 200

