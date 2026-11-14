"""Adaptive Difficulty Recommendation Engine.

Evaluates student mastery levels and learning velocity to recommend optimal
cognitive difficulty tiers (Easy, Medium, Hard) without forcing rigid changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.app.ai.learning_analysis_service import learning_analysis_service
from backend.app.utils.learning_metrics import recommend_adaptive_difficulty

logger = logging.getLogger(__name__)


class AdaptiveDifficultyService:
    """Computes transparent, data-grounded quiz difficulty recommendations."""

    def recommend_difficulty(
        self,
        user_id: int,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates recommended quiz difficulty tier for a topic or overall student profile.

        Args:
            user_id: Student identifier.
            topic: Optional target topic. If None, uses overall quiz performance.

        Returns:
            Dict containing recommended difficulty tier, metric values, and clear justification.
        """
        analysis = learning_analysis_service.analyze_user_learning(user_id)

        if topic and topic in analysis.get("topic_performance", {}):
            t_data = analysis["topic_performance"][topic]
            acc = t_data["accuracy"]
            att = t_data["attempted_questions"]
            target_label = topic
        else:
            acc = analysis.get("average_quiz_score", 0.0)
            att = analysis.get("total_quizzes_attempted", 0)
            target_label = "Overall Curriculum"

        rec_tier, reason = recommend_adaptive_difficulty(
            topic_accuracy=acc,
            attempts=att,
            min_attempts=learning_analysis_service.min_attempts,
        )

        confidence = "high" if att >= 5 else ("moderate" if att >= 3 else "low")

        return {
            "recommended_difficulty": rec_tier,
            "target": target_label,
            "accuracy": acc,
            "attempts": att,
            "reason": reason,
            "confidence": confidence,
            "suggested_actions": [
                f"Practice {rec_tier.capitalize()} level assessments to maximize retention.",
                "Review corresponding study notes before advancing to the next tier.",
            ],
        }


# Singleton instance
adaptive_difficulty_service = AdaptiveDifficultyService()

