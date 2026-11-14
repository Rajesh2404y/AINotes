"""Weak and Strong Topic Detection Service.

Identifies knowledge gaps, declining learning trajectories, consistent strengths,
and recurring mistakes using configurable accuracy thresholds.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class WeakTopicDetectionService:
    """Classifies learning performance gaps and strengths with transparent justifications."""

    def detect_topic_classifications(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts prioritized deficit and strength classifications from learning analysis.

        Args:
            analysis: Result dictionary from learning_analysis_service.analyze_user_learning().

        Returns:
            Dict containing categorized topics, declining topics, improving topics,
            and recurring mistakes.
        """
        weak_topics = analysis.get("weak_topics", [])
        moderate_topics = analysis.get("moderate_topics", [])
        good_topics = analysis.get("good_topics", [])
        strong_topics = analysis.get("strong_topics", [])
        insufficient_topics = analysis.get("insufficient_data_topics", [])

        all_topics = analysis.get("topic_performance", {})

        # Identify topics with declining and improving trends
        declining_topics = []
        improving_topics = []
        for topic_name, data in all_topics.items():
            if data.get("trend") == "declining":
                declining_topics.append({
                    "topic": topic_name,
                    "accuracy": data["accuracy"],
                    "reason": f"Performance in '{topic_name}' has dropped by more than 8% in recent attempts.",
                    "related_document_id": data.get("related_document_id"),
                    "related_summary_id": data.get("related_summary_id"),
                })
            elif data.get("trend") == "improving":
                improving_topics.append({
                    "topic": topic_name,
                    "accuracy": data["accuracy"],
                    "reason": f"Performance in '{topic_name}' shows an upward trajectory of over 8% in recent attempts.",
                })

        return {
            "weak_topics": weak_topics,
            "moderate_topics": moderate_topics,
            "good_topics": good_topics,
            "strong_topics": strong_topics,
            "insufficient_data_topics": insufficient_topics,
            "declining_topics": declining_topics,
            "improving_topics": improving_topics,
            "has_deficits": len(weak_topics) > 0 or len(declining_topics) > 0,
            "repeated_mistakes": analysis.get("repeated_incorrect_count", 0),
        }


# Singleton instance
weak_topic_detection_service = WeakTopicDetectionService()

