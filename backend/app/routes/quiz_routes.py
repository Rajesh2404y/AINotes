"""
Interactive Quiz Management and Assessment API Routes.

Implements authenticated endpoints for:
- POST /api/quizzes/generate: Synthesizes source-grounded quiz questions
- GET /api/quizzes/<int:quiz_id>: Fetches questions for practice without exposing answer keys
- GET /api/quizzes: Paginated list of user quizzes with filtering
- POST /api/quizzes/<int:quiz_id>/submit: Server-side answer evaluation and attempt recording
- GET /api/quizzes/attempts/<int:attempt_id>: Full scoring breakdown and question reviews
- GET /api/quizzes/history: Paginated user assessment attempt history
- DELETE /api/quizzes/<int:quiz_id>: Deletes quiz and associated questions
"""
from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from flask_jwt_extended import current_user, jwt_required

from backend.app.extensions import db
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.services.quiz_attempt_service import (
    QuizAttemptServiceError,
    quiz_attempt_service,
)
from backend.app.services.quiz_service import QuizServiceError, quiz_service

logger = logging.getLogger("ainotes.quiz_routes")

quiz_bp = Blueprint("quizzes", __name__, url_prefix="/api/quizzes")


@quiz_bp.route("/generate", methods=["POST"])
@jwt_required()
def generate_quiz():
    """
    Generates a new assessment quiz from a selected document or summary.
    """
    data = request.get_json(silent=True) or {}
    document_id = data.get("document_id")
    summary_id = data.get("summary_id")
    question_types = data.get("question_types")
    difficulty = data.get("difficulty", "medium")
    total_questions = data.get("total_questions", 10)

    # Type handling for question_types if passed as string or list
    if isinstance(question_types, str):
        question_types = [question_types]

    # Validate total_questions
    if total_questions is not None:
        try:
            total_questions = int(total_questions)
            if total_questions < 1 or total_questions > 50:
                return jsonify({
                    "status": "error",
                    "error": "Invalid Question Count",
                    "message": "Question count must be between 1 and 50."
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "error": "Invalid Question Count",
                "message": "Question count must be a valid integer."
            }), 400
    else:
        total_questions = 10

    try:
        quiz = quiz_service.create_quiz(
            user_id=current_user.id,
            document_id=int(document_id) if document_id else None,
            summary_id=int(summary_id) if summary_id else None,
            question_types=question_types,
            difficulty=difficulty,
            total_questions=total_questions
        )

        return jsonify({
            "status": "success",
            "message": f"Successfully generated quiz with {quiz.total_questions} questions.",
            "data": quiz.to_dict(include_questions=True, include_answers=False)
        }), 201

    except QuizServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Quiz Creation Error",
            "message": err.message
        }), err.status_code
    except Exception as exc:
        logger.exception("Unexpected error in quiz generation: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Server Error",
            "message": f"Failed to generate quiz: {str(exc)}"
        }), 500


@quiz_bp.route("/<int:quiz_id>", methods=["GET"])
@jwt_required()
def get_quiz(quiz_id: int):
    """
    Retrieves quiz questions for a test session.
    Strictly omits correct answers and explanations.
    """
    try:
        quiz = quiz_service.get_quiz_for_user(quiz_id, current_user.id)
        return jsonify({
            "status": "success",
            "data": quiz.to_dict(include_questions=True, include_answers=False)
        }), 200
    except QuizServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Quiz Retrieval Error",
            "message": err.message
        }), err.status_code


@quiz_bp.route("", methods=["GET"])
@jwt_required()
def list_quizzes():
    """
    Returns a paginated list of quizzes for the current user.
    """
    document_id = request.args.get("document_id", type=int)
    difficulty = request.args.get("difficulty")
    quiz_type = request.args.get("quiz_type")
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    result = quiz_service.list_quizzes(
        user_id=current_user.id,
        document_id=document_id,
        difficulty=difficulty,
        quiz_type=quiz_type,
        page=page,
        per_page=per_page
    )

    return jsonify({
        "status": "success",
        "data": result
    }), 200


@quiz_bp.route("/<int:quiz_id>/submit", methods=["POST"])
@jwt_required()
def submit_quiz(quiz_id: int):
    """
    Grades user answers server-side, records an attempt, and returns results.
    """
    data = request.get_json(silent=True) or {}
    responses = data.get("responses", [])

    if not isinstance(responses, list):
        return jsonify({
            "status": "error",
            "error": "Validation Error",
            "message": "Field 'responses' must be a list of question answers."
        }), 400

    try:
        result = quiz_attempt_service.submit_attempt(
            quiz_id=quiz_id,
            user_id=current_user.id,
            responses_payload=responses
        )

        return jsonify({
            "status": "success",
            "message": "Quiz submitted and evaluated successfully.",
            "data": result
        }), 200

    except QuizAttemptServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Submission Evaluation Error",
            "message": err.message
        }), err.status_code
    except Exception as exc:
        logger.exception("Unexpected error in quiz submission: %s", exc)
        return jsonify({
            "status": "error",
            "error": "Server Error",
            "message": f"Failed to grade quiz: {str(exc)}"
        }), 500


@quiz_bp.route("/attempts/<int:attempt_id>", methods=["GET"])
@jwt_required()
def get_attempt_results(attempt_id: int):
    """
    Returns the comprehensive score and answer review for an attempt.
    """
    try:
        result = quiz_attempt_service.get_attempt_details(attempt_id, current_user.id)
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except QuizAttemptServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Attempt Retrieval Error",
            "message": err.message
        }), err.status_code


@quiz_bp.route("/history", methods=["GET"])
@jwt_required()
def quiz_history():
    """
    Returns paginated attempt history for the authenticated user.
    """
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)

    result = quiz_attempt_service.list_user_history(
        user_id=current_user.id,
        page=page,
        per_page=per_page
    )

    return jsonify({
        "status": "success",
        "data": result
    }), 200


@quiz_bp.route("/<int:quiz_id>", methods=["DELETE"])
@jwt_required()
def delete_quiz(quiz_id: int):
    """
    Deletes a quiz and all cascaded questions and attempts.
    """
    try:
        quiz_service.delete_quiz(quiz_id, current_user.id)
        return jsonify({
            "status": "success",
            "message": f"Quiz {quiz_id} has been deleted successfully."
        }), 200
    except QuizServiceError as err:
        return jsonify({
            "status": "error",
            "error": "Quiz Deletion Error",
            "message": err.message
        }), err.status_code


@quiz_bp.route("/attempts/<int:attempt_id>", methods=["DELETE"])
@jwt_required()
def delete_attempt(attempt_id: int):
    """
    Deletes a specific quiz attempt record.
    """
    attempt = db.session.get(QuizAttempt, attempt_id)
    if not attempt:
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "message": f"Quiz attempt #{attempt_id} was not found."
        }), 404

    if attempt.user_id != current_user.id:
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "message": "You do not have permission to delete this quiz attempt."
        }), 403

    db.session.delete(attempt)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Quiz attempt #{attempt_id} has been deleted successfully."
    }), 200


