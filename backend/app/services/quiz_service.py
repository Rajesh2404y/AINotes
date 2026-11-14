"""
Quiz Management Service.
Handles quiz generation orchestration, document/summary sourcing, persistence,
retrieval, and ownership checks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.app.ai.question_generation_service import question_generation_service
from backend.app.ai.quiz_quality_service import quiz_quality_service
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.question import Question
from backend.app.models.quiz import Quiz
from backend.app.models.summary import Summary

logger = logging.getLogger(__name__)


class QuizServiceError(Exception):
    """Custom exception for quiz service operations."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuizService:
    """Manages quiz creation, database persistence, and retrieval."""

    def create_quiz(
        self,
        user_id: int,
        document_id: Optional[int] = None,
        summary_id: Optional[int] = None,
        question_types: Optional[List[str]] = None,
        difficulty: str = "medium",
        total_questions: int = 10
    ) -> Quiz:
        """
        Creates a new quiz session by generating questions from user's document or summary.
        """
        if not document_id and not summary_id:
            raise QuizServiceError("Either 'document_id' or 'summary_id' must be provided.", 400)

        # 1. Fetch source and verify ownership
        source_text = ""
        source_ref = ""
        target_doc = None
        target_summary = None

        if document_id:
            target_doc = db.session.get(Document, document_id)
            if not target_doc:
                raise QuizServiceError(f"Document with ID {document_id} was not found.", 404)
            if target_doc.user_id != user_id:
                raise QuizServiceError("You do not have permission to access this document.", 403)
            doc_text = target_doc.cleaned_text or target_doc.extracted_text or ""
            source_text += doc_text + "\n\n"
            source_ref = f"Document: {target_doc.original_filename}"

        if summary_id:
            target_summary = db.session.get(Summary, summary_id)
            if not target_summary:
                raise QuizServiceError(f"Summary with ID {summary_id} was not found.", 404)
            if target_summary.user_id != user_id:
                raise QuizServiceError("You do not have permission to access this summary.", 403)
            summary_content = target_summary.summary_text or ""
            source_text += summary_content
            if not source_ref:
                source_ref = f"Summary ID: {summary_id}"

        source_text = source_text.strip()
        if not source_text or len(source_text) < 40:
            raise QuizServiceError(
                "The selected study material contains insufficient text to generate quiz questions.", 422
            )

        # 2. Check source sufficiency
        is_sufficient, reason = quiz_quality_service.assess_source_sufficiency(source_text, total_questions)
        if not is_sufficient and len(source_text.split()) < max(40, total_questions * 8):
            raise QuizServiceError(reason or f"Insufficient source content to generate {total_questions} questions.", 422)

        # 3. Constrain total questions
        clamped_total = max(1, min(total_questions, 50))

        # 4. Generate Questions
        generated_questions = question_generation_service.generate_quiz_questions(
            source_text=source_text,
            question_types=question_types,
            difficulty=difficulty,
            total_questions=clamped_total,
            source_reference=source_ref
        )

        if not generated_questions:
            raise QuizServiceError(
                "Could not generate valid assessment questions from the provided content.", 500
            )

        # If source content is too limited to yield the requested count, report explicit error
        if len(generated_questions) < clamped_total and len(source_text.split()) < clamped_total * 10:
            raise QuizServiceError(
                f"Source document contains insufficient content to generate all {clamped_total} requested questions without repetition. Only {len(generated_questions)} valid questions could be formulated.",
                422
            )

        # 5. Persist Quiz and Questions
        # Determine quiz_type label
        if not question_types or len(question_types) > 1:
            quiz_type_label = "mixed"
        else:
            quiz_type_label = question_types[0]

        quiz = Quiz(
            user_id=user_id,
            document_id=target_doc.id if target_doc else None,
            summary_id=target_summary.id if target_summary else None,
            quiz_type=quiz_type_label,
            difficulty=difficulty.lower(),
            total_questions=len(generated_questions)
        )
        db.session.add(quiz)
        db.session.flush()  # Populates quiz.id

        for q_data in generated_questions:
            question = Question(
                quiz_id=quiz.id,
                question_text=q_data["question_text"],
                question_type=q_data["question_type"],
                options=q_data.get("options"),
                correct_answer=str(q_data["correct_answer"]),
                explanation=q_data.get("explanation"),
                source_reference=q_data.get("source_reference", source_ref)
            )
            db.session.add(question)

        db.session.commit()
        logger.info("Successfully created quiz id=%d with %d questions", quiz.id, len(generated_questions))
        return quiz

    def get_quiz_for_user(self, quiz_id: int, user_id: int, include_answers: bool = False) -> Quiz:
        """
        Retrieves a quiz ensuring cross-user access restrictions.
        """
        quiz = db.session.get(Quiz, quiz_id)
        if not quiz:
            raise QuizServiceError(f"Quiz with ID {quiz_id} was not found.", 404)
        if quiz.user_id != user_id:
            raise QuizServiceError("You do not have permission to view this quiz.", 403)
        return quiz

    def list_quizzes(
        self,
        user_id: int,
        document_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        quiz_type: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Returns a paginated list of quizzes for the given user.
        """
        query = Quiz.query.filter_by(user_id=user_id)
        if document_id:
            query = query.filter_by(document_id=document_id)
        if difficulty:
            query = query.filter_by(difficulty=difficulty.lower())
        if quiz_type:
            query = query.filter_by(quiz_type=quiz_type.lower())

        query = query.order_by(Quiz.created_at.desc())
        pagination = query.paginate(page=page, per_page=min(per_page, 100), error_out=False)

        return {
            "quizzes": [q.to_dict(include_questions=False) for q in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }

    def delete_quiz(self, quiz_id: int, user_id: int) -> bool:
        """
        Deletes a quiz along with associated questions and attempts.
        """
        quiz = self.get_quiz_for_user(quiz_id, user_id)
        db.session.delete(quiz)
        db.session.commit()
        return True


# Global service instance
quiz_service = QuizService()

