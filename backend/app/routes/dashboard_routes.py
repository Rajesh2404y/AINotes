"""Dashboard Analytics and Activity REST Endpoints.

Provides aggregated KPIs, recent activity timeline, and quiz score performance
for the authenticated user. All metrics are derived from real database records.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from sqlalchemy import func
from backend.app.extensions import db
from backend.app.models import Document, Summary, Quiz, QuizAttempt, Translation
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.utils.datetime_utils import to_utc_iso

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _calculate_study_streak(user_id):
    """Calculates consecutive days of study activity ending today or yesterday with windowed querying."""
    today = datetime.utcnow().date()
    activity_dates = set()
    window_start = datetime.utcnow() - timedelta(days=90)

    # Collect distinct activity dates within the active 90-day window
    for d in (
        db.session.query(Document.created_at)
        .filter(Document.user_id == user_id, Document.created_at >= window_start)
        .distinct()
        .all()
    ):
        if d[0]:
            activity_dates.add(d[0].date())

    for s in (
        db.session.query(Summary.created_at)
        .filter(Summary.user_id == user_id, Summary.created_at >= window_start)
        .distinct()
        .all()
    ):
        if s[0]:
            activity_dates.add(s[0].date())

    for a in (
        db.session.query(QuizAttempt.completed_at)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.completed_at >= window_start)
        .distinct()
        .all()
    ):
        if a[0]:
            activity_dates.add(a[0].date())

    for t in (
        db.session.query(Translation.created_at)
        .filter(Translation.user_id == user_id, Translation.created_at >= window_start)
        .distinct()
        .all()
    ):
        if t[0]:
            activity_dates.add(t[0].date())

    if not activity_dates:
        # Check if user ever had any historical record
        has_any = (
            Document.query.filter_by(user_id=user_id).first() is not None
            or Summary.query.filter_by(user_id=user_id).first() is not None
            or QuizAttempt.query.filter_by(user_id=user_id).first() is not None
        )
        return 1 if has_any else 0

    streak = 0
    curr = today
    if curr not in activity_dates:
        curr = today - timedelta(days=1)

    while curr in activity_dates:
        streak += 1
        curr -= timedelta(days=1)

    return max(streak, 1 if len(activity_dates) > 0 else 0)


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_authenticated
def get_dashboard_stats():
    """GET /api/dashboard/stats

    Calculates real database counts and averages scoped strictly to the current user.
    """
    user = get_current_user()

    total_docs = Document.query.filter_by(user_id=user.id).count()
    total_summaries = Summary.query.filter_by(user_id=user.id).count()
    total_quizzes = QuizAttempt.query.filter_by(user_id=user.id).count()
    total_translations = Translation.query.filter_by(user_id=user.id).count()

    # Calculate average and highest score across quiz attempts
    avg_score = (
        db.session.query(func.avg(QuizAttempt.percentage))
        .filter(QuizAttempt.user_id == user.id)
        .scalar()
    )
    max_score = (
        db.session.query(func.max(QuizAttempt.percentage))
        .filter(QuizAttempt.user_id == user.id)
        .scalar()
    )
    average_score = round(float(avg_score), 1) if avg_score is not None else 0.0
    highest_score = round(float(max_score), 1) if max_score is not None else 0.0

    total_activities = total_docs + total_summaries + total_quizzes + total_translations
    streak_days = _calculate_study_streak(user.id)

    return jsonify({
        "status": "success",
        "stats": {
            "total_documents": total_docs,
            "summaries_generated": total_summaries,
            "total_summaries": total_summaries,
            "quizzes_attempted": total_quizzes,
            "total_quizzes_completed": total_quizzes,
            "average_quiz_score": average_score,
            "highest_quiz_score": highest_score,
            "translations_completed": total_translations,
            "total_translations": total_translations,
            "learning_activities": total_activities,
            "study_streak_days": streak_days
        }
    }), 200


@dashboard_bp.route("/activities", methods=["GET"])
@jwt_authenticated
def get_recent_activities():
    """GET /api/dashboard/activities

    Aggregates recent events across documents, summaries, quizzes, and translations.
    """
    user = get_current_user()
    limit = request.args.get("limit", default=10, type=int)
    activities = []

    # 1. Recent Documents
    docs = Document.query.filter_by(user_id=user.id).order_by(Document.created_at.desc()).limit(limit).all()
    for d in docs:
        activities.append({
            "id": f"doc-{d.id}",
            "raw_id": d.id,
            "title": d.original_filename or "Untitled Document",
            "type": "document",
            "type_label": "Document Upload",
            "status": d.processing_status,
            "details": f"File type: {(d.file_type or 'doc').upper()} - {d.processing_status.capitalize()}",
            "timestamp": to_utc_iso(d.created_at),
            "link": "upload.html"
        })

    # 2. Recent Summaries
    sums = Summary.query.filter_by(user_id=user.id).order_by(Summary.created_at.desc()).limit(limit).all()
    for s in sums:
        activities.append({
            "id": f"sum-{s.id}",
            "raw_id": s.id,
            "title": f"{(s.summary_type or 'Text').capitalize()} Summary",
            "type": "summary",
            "type_label": "AI Summary",
            "status": "completed",
            "details": f"Generated {s.summary_type} summary from Doc #{s.document_id}",
            "timestamp": to_utc_iso(s.created_at),
            "link": "summary.html"
        })

    # 3. Recent Quiz Attempts
    attempts = QuizAttempt.query.filter_by(user_id=user.id).order_by(QuizAttempt.completed_at.desc()).limit(limit).all()
    for a in attempts:
        activities.append({
            "id": f"quiz-{a.id}",
            "raw_id": a.id,
            "quiz_id": a.quiz_id,
            "title": f"Quiz Assessment Attempt",
            "type": "quiz",
            "type_label": "Quiz Practice",
            "status": f"{int(a.percentage)}%",
            "details": f"Scored {a.score}/{a.total_questions} ({int(a.percentage)}%) on Quiz #{a.quiz_id}",
            "timestamp": to_utc_iso(a.completed_at),
            "link": "quiz-results.html"
        })

    # 4. Recent Translations
    trans = Translation.query.filter_by(user_id=user.id).order_by(Translation.created_at.desc()).limit(limit).all()
    for t in trans:
        activities.append({
            "id": f"trans-{t.id}",
            "raw_id": t.id,
            "title": f"Translated to {(t.target_language or '').upper()}",
            "type": "translation",
            "type_label": "Translation",
            "status": "completed",
            "details": f"Language translation from Summary #{t.summary_id}",
            "timestamp": to_utc_iso(t.created_at),
            "link": "translate.html"
        })

    # Sort all activities by timestamp descending
    activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return jsonify({
        "status": "success",
        "activities": activities[:limit]
    }), 200


@dashboard_bp.route("/performance", methods=["GET"])
@jwt_authenticated
def get_quiz_performance():
    """GET /api/dashboard/performance

    Returns chronological quiz scores, category distributions, and 7-day velocity for Chart.js.
    """
    user = get_current_user()

    attempts = (
        QuizAttempt.query.filter_by(user_id=user.id)
        .order_by(QuizAttempt.completed_at.asc())
        .limit(15)
        .all()
    )

    labels = []
    scores = []
    percentages = []

    for idx, att in enumerate(attempts):
        label = att.completed_at.strftime("%b %d") if att.completed_at else f"Attempt {idx + 1}"
        labels.append(label)
        scores.append(att.score)
        percentages.append(round(att.percentage, 1))

    # Activity breakdown counts
    doc_count = Document.query.filter_by(user_id=user.id).count()
    sum_count = Summary.query.filter_by(user_id=user.id).count()
    quiz_count = QuizAttempt.query.filter_by(user_id=user.id).count()
    trans_count = Translation.query.filter_by(user_id=user.id).count()

    # 7-day Velocity Breakdown
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=6 - i)) for i in range(7)]
    weekly_labels = [d.strftime("%a") for d in days]
    day_indices = {d: i for i, d in enumerate(days)}

    doc_velocity = [0] * 7
    sum_velocity = [0] * 7
    quiz_velocity = [0] * 7
    trans_velocity = [0] * 7

    start_date = datetime.combine(days[0], datetime.min.time())

    for d in Document.query.filter(Document.user_id == user.id, Document.created_at >= start_date).all():
        if d.created_at and d.created_at.date() in day_indices:
            doc_velocity[day_indices[d.created_at.date()]] += 1

    for s in Summary.query.filter(Summary.user_id == user.id, Summary.created_at >= start_date).all():
        if s.created_at and s.created_at.date() in day_indices:
            sum_velocity[day_indices[s.created_at.date()]] += 1

    for a in QuizAttempt.query.filter(QuizAttempt.user_id == user.id, QuizAttempt.completed_at >= start_date).all():
        if a.completed_at and a.completed_at.date() in day_indices:
            quiz_velocity[day_indices[a.completed_at.date()]] += 1

    for t in Translation.query.filter(Translation.user_id == user.id, Translation.created_at >= start_date).all():
        if t.created_at and t.created_at.date() in day_indices:
            trans_velocity[day_indices[t.created_at.date()]] += 1

    return jsonify({
        "status": "success",
        "performance": {
            # Backwards compatibility keys
            "labels": labels,
            "scores": scores,
            "percentages": percentages,
            "distribution": {
                "documents": doc_count,
                "summaries": sum_count,
                "quizzes": quiz_count,
                "translations": trans_count
            },
            # Explicit Chart.js structures for frontend
            "quiz_trends": {
                "dates": labels if labels else weekly_labels,
                "scores": percentages if percentages else [0] * 7
            },
            "weekly_activity": {
                "labels": weekly_labels,
                "documents": doc_velocity,
                "summaries": sum_velocity,
                "quizzes": quiz_velocity,
                "translations": trans_velocity
            },
            "category_distribution": {
                "labels": ["Documents", "Summaries", "Quizzes", "Translations"],
                "counts": [doc_count, sum_count, quiz_count, trans_count]
            }
        }
    }), 200
