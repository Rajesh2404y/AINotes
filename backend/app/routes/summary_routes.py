"""
AI Summarization and Study Notes API Routes.

Implements authenticated endpoints for:
- POST /api/summaries/generate: Generate multi-tier summary with takeaways, definitions, and keywords
- GET /api/summaries: Paginated user summaries list
- GET /api/summaries/<int:summary_id>: Retrieve specific summary with document context
- DELETE /api/summaries/<int:summary_id>: Delete summary
- GET /api/summaries/<int:summary_id>/export: Download as PDF or plain text
"""
from __future__ import annotations

import io
import logging
import time
from flask import Blueprint, current_app, jsonify, request, send_file
from flask_jwt_extended import current_user, jwt_required

from backend.app.ai.content_extraction_service import content_extraction_service
from backend.app.ai.summarization_service import summarization_service
from backend.app.ai.summary_quality_service import summary_quality_service
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.services.summary_export_service import summary_export_service

logger = logging.getLogger("ainotes.summary_routes")

summary_bp = Blueprint("summaries", __name__, url_prefix="/api/summaries")


@summary_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_summary():
    """
    Generates an AI summary and study notes from an existing processed document.
    """
    data = request.get_json(silent=True) or {}
    document_id = data.get("document_id")
    summary_type = data.get("summary_type") or data.get("mode") or "medium"

    if not document_id:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": "Field 'document_id' is required."
        }), 400

    valid_types = {"short", "medium", "detailed"}
    if summary_type not in valid_types:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": f"Invalid summary_type '{summary_type}'. Must be one of: short, medium, detailed."
        }), 400

    # Fetch document and verify ownership
    document = db.session.get(Document, int(document_id))
    if not document:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Document with ID {document_id} was not found."
        }), 404

    if document.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to access this document."
        }), 403

    # Check extracted content
    source_text = document.extracted_text or ""
    if not source_text.strip():
        return jsonify({
            "status": "error",
            "error": "Unprocessable Entity",
            "message": "The selected document does not contain extracted text. Please process or extract text first."
        }), 422

    start_time = time.time()
    try:
        # 1. Summarization
        summary_result = summarization_service.generate_summary(
            text=source_text,
            mode=summary_type
        )
        summary_text = summary_result.get("summary_text", "")

        # 2. Key Takeaways, Definitions, and Keywords
        extraction_result = content_extraction_service.extract_all(source_text)

        # 3. Quality and Grounding Evaluation
        quality_result = summary_quality_service.evaluate(
            source_text=source_text,
            summary_text=summary_text
        )

        duration = time.time() - start_time

        # 4. Save to Database
        summary = Summary(
            user_id=current_user.id,
            document_id=document.id,
            summary_type=summary_type,
            summary_text=summary_text,
            key_takeaways=extraction_result.get("key_takeaways", []),
            definitions=extraction_result.get("definitions", []),
            keywords=extraction_result.get("keywords", []),
            model_name=summary_result.get("model_name"),
            model_version=summary_result.get("model_version"),
            source_token_count=summary_result.get("source_token_count", 0),
            generated_token_count=summary_result.get("generated_token_count", 0),
            total_chunks=summary_result.get("total_chunks", 1),
            processing_duration=duration,
            summary_metadata={
                "quality": quality_result,
                "generation_meta": summary_result.get("metadata", {})
            }
        )

        db.session.add(summary)
        db.session.commit()

        logger.info(
            f"Generated summary id={summary.id} for doc_id={document.id} user={current_user.id} in {duration:.2f}s"
        )

        return jsonify({
            "status": "success",
            "message": "Summary generated successfully.",
            "data": {
                **summary.to_dict(),
                "document_title": document.original_filename
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error during summary generation: {e}")
        return jsonify({
            "status": "error",
            "error": "Generation Failed",
            "message": f"Failed to generate summary: {str(e)}"
        }), 500


@summary_bp.route("", methods=["GET"])
@jwt_required()
def list_summaries():
    """
    Returns a paginated list of summaries for the current authenticated user.
    Optional query params: document_id, page, per_page.
    """
    document_id = request.args.get("document_id", type=int)
    page = request.args.get("page", default=1, type=int)
    per_page = min(request.args.get("per_page", default=10, type=int), 100)

    query = Summary.query.filter_by(user_id=current_user.id)
    if document_id:
        query = query.filter_by(document_id=document_id)

    query = query.order_by(Summary.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "data": {
            "summaries": [s.to_dict() for s in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }
    }), 200


@summary_bp.route("/<int:summary_id>", methods=["GET"])
@jwt_required()
def get_summary(summary_id: int):
    """
    Retrieves full details of a specific summary.
    """
    summary = db.session.get(Summary, summary_id)
    if not summary:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Summary with ID {summary_id} was not found."
        }), 404

    if summary.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to view this summary."
        }), 403

    doc = summary.document
    return jsonify({
        "status": "success",
        "data": {
            **summary.to_dict(),
            "document": {
                "id": doc.id,
                "title": doc.original_filename,
                "file_type": doc.file_type,
                "word_count": doc.total_words
            }
        }
    }), 200


@summary_bp.route("/<int:summary_id>", methods=["DELETE"])
@jwt_required()
def delete_summary(summary_id: int):
    """
    Deletes an existing summary.
    """
    summary = db.session.get(Summary, summary_id)
    if not summary:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Summary with ID {summary_id} was not found."
        }), 404

    if summary.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to delete this summary."
        }), 403

    db.session.delete(summary)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Summary {summary_id} has been deleted successfully."
    }), 200


@summary_bp.route("/<int:summary_id>/export", methods=["GET"])
@jwt_required()
def export_summary(summary_id: int):
    """
    Exports a summary as PDF or plain text.
    Query param format: 'pdf' (default) or 'txt'.
    """
    summary = db.session.get(Summary, summary_id)
    if not summary:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Summary with ID {summary_id} was not found."
        }), 404

    if summary.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to export this summary."
        }), 403

    export_format = request.args.get("format", "pdf").lower()
    doc_title = summary.document.original_filename if summary.document else "Study Notes"
    summary_dict = summary.to_dict()

    if export_format == "txt":
        txt_content = summary_export_service.export_txt(summary_dict, doc_title=doc_title)
        mem = io.BytesIO()
        mem.write(txt_content.encode("utf-8"))
        mem.seek(0)
        return send_file(
            mem,
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name=f"summary_{summary.id}.txt"
        )
    elif export_format == "pdf":
        try:
            pdf_buffer = summary_export_service.export_pdf(summary_dict, doc_title=doc_title)
            return send_file(
                pdf_buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"summary_{summary.id}.pdf"
            )
        except Exception as e:
            logger.exception(f"PDF export failed: {e}")
            return jsonify({
                "status": "error",
                "error": "Export Failed",
                "message": f"Could not generate PDF: {str(e)}"
            }), 500
    else:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": f"Unsupported export format '{export_format}'. Supported formats: pdf, txt."
        }), 400

