"""
Quiz Attempt and Submission Evaluation Service.
Handles server-side grading, record persistence, and retrieval of attempt reviews.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.app.ai.answer_evaluation_service import answer_evaluation_service
from backend.app.extensions import db
from backend.app.models.question import Question
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.quiz_response import QuizResponse

logger = logging.getLogger(__name__)


class QuizAttemptServiceError(Exception):
    """Custom exception for quiz attempt operations."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuizAttemptService:
    """Manages student quiz submission grading and attempt records."""

    def submit_attempt(
        self,
        quiz_id: int,
        user_id: int,
        responses_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Grades and persists a student's quiz submission.

        Args:
            quiz_id: Target quiz ID.
            user_id: Authenticated student ID.
            responses_payload: List of [{'question_id': int, 'answer': str}].

        Returns:
            Dict containing attempt summary and detailed question evaluations.
        """
        # 1. Fetch quiz and check ownership
        quiz = db.session.get(Quiz, quiz_id)
        if not quiz:
            raise QuizAttemptServiceError(f"Quiz with ID {quiz_id} was not found.", 404)
        if quiz.user_id != user_id:
            raise QuizAttemptServiceError("You do not have permission to submit answers for this quiz.", 403)

        questions = quiz.questions.all()
        if not questions:
            raise QuizAttemptServiceError("This quiz has no questions.", 422)

        # 2. Map questions and validate response IDs
        question_map = {q.id: q for q in questions}
        submitted_answers: Dict[int, str] = {}

        for item in responses_payload or []:
            q_id = item.get("question_id")
            if q_id not in question_map:
                raise QuizAttemptServiceError(
                    f"Question ID {q_id} does not belong to Quiz {quiz_id}.", 400
                )
            submitted_answers[q_id] = str(item.get("answer", "")).strip()

        # 3. Server-side grading
        eval_result = answer_evaluation_service.calculate_score(questions, submitted_answers)
        score = eval_result["score"]
        total = eval_result["total_questions"]
        percentage = eval_result["percentage"]

        # 4. Save QuizAttempt and QuizResponses in a transaction
        attempt = QuizAttempt(
            user_id=user_id,
            quiz_id=quiz.id,
            score=score,
            total_questions=total,
            percentage=percentage,
            completed_at=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.flush()

        for item in eval_result["evaluations"]:
            q_id = item["question_id"]
            resp = QuizResponse(
                attempt_id=attempt.id,
                question_id=q_id,
                selected_answer=item["selected_answer"],
                is_correct=item["is_correct"]
            )
            db.session.add(resp)

        db.session.commit()
        logger.info(
            "User %d submitted attempt %d for quiz %d: score %d/%d (%.1f%%)",
            user_id, attempt.id, quiz_id, score, total, percentage
        )

        return {
            "attempt_id": attempt.id,
            "quiz_id": quiz.id,
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "completed_at": attempt.completed_at.isoformat(),
            "results": eval_result["evaluations"]
        }

    def get_attempt_details(self, attempt_id: int, user_id: int) -> Dict[str, Any]:
        """
        Retrieves full score breakdown and question keys for a completed attempt.
        """
        attempt = db.session.get(QuizAttempt, attempt_id)
        if not attempt:
            raise QuizAttemptServiceError(f"Attempt with ID {attempt_id} was not found.", 404)
        if attempt.user_id != user_id:
            raise QuizAttemptServiceError("You do not have permission to view this attempt.", 403)

        responses = attempt.responses.all()
        response_details = []
        for r in responses:
            q = r.question
            response_details.append({
                "question_id": r.question_id,
                "question_text": q.question_text if q else None,
                "question_type": q.question_type if q else None,
                "options": q.options if q else [],
                "selected_answer": r.selected_answer,
                "correct_answer": q.correct_answer if q else None,
                "is_correct": r.is_correct,
                "explanation": q.explanation if q else None
            })

        return {
            "id": attempt.id,
            "quiz_id": attempt.quiz_id,
            "user_id": attempt.user_id,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "percentage": attempt.percentage,
            "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
            "responses": response_details
        }

    def list_user_history(self, user_id: int, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        Returns paginated attempt history for an authenticated user.
        """
        query = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.completed_at.desc())
        pagination = query.paginate(page=page, per_page=min(per_page, 100), error_out=False)

        attempts_list = []
        for att in pagination.items:
            attempts_list.append({
                "id": att.id,
                "quiz_id": att.quiz_id,
                "score": att.score,
                "total_questions": att.total_questions,
                "percentage": att.percentage,
                "completed_at": att.completed_at.isoformat() if att.completed_at else None,
                "quiz_type": att.quiz.quiz_type if att.quiz else "mixed",
                "difficulty": att.quiz.difficulty if att.quiz else "medium"
            })

        return {
            "attempts": attempts_list,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }


# Global attempt service instance
quiz_attempt_service = QuizAttemptService()

