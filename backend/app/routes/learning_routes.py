"""Learning Analytics and Adaptive Difficulty REST Endpoints.
"""

from flask import Blueprint, jsonify, request
from backend.app.ai.adaptive_difficulty_service import adaptive_difficulty_service
from backend.app.ai.learning_analysis_service import learning_analysis_service
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.services.learning_progress_service import learning_progress_service

learning_bp = Blueprint("learning", __name__, url_prefix="/api/learning")


@learning_bp.route("/overview", methods=["GET"])
@jwt_authenticated
def get_learning_overview():
    """GET /api/learning/overview

    Returns comprehensive performance overview, topic classifications,
    and recommended next action based on real completed quizzes.
    """
    user = get_current_user()
    overview = learning_progress_service.get_topic_overview(user.id)
    return jsonify({"status": "success", "data": overview}), 200


@learning_bp.route("/topics", methods=["GET"])
@jwt_authenticated
def get_topic_performance():
    """GET /api/learning/topics

    Returns topic-level metrics, accuracy, question breakdown,
    diagnostic reasons, and longitudinal learning trends.
    """
    user = get_current_user()
    learning_progress_service.sync_user_progress(user.id)
    analysis = learning_analysis_service.analyze_user_learning(user.id)

    return jsonify({
        "status": "success",
        "data": {
            "topics": list(analysis.get("topic_performance", {}).values()),
            "difficulty_breakdown": analysis.get("difficulty_performance", {}),
            "question_type_breakdown": analysis.get("question_type_performance", {}),
            "repeated_mistakes": analysis.get("repeated_incorrect_count", 0),
        }
    }), 200


@learning_bp.route("/adaptive-difficulty", methods=["GET"])
@jwt_authenticated
def get_adaptive_difficulty():
    """GET /api/learning/adaptive-difficulty?topic=<topic>

    Returns data-grounded quiz difficulty tier recommendation.
    """
    user = get_current_user()
    topic = request.args.get("topic")
    rec = adaptive_difficulty_service.recommend_difficulty(user.id, topic=topic)
    return jsonify({"status": "success", "data": rec}), 200

