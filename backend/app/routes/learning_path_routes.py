"""Adaptive Learning Paths REST Endpoints.
"""

from flask import Blueprint, jsonify, request
from backend.app.middleware.auth_guard import get_current_user, jwt_authenticated
from backend.app.services.learning_path_service import (
    LearningPathServiceError,
    learning_path_service,
)

learning_path_bp = Blueprint("learning_paths", __name__, url_prefix="/api/learning-paths")


@learning_path_bp.route("/generate", methods=["POST"])
@jwt_authenticated
def generate_learning_path():
    """POST /api/learning-paths/generate

    Body:
    {
        "topic": "Neural Networks",
        "document_id": 12 (optional),
        "summary_id": 5 (optional)
    }
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    topic = data.get("topic")

    if not topic or not str(topic).strip():
        return jsonify({"status": "error", "message": "'topic' is required to generate a learning path."}), 400

    try:
        path = learning_path_service.create_learning_path(
            user_id=user.id,
            target_topic=str(topic).strip(),
            document_id=data.get("document_id"),
            summary_id=data.get("summary_id"),
        )
        return jsonify({
            "status": "success",
            "message": f"Adaptive learning path created for topic '{topic}'.",
            "data": path,
        }), 201
    except LearningPathServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code


@learning_path_bp.route("", methods=["GET"])
@jwt_authenticated
def list_learning_paths():
    """GET /api/learning-paths?status=in_progress&page=1&per_page=10

    Returns paginated list of learning paths for the user.
    """
    user = get_current_user()
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    items, pagination = learning_path_service.list_learning_paths(
        user_id=user.id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return jsonify({
        "status": "success",
        "data": items,
        "pagination": pagination,
    }), 200


@learning_path_bp.route("/<int:path_id>", methods=["GET"])
@jwt_authenticated
def get_learning_path(path_id: int):
    """GET /api/learning-paths/<id>

    Returns path metadata, progress percentage, and sequential activities.
    """
    user = get_current_user()
    try:
        path = learning_path_service.get_path_details(user_id=user.id, path_id=path_id)
        return jsonify({"status": "success", "data": path}), 200
    except LearningPathServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code


@learning_path_bp.route("/<int:path_id>", methods=["PATCH"])
@jwt_authenticated
def update_learning_path(path_id: int):
    """PATCH /api/learning-paths/<id>

    Body: {"status": "in_progress" | "paused" | "completed" | "not_started"}
    """
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"status": "error", "message": "'status' field is required."}), 400

    try:
        updated = learning_path_service.update_path_status(
            user_id=user.id, path_id=path_id, new_status=new_status
        )
        return jsonify({
            "status": "success",
            "message": f"Learning path status updated to '{new_status}'.",
            "data": updated,
        }), 200
    except LearningPathServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code


@learning_path_bp.route("/<int:path_id>/activities/<int:activity_id>/complete", methods=["POST"])
@jwt_authenticated
def complete_learning_activity(path_id: int, activity_id: int):
    """POST /api/learning-paths/<id>/activities/<activity_id>/complete

    Verifies server-side completion of milestone activity and recalculates path progress.
    """
    user = get_current_user()
    try:
        result = learning_path_service.complete_activity(
            user_id=user.id, path_id=path_id, activity_id=activity_id
        )
        return jsonify({
            "status": "success",
            "message": result["message"],
            "data": {
                "activity": result["activity"],
                "path": result["path"],
            }
        }), 200
    except LearningPathServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code


@learning_path_bp.route("/<int:path_id>", methods=["DELETE"])
@jwt_authenticated
def delete_learning_path(path_id: int):
    """DELETE /api/learning-paths/<id>

    Deletes a learning path and associated activities.
    """
    user = get_current_user()
    try:
        learning_path_service.delete_learning_path(user_id=user.id, path_id=path_id)
        return jsonify({
            "status": "success",
            "message": f"Learning path {path_id} deleted successfully.",
        }), 200
    except LearningPathServiceError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code

