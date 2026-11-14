"""History REST Endpoints with Server-Side Database Pagination.

Provides paginated, searchable, categorized study history records for the authenticated user.
Supports:
- Category filtering: all, document, summary, quiz, translation
- Real-time search across titles, details, topics, and languages
- Configurable page sizes: 10, 20, 50
- Deterministic sorting by timestamp descending with unique ID tie-breaker
- Database-level slicing (avoids loading all records into memory)
"""

import math
from flask import Blueprint, jsonify, request
from sqlalchemy import literal, union_all, or_
from backend.app.extensions import db
from backend.app.models import Document, Summary, QuizAttempt, Translation
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.utils.datetime_utils import to_utc_iso

history_bp = Blueprint("history", __name__, url_prefix="/api/history")

ALLOWED_TYPES = {"all", "document", "summary", "quiz", "translation"}
ALLOWED_PAGE_SIZES = {10, 20, 50}


@history_bp.route("", methods=["GET"])
@history_bp.route("/", methods=["GET"])
@jwt_authenticated
def get_user_history():
    """GET /api/history

    Query parameters:
    - page: int (>= 1, default 1)
    - per_page: int (10, 20, 50, default 10)
    - type: string (all, document, summary, quiz, translation, default all)
    - search: string (optional search keyword)

    Returns:
    JSON payload containing paginated history data and navigation metadata.
    """
    user = get_current_user()

    # 1. Parse and validate pagination parameters
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", 10))
        if per_page not in ALLOWED_PAGE_SIZES:
            # Clamp or fallback to 10 if invalid
            if per_page <= 0:
                per_page = 10
            elif per_page > 100:
                per_page = 50
    except (ValueError, TypeError):
        per_page = 10

    # 2. Parse and validate type filter
    raw_type = request.args.get("type", "all").strip().lower()
    item_type = raw_type if raw_type in ALLOWED_TYPES else "all"

    # 3. Parse search query
    search_query = request.args.get("search", "").strip()
    search_term = f"%{search_query}%" if search_query else None

    # 4. Build database queries per category
    subqueries = []

    # A. Documents
    if item_type in ("all", "document"):
        doc_q = db.session.query(
            Document.id.label("raw_id"),
            literal("document").label("type"),
            Document.original_filename.label("title"),
            Document.processing_status.label("status"),
            Document.created_at.label("timestamp"),
            Document.extracted_text.label("details_text"),
            Document.file_type.label("extra_info")
        ).filter(Document.user_id == user.id)

        if search_term:
            doc_q = doc_q.filter(
                or_(
                    Document.original_filename.ilike(search_term),
                    Document.extracted_text.ilike(search_term),
                    Document.file_type.ilike(search_term),
                    Document.processing_status.ilike(search_term)
                )
            )
        subqueries.append(doc_q)

    # B. Summaries
    if item_type in ("all", "summary"):
        sum_q = db.session.query(
            Summary.id.label("raw_id"),
            literal("summary").label("type"),
            Summary.summary_type.label("title"),
            literal("completed").label("status"),
            Summary.created_at.label("timestamp"),
            Summary.summary_text.label("details_text"),
            literal("summary").label("extra_info")
        ).filter(Summary.user_id == user.id)

        if search_term:
            sum_q = sum_q.filter(
                or_(
                    Summary.summary_type.ilike(search_term),
                    Summary.summary_text.ilike(search_term)
                )
            )
        subqueries.append(sum_q)

    # C. Quiz Attempts
    if item_type in ("all", "quiz"):
        quiz_q = db.session.query(
            QuizAttempt.id.label("raw_id"),
            literal("quiz").label("type"),
            literal("Quiz Assessment Attempt").label("title"),
            literal("completed").label("status"),
            QuizAttempt.completed_at.label("timestamp"),
            literal("Quiz Practice Score").label("details_text"),
            literal("quiz").label("extra_info")
        ).filter(QuizAttempt.user_id == user.id)

        if search_term:
            quiz_q = quiz_q.filter(
                or_(
                    literal("Quiz Assessment Attempt").ilike(search_term),
                    literal("quiz").ilike(search_term)
                )
            )
        subqueries.append(quiz_q)

    # D. Translations
    if item_type in ("all", "translation"):
        trans_q = db.session.query(
            Translation.id.label("raw_id"),
            literal("translation").label("type"),
            Translation.target_language.label("title"),
            literal("completed").label("status"),
            Translation.created_at.label("timestamp"),
            Translation.translated_text.label("details_text"),
            Translation.source_language.label("extra_info")
        ).filter(Translation.user_id == user.id)

        if search_term:
            trans_q = trans_q.filter(
                or_(
                    Translation.translated_text.ilike(search_term),
                    Translation.original_text.ilike(search_term),
                    Translation.target_language.ilike(search_term),
                    Translation.source_language.ilike(search_term)
                )
            )
        subqueries.append(trans_q)

    # 5. Union queries and execute database-level count and pagination
    if not subqueries:
        combined_subquery = None
        total_items = 0
        paginated_rows = []
    elif len(subqueries) == 1:
        combined_subquery = subqueries[0].subquery()
        total_items = db.session.query(combined_subquery).count()
        offset = (page - 1) * per_page
        paginated_rows = (
            db.session.query(combined_subquery)
            .order_by(combined_subquery.c.timestamp.desc(), combined_subquery.c.raw_id.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )
    else:
        union_stmt = union_all(*subqueries).subquery()
        total_items = db.session.query(union_stmt).count()
        offset = (page - 1) * per_page
        paginated_rows = (
            db.session.query(union_stmt)
            .order_by(union_stmt.c.timestamp.desc(), union_stmt.c.raw_id.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

    # 6. Calculate pagination metadata
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 0
    has_previous = page > 1 and total_pages > 0
    has_next = page < total_pages

    # 7. Map database records to uniform API presentation
    type_meta = {
        "document": {"type_label": "Document Upload", "link": "upload.html"},
        "summary": {"type_label": "AI Summary", "link": "summary.html"},
        "quiz": {"type_label": "Quiz Practice", "link": "quiz-results.html"},
        "translation": {"type_label": "Translation", "link": "translate.html"}
    }

    data = []
    for row in paginated_rows:
        row_type = row.type
        meta = type_meta.get(row_type, {"type_label": row_type.capitalize(), "link": "history.html"})

        # Build user-friendly title and details
        if row_type == "document":
            title = row.title or "Untitled Document"
            details = f"File type: {(row.extra_info or 'doc').upper()} - {row.status.capitalize() if row.status else 'Uploaded'}"
            status = row.status or "completed"
        elif row_type == "summary":
            summary_mode = (row.title or "Text").capitalize()
            title = f"{summary_mode} Summary"
            details = f"Generated {row.title} study summary"
            status = "completed"
        elif row_type == "quiz":
            title = "Quiz Assessment Attempt"
            # Attempt details
            details = "Completed practice quiz session"
            status = "completed"
        elif row_type == "translation":
            target_lang = (row.title or "Language").upper()
            title = f"Translated to {target_lang}"
            details = f"Language translation ({str(row.extra_info or 'en').upper()} \u2192 {target_lang})"
            status = "completed"
        else:
            title = row.title or "Study Material"
            details = ""
            status = row.status or "completed"

        data.append({
            "id": f"{row_type}-{row.raw_id}",
            "raw_id": row.raw_id,
            "type": row_type,
            "type_label": meta["type_label"],
            "title": title,
            "details": details,
            "status": status,
            "timestamp": to_utc_iso(row.timestamp),
            "link": meta["link"]
        })

    return jsonify({
        "success": True,
        "status": "success",
        "data": data,
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next
        }
    }), 200

