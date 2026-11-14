"""
Multilingual Translation API Routes.

Implements authenticated endpoints for:
- GET /api/translations/languages: Supported language catalog
- POST /api/translations/generate: Translates saved summary notes
- GET /api/translations/<int:trans_id>: Retrieves translation record
- GET /api/translations/history: Paginated user translation history
- GET /api/translations: Paginated user translation list
- DELETE /api/translations/<int:trans_id>: Deletes translation safely
- GET /api/translations/<int:trans_id>/export: Downloads PDF or TXT export
"""
from __future__ import annotations

import io
import logging
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import current_user, jwt_required

from backend.app.ai.translation_service import TranslationServiceError, translation_service
from backend.app.extensions import db
from backend.app.models.summary import Summary
from backend.app.models.translation import Translation
from backend.app.services.translation_export_service import translation_export_service
from backend.app.utils.language_utils import get_supported_languages

logger = logging.getLogger("ainotes.translation_routes")

translation_bp = Blueprint("translations", __name__, url_prefix="/api/translations")


@translation_bp.route("/languages", methods=["GET"])
def list_languages():
    """
    Returns the supported languages list with ISO codes, display names, and native labels.
    """
    languages = get_supported_languages()
    return jsonify({
        "status": "success",
        "data": languages
    }), 200


@translation_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_translation():
    """
    Generates a high-fidelity translation from an existing saved summary.
    """
    data = request.get_json(silent=True) or {}
    summary_id = data.get("summary_id")
    source_lang = (data.get("source_language") or "en").lower().strip()
    target_lang = (data.get("target_language") or "ta").lower().strip()

    if not summary_id:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": "Field 'summary_id' is required."
        }), 400

    # 1. Fetch summary and verify ownership
    summary = db.session.get(Summary, int(summary_id))
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
            "message": "You do not have permission to translate this summary."
        }), 403

    summary_text = summary.summary_text or ""
    if not summary_text.strip():
        return jsonify({
            "status": "error",
            "error": "Unprocessable Entity",
            "message": "The selected summary does not contain text to translate."
        }), 422

    force_refresh = bool(data.get("force_refresh", False))

    # 2. Check for cached existing translation to prevent duplicate work
    if not force_refresh:
        existing_trans = Translation.query.filter_by(
            user_id=current_user.id,
            summary_id=summary.id,
            source_language=source_lang,
            target_language=target_lang
        ).order_by(Translation.created_at.desc()).first()

        if existing_trans and existing_trans.original_text.strip() == summary_text.strip():
            logger.info(
                "Translation cache hit: user %d, summary %d (%s -> %s)",
                current_user.id, summary.id, source_lang, target_lang
            )
            trans_dict = existing_trans.to_dict()
            trans_dict["is_cached"] = True
            return jsonify({
                "status": "success",
                "message": "Translation retrieved from study history cache.",
                "data": trans_dict
            }), 200

    # 3. Execute translation
    try:
        trans_res = translation_service.translate_text(
            text=summary_text,
            source_lang=source_lang,
            target_lang=target_lang
        )

        # 4. Save Translation to Database
        translation = Translation(
            user_id=current_user.id,
            summary_id=summary.id,
            source_language=source_lang,
            target_language=target_lang,
            original_text=summary_text,
            translated_text=trans_res["translated_text"],
            model_name=trans_res.get("model_name"),
            total_chunks=trans_res.get("total_chunks", 1),
            processing_duration=trans_res.get("processing_duration", 0.0),
            translation_metadata=trans_res.get("metadata", {})
        )

        db.session.add(translation)
        db.session.commit()

        logger.info(
            "User %d translated summary %d (%s -> %s) successfully.",
            current_user.id, summary.id, source_lang, target_lang
        )

        return jsonify({
            "status": "success",
            "message": "Translation generated successfully.",
            "data": translation.to_dict()
        }), 201

    except TranslationServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Translation Error",
            "message": str(err)
        }), 400
    except Exception as exc:
        db.session.rollback()
        logger.exception("Unexpected translation error: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Server Error",
            "message": f"Translation failed: {str(exc)}"
        }), 500


@translation_bp.route("/<int:trans_id>", methods=["GET"])
@jwt_required()
def get_translation(trans_id: int):
    """
    Retrieves a specific translation record.
    """
    trans = db.session.get(Translation, trans_id)
    if not trans:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Translation with ID {trans_id} was not found."
        }), 404

    if trans.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to view this translation."
        }), 403

    return jsonify({
        "status": "success",
        "data": trans.to_dict()
    }), 200


@translation_bp.route("/history", methods=["GET"])
@translation_bp.route("", methods=["GET"])
@jwt_required()
def list_translations():
    """
    Returns a paginated list of translations for the current user.
    """
    source_lang = request.args.get("source_language")
    target_lang = request.args.get("target_language")
    summary_id = request.args.get("summary_id", type=int)
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    query = Translation.query.filter_by(user_id=current_user.id)
    if source_lang:
        query = query.filter_by(source_language=source_lang.lower())
    if target_lang:
        query = query.filter_by(target_language=target_lang.lower())
    if summary_id:
        query = query.filter_by(summary_id=summary_id)

    query = query.order_by(Translation.created_at.desc())
    pagination = query.paginate(page=page, per_page=min(per_page, 100), error_out=False)

    return jsonify({
        "status": "success",
        "data": {
            "translations": [t.to_dict() for t in pagination.items],
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


@translation_bp.route("/<int:trans_id>", methods=["DELETE"])
@jwt_required()
def delete_translation(trans_id: int):
    """
    Safely deletes a translation record without modifying the underlying summary.
    """
    trans = db.session.get(Translation, trans_id)
    if not trans:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Translation with ID {trans_id} was not found."
        }), 404

    if trans.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to delete this translation."
        }), 403

    db.session.delete(trans)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Translation {trans_id} has been deleted successfully."
    }), 200


@translation_bp.route("/<int:trans_id>/export", methods=["GET"])
@jwt_required()
def export_translation(trans_id: int):
    """
    Exports a translation as PDF or plain text.
    Query param format: 'pdf' (default) or 'txt'.
    """
    trans = db.session.get(Translation, trans_id)
    if not trans:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Translation with ID {trans_id} was not found."
        }), 404

    if trans.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to export this translation."
        }), 403

    export_format = request.args.get("format", "pdf").lower()
    doc_title = f"Translation ({trans.target_language.upper()})"
    if trans.summary and trans.summary.document:
        doc_title = trans.summary.document.original_filename

    trans_dict = trans.to_dict()

    if export_format == "txt":
        txt_content = translation_export_service.export_txt(trans_dict, doc_title=doc_title)
        mem = io.BytesIO()
        mem.write(txt_content.encode("utf-8"))
        mem.seek(0)
        return send_file(
            mem,
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name=f"translation_{trans.id}_{trans.target_language}.txt"
        )
    elif export_format == "pdf":
        try:
            pdf_buffer = translation_export_service.export_pdf(trans_dict, doc_title=doc_title)
            return send_file(
                pdf_buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"translation_{trans.id}_{trans.target_language}.pdf"
            )
        except Exception as exc:
            logger.exception("PDF export failed: %s", exc)
            return jsonify({
                "status": "error",
                "error": "Export Failed",
                "message": f"Could not generate PDF: {str(exc)}"
            }), 500
    else:
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": f"Unsupported export format '{export_format}'. Supported formats: pdf, txt."
        }), 400

