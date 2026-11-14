"""Personalized Learning Recommendations REST Endpoints.
"""

from flask import Blueprint, jsonify, request
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.services.recommendation_service import (
    RecommendationServiceError,
    recommendation_service,
)

recommendation_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")


@recommendation_bp.route("", methods=["GET"])
@jwt_authenticated
def get_recommendations():
    """GET /api/recommendations?status=pending&priority=high&page=1&per_page=10

    Returns paginated personalized recommendations for the authenticated user.
    """
    user = get_current_user()
    status = request.args.get("status")
    priority = request.args.get("priority")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    items, pagination = recommendation_service.get_recommendations(
        user_id=user.id,
        status=status,
        priority=priority,
        page=page,
        per_page=per_page,
    )
    return jsonify({
        "status": "success",
        "data": items,
        "pagination": pagination,
    }), 200


@recommendation_bp.route("/generate", methods=["POST"])
@jwt_authenticated
def generate_recommendations():
    """POST /api/recommendations/generate

    Analyzes student performance and generates fresh prioritized recommendations.
    """
    user = get_current_user()
    items = recommendation_service.generate_user_recommendations(user.id)
    return jsonify({
        "status": "success",
        "message": f"Successfully generated {len(items)} personalized recommendation(s).",
        "data": items,
    }), 200


@recommendation_bp.route("/<int:recommendation_id>", methods=["PATCH"])
@jwt_authenticated
def update_recommendation_status(recommendation_id: int):
    """PATCH /api/recommendations/<id>

    Body: {"status": "in_progress" | "completed" | "dismissed" | "pending"}
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"status": "error", "message": "'status' field is required."}), 400

    try:
        updated = recommendation_service.update_recommendation_status(
            user_id=user.id,
            recommendation_id=recommendation_id,
            new_status=new_status,
        )
        return jsonify({
            "status": "success",
            "message": f"Recommendation updated to '{new_status}'.",
            "data": updated,
        }), 200
    except RecommendationServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code

