"""Learning Progress Synchronization and Management Service.

Synchronizes computed topic accuracies and mastery statuses into the persistent
LearningProgress table, enabling fast index-based lookups and historic tracking.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.app.ai.learning_analysis_service import learning_analysis_service
from backend.app.extensions import db
from backend.app.models.learning_progress import LearningProgress

logger = logging.getLogger(__name__)


class LearningProgressService:
    """Synchronizes dynamic quiz analytics with persistent progress records."""

    def sync_user_progress(self, user_id: int) -> List[LearningProgress]:
        """Calculates latest performance and synchronizes learning_progress table.

        Args:
            user_id: Target student ID.

        Returns:
            List[LearningProgress]: Updated persistent records.
        """
        analysis = learning_analysis_service.analyze_user_learning(user_id)
        topic_perf = analysis.get("topic_performance", {})

        records = []
        for topic_name, data in topic_perf.items():
            record = LearningProgress.query.filter_by(user_id=user_id, topic=topic_name).first()
            if not record:
                record = LearningProgress(
                    user_id=user_id,
                    topic=topic_name,
                    attempted_questions=data["attempted_questions"],
                    correct_answers=data["correct_answers"],
                    accuracy=data["accuracy"],
                    performance_status=data["performance_status"],
                    last_attempted_at=datetime.fromisoformat(data["last_attempted_at"])
                    if data["last_attempted_at"]
                    else None,
                )
                db.session.add(record)
            else:
                record.attempted_questions = data["attempted_questions"]
                record.correct_answers = data["correct_answers"]
                record.accuracy = data["accuracy"]
                record.performance_status = data["performance_status"]
                if data["last_attempted_at"]:
                    record.last_attempted_at = datetime.fromisoformat(data["last_attempted_at"])
                record.updated_at = datetime.utcnow()
            records.append(record)

        db.session.commit()
        return records

    def get_topic_overview(self, user_id: int) -> Dict[str, Any]:
        """Returns consolidated learning analytics and topic distributions."""
        # Ensure latest sync
        self.sync_user_progress(user_id)
        analysis = learning_analysis_service.analyze_user_learning(user_id)

        # Derive recommended next action
        weak_topics = analysis.get("weak_topics", [])
        if weak_topics:
            top_weak = weak_topics[0]["topic"]
            next_action = {
                "action_type": "review_weak_topic",
                "title": f"Revise {top_weak}",
                "description": f"Accuracy is at {weak_topics[0]['accuracy']}%. Review summary notes and take an Easy practice quiz.",
                "topic": top_weak,
                "priority": "high",
            }
        elif analysis.get("total_quizzes_attempted", 0) == 0:
            next_action = {
                "action_type": "initial_assessment",
                "title": "Take Your First Quiz",
                "description": "Upload a note or generate a quiz to calibrate your learning profile.",
                "topic": "General",
                "priority": "medium",
            }
        else:
            next_action = {
                "action_type": "advance_curriculum",
                "title": "Explore Advanced Quizzes",
                "description": "Solid understanding across topics. Challenge yourself with Medium or Hard quizzes.",
                "topic": "Curriculum",
                "priority": "low",
            }

        return {
            "total_quizzes_attempted": analysis.get("total_quizzes_attempted", 0),
            "average_quiz_score": analysis.get("average_quiz_score", 0.0),
            "highest_quiz_score": analysis.get("highest_quiz_score", 0.0),
            "recent_performance": analysis.get("recent_performance", {}),
            "strong_topics": [t["topic"] for t in analysis.get("strong_topics", [])],
            "weak_topics": [t["topic"] for t in analysis.get("weak_topics", [])],
            "moderate_topics": [t["topic"] for t in analysis.get("moderate_topics", [])],
            "recommended_next_action": next_action,
        }


# Singleton instance
learning_progress_service = LearningProgressService()

