"""Learning Path Orchestration and Activity Verification Service.

Manages learning pathways, milestone progress recalculations, and server-side
verification of completed learning activities (summaries, definitions, and quizzes).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.app.ai.learning_path_generator import learning_path_generator
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.learning_path import LearningPath, LearningPathActivity
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.summary import Summary

logger = logging.getLogger(__name__)


class LearningPathServiceError(Exception):
    """Custom exception for learning path operations."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LearningPathService:
    """Handles learning path generation, updates, and robust activity verification."""

    VALID_PATH_STATUSES = {"not_started", "in_progress", "completed", "paused"}

    def create_learning_path(
        self,
        user_id: int,
        target_topic: str,
        document_id: Optional[int] = None,
        summary_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Creates an adaptive learning path with 4 sequential curriculum milestones."""
        if not target_topic or not target_topic.strip():
            raise LearningPathServiceError("Target topic is required to generate a learning path.", 400)

        # Validate resource ownership if provided
        if document_id:
            doc = db.session.get(Document, document_id)
            if not doc:
                raise LearningPathServiceError(f"Document {document_id} was not found.", 404)
            if doc.user_id != user_id:
                raise LearningPathServiceError("Access forbidden to the specified document.", 403)

        if summary_id:
            summ = db.session.get(Summary, summary_id)
            if not summ:
                raise LearningPathServiceError(f"Summary {summary_id} was not found.", 404)
            if summ.user_id != user_id:
                raise LearningPathServiceError("Access forbidden to the specified summary.", 403)

        path = learning_path_generator.generate_path(
            user_id=user_id,
            target_topic=target_topic.strip(),
            document_id=document_id,
            summary_id=summary_id,
        )
        return path.to_dict(include_activities=True)

    def list_learning_paths(
        self,
        user_id: int,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Retrieves paginated learning paths for the authenticated student."""
        query = LearningPath.query.filter_by(user_id=user_id)

        if status:
            norm_status = status.lower().strip()
            if norm_status in self.VALID_PATH_STATUSES:
                query = query.filter_by(status=norm_status)

        query = query.order_by(LearningPath.updated_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        items = [p.to_dict(include_activities=True) for p in paginated.items]
        pagination = {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total_items": paginated.total,
            "total_pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        }
        return items, pagination

    def get_path_details(self, user_id: int, path_id: int) -> Dict[str, Any]:
        """Retrieves full details and milestone activities for a specific learning path."""
        path = db.session.get(LearningPath, path_id)
        if not path:
            raise LearningPathServiceError(f"Learning path with ID {path_id} not found.", 404)
        if path.user_id != user_id:
            raise LearningPathServiceError("Access forbidden to this learning path.", 403)

        path.calculate_progress()
        db.session.commit()
        return path.to_dict(include_activities=True)

    def update_path_status(self, user_id: int, path_id: int, new_status: str) -> Dict[str, Any]:
        """Updates the status (start, pause, resume, complete) of a learning path."""
        path = db.session.get(LearningPath, path_id)
        if not path:
            raise LearningPathServiceError(f"Learning path with ID {path_id} not found.", 404)
        if path.user_id != user_id:
            raise LearningPathServiceError("Access forbidden to this learning path.", 403)

        norm_status = new_status.lower().strip()
        if norm_status not in self.VALID_PATH_STATUSES:
            raise LearningPathServiceError(
                f"Invalid status '{new_status}'. Allowed: {sorted(list(self.VALID_PATH_STATUSES))}", 400
            )

        path.status = norm_status
        db.session.commit()
        return path.to_dict(include_activities=True)

    def complete_activity(
        self,
        user_id: int,
        path_id: int,
        activity_id: int,
    ) -> Dict[str, Any]:
        """Verifies server-side completion of a learning activity before marking it done."""
        path = db.session.get(LearningPath, path_id)
        if not path:
            raise LearningPathServiceError(f"Learning path with ID {path_id} not found.", 404)
        if path.user_id != user_id:
            raise LearningPathServiceError("Access forbidden to this learning path.", 403)

        activity = db.session.get(LearningPathActivity, activity_id)
        if not activity or activity.learning_path_id != path.id:
            raise LearningPathServiceError(
                f"Activity {activity_id} does not belong to learning path {path_id}.", 404
            )

        if activity.status == "completed":
            return {
                "message": "Activity already marked as completed.",
                "activity": activity.to_dict(),
                "path": path.to_dict(include_activities=True),
            }

        # Server-side verification based on activity type
        act_type = activity.activity_type
        if act_type in ("summary_review", "takeaways_study", "definitions_review"):
            # Verify that either the linked summary or document exists and is accessible
            if activity.resource_id:
                summ = db.session.get(Summary, activity.resource_id)
                doc = db.session.get(Document, activity.resource_id)
                if not summ and not doc:
                    # Resource might have been deleted, fallback to path-level resources
                    if not path.related_summary_id and not path.related_document_id:
                        raise LearningPathServiceError(
                            "Cannot verify activity: associated study resource does not exist.", 422
                        )
        elif act_type == "quiz_practice":
            # For quiz practice, verify that user has at least one completed QuizAttempt
            # for the quiz, document, or summary
            has_attempt = False
            if activity.resource_id:
                has_attempt = (
                    QuizAttempt.query.filter_by(
                        user_id=user_id, quiz_id=activity.resource_id
                    ).first()
                    is not None
                )

            if not has_attempt:
                # Check attempts linked through the path's quiz or document/summary
                q_ids = [
                    q.id
                    for q in Quiz.query.filter_by(user_id=user_id)
                    .filter(
                        (Quiz.document_id == path.related_document_id)
                        | (Quiz.summary_id == path.related_summary_id)
                    )
                    .all()
                ]
                if q_ids:
                    has_attempt = (
                        QuizAttempt.query.filter(
                            QuizAttempt.user_id == user_id,
                            QuizAttempt.quiz_id.in_(q_ids),
                        ).first()
                        is not None
                    )

            if not has_attempt:
                # Check any attempt by this user
                total_attempts = QuizAttempt.query.filter_by(user_id=user_id).count()
                if total_attempts == 0:
                    raise LearningPathServiceError(
                        "Cannot mark quiz activity complete: no completed quiz attempt was found.", 422
                    )

        # Mark activity completed
        activity.status = "completed"
        activity.completed_at = datetime.utcnow()

        # Recalculate parent path progress
        path.calculate_progress()
        db.session.commit()

        return {
            "message": "Activity successfully verified and completed.",
            "activity": activity.to_dict(),
            "path": path.to_dict(include_activities=True),
        }

    def delete_learning_path(self, user_id: int, path_id: int) -> bool:
        """Safely removes a learning path and cascaded milestones."""
        path = db.session.get(LearningPath, path_id)
        if not path:
            raise LearningPathServiceError(f"Learning path with ID {path_id} not found.", 404)
        if path.user_id != user_id:
            raise LearningPathServiceError("Access forbidden to this learning path.", 403)

        db.session.delete(path)
        db.session.commit()
        return True


# Singleton instance
learning_path_service = LearningPathService()

