"""Recommendation Management and Query Service.

Coordinates recommendation lifecycle, pagination, priority filtering,
and status transitions (pending, in_progress, completed, dismissed).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.app.ai.recommendation_engine import recommendation_engine
from backend.app.extensions import db
from backend.app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class RecommendationServiceError(Exception):
    """Custom exception for recommendation service operations."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RecommendationService:
    """Manages recommendation generation, filtering, and status updates."""

    VALID_STATUSES = {"pending", "in_progress", "completed", "dismissed"}

    def get_recommendations(
        self,
        user_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Retrieves paginated recommendations for an authenticated student."""
        query = Recommendation.query.filter_by(user_id=user_id)

        if status:
            norm_status = status.lower().strip()
            if norm_status in self.VALID_STATUSES:
                query = query.filter_by(status=norm_status)

        if priority:
            norm_priority = priority.lower().strip()
            if norm_priority in {"high", "medium", "low"}:
                query = query.filter_by(priority=norm_priority)

        # Order by priority weight then creation recency
        query = query.order_by(
            db.case(
                (Recommendation.priority == "high", 1),
                (Recommendation.priority == "medium", 2),
                else_=3,
            ),
            Recommendation.created_at.desc(),
        )

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        items = [r.to_dict() for r in paginated.items]

        pagination = {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total_items": paginated.total,
            "total_pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        }
        return items, pagination

    def generate_user_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """Triggers recommendation generation engine and returns active items."""
        recs = recommendation_engine.generate_recommendations(user_id)
        return [r.to_dict() for r in recs]

    def update_recommendation_status(
        self,
        user_id: int,
        recommendation_id: int,
        new_status: str,
    ) -> Dict[str, Any]:
        """Updates the status of a specific recommendation with strict ownership check."""
        rec = db.session.get(Recommendation, recommendation_id)
        if not rec:
            raise RecommendationServiceError(
                f"Recommendation with ID {recommendation_id} not found.", 404
            )
        if rec.user_id != user_id:
            raise RecommendationServiceError(
                "You do not have permission to modify this recommendation.", 403
            )

        norm_status = new_status.lower().strip()
        if norm_status not in self.VALID_STATUSES:
            raise RecommendationServiceError(
                f"Invalid status '{new_status}'. Allowed: {sorted(list(self.VALID_STATUSES))}", 400
            )

        rec.status = norm_status
        if norm_status == "completed":
            rec.completed_at = datetime.utcnow()
        elif norm_status == "pending":
            rec.completed_at = None

        db.session.commit()
        return rec.to_dict()


# Singleton instance
recommendation_service = RecommendationService()

