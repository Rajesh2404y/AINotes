"""Personalized Learning Recommendation Engine.

Generates explainable, prioritized educational recommendations grounded strictly in
real quiz attempts, topic performance metrics, and available study resources.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.ai.adaptive_difficulty_service import adaptive_difficulty_service
from backend.app.ai.learning_analysis_service import learning_analysis_service
from backend.app.ai.weak_topic_detection import weak_topic_detection_service
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.learning_path import LearningPath
from backend.app.models.quiz import Quiz
from backend.app.models.recommendation import Recommendation
from backend.app.models.summary import Summary

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Synthesizes actionable, explainable learning recommendations based on actual user data."""

    def generate_recommendations(self, user_id: int) -> List[Recommendation]:
        """Generates and persists personalized recommendations for an authenticated student.

        Args:
            user_id: Primary key of authenticated student.

        Returns:
            List[Recommendation]: Newly generated and existing active recommendations.
        """
        analysis = learning_analysis_service.analyze_user_learning(user_id)
        classifications = weak_topic_detection_service.detect_topic_classifications(analysis)

        # Existing active recommendations for duplicate prevention
        existing_recs = Recommendation.query.filter_by(
            user_id=user_id, status="pending"
        ).all()
        existing_keys = {(r.topic, r.recommendation_type) for r in existing_recs}

        new_recs: List[Recommendation] = []

        # 1. Check for Incomplete Active Learning Paths
        active_path = (
            LearningPath.query.filter_by(user_id=user_id)
            .filter(LearningPath.status.in_(["in_progress", "not_started"]))
            .first()
        )
        if active_path and (active_path.target_topic, "continue_path") not in existing_keys:
            rec = Recommendation(
                user_id=user_id,
                topic=active_path.target_topic,
                recommendation_type="continue_path",
                title=f"Continue Learning Path: {active_path.title}",
                description=f"You have an ongoing learning path on '{active_path.target_topic}' at {active_path.progress_percentage}% completion.",
                suggested_action="Resume your sequential milestone activities to complete this module.",
                reason=f"Learning path '{active_path.title}' is currently {active_path.status} with uncompleted milestones.",
                related_document_id=active_path.related_document_id,
                related_summary_id=active_path.related_summary_id,
                priority="high",
                status="pending",
            )
            db.session.add(rec)
            new_recs.append(rec)
            existing_keys.add((active_path.target_topic, "continue_path"))

        # 2. Insufficient Data Scenario
        if analysis.get("total_quizzes_attempted", 0) == 0:
            if ("General", "insufficient_data") not in existing_keys:
                # Find any available document or summary to recommend
                first_doc = Document.query.filter_by(user_id=user_id).first()
                first_summary = Summary.query.filter_by(user_id=user_id).first()
                rec = Recommendation(
                    user_id=user_id,
                    topic="General",
                    recommendation_type="insufficient_data",
                    title="Attempt an Initial Assessment",
                    description="No quiz attempts have been recorded yet. Complete an initial quiz to unlock personalized analytics.",
                    suggested_action="Generate a quiz from one of your uploaded notes or summaries to calibrate your proficiency.",
                    reason="At least one completed quiz attempt is required to evaluate topic mastery and strengths.",
                    related_document_id=first_doc.id if first_doc else None,
                    related_summary_id=first_summary.id if first_summary else None,
                    priority="medium",
                    status="pending",
                )
                db.session.add(rec)
                new_recs.append(rec)
                existing_keys.add(("General", "insufficient_data"))

        # 3. Weak Topics (Needs Improvement) -> High Priority
        for w in classifications.get("weak_topics", []):
            topic = w["topic"]
            if (topic, "retry_weak_topic") not in existing_keys:
                rec = Recommendation(
                    user_id=user_id,
                    topic=topic,
                    recommendation_type="retry_weak_topic",
                    title=f"Targeted Revision: {topic}",
                    description=f"Review summary notes and re-attempt practice quizzes on {topic}.",
                    suggested_action="Study key takeaways and take an Easy practice quiz to rebuild conceptual fundamentals.",
                    reason=f"Your accuracy was {w['accuracy']}% across {w['attempted_questions']} questions, which is below the 50% weak-topic threshold.",
                    related_document_id=w.get("related_document_id"),
                    related_summary_id=w.get("related_summary_id"),
                    related_quiz_id=w.get("related_quiz_id"),
                    priority="high",
                    status="pending",
                )
                db.session.add(rec)
                new_recs.append(rec)
                existing_keys.add((topic, "retry_weak_topic"))

        # 4. Declining Topics -> High Priority
        for d in classifications.get("declining_topics", []):
            topic = d["topic"]
            if (topic, "revisit_document") not in existing_keys:
                rec = Recommendation(
                    user_id=user_id,
                    topic=topic,
                    recommendation_type="revisit_document",
                    title=f"Reinforce Retention: {topic}",
                    description=f"Recent scores in {topic} indicate decreasing retention.",
                    suggested_action="Revisit source notes and complete a targeted quiz review.",
                    reason=d["reason"],
                    related_document_id=d.get("related_document_id"),
                    related_summary_id=d.get("related_summary_id"),
                    priority="high",
                    status="pending",
                )
                db.session.add(rec)
                new_recs.append(rec)
                existing_keys.add((topic, "revisit_document"))

        # 5. Moderate Topics (Developing) -> Medium Priority
        for m in classifications.get("moderate_topics", []):
            topic = m["topic"]
            if (topic, "review_definitions") not in existing_keys:
                rec = Recommendation(
                    user_id=user_id,
                    topic=topic,
                    recommendation_type="review_definitions",
                    title=f"Consolidate Concepts: {topic}",
                    description=f"Refine technical terminology and practice Medium difficulty questions for {topic}.",
                    suggested_action="Revise definition cards and attempt another Medium quiz.",
                    reason=f"Your accuracy is {m['accuracy']}% across {m['attempted_questions']} questions, showing developing comprehension.",
                    related_document_id=m.get("related_document_id"),
                    related_summary_id=m.get("related_summary_id"),
                    related_quiz_id=m.get("related_quiz_id"),
                    priority="medium",
                    status="pending",
                )
                db.session.add(rec)
                new_recs.append(rec)
                existing_keys.add((topic, "review_definitions"))

        # 6. Strong Topics (Strong) -> Low Priority (Enrichment/Challenge)
        for s in classifications.get("strong_topics", []):
            topic = s["topic"]
            if (topic, "advanced_quiz") not in existing_keys:
                rec = Recommendation(
                    user_id=user_id,
                    topic=topic,
                    recommendation_type="advanced_quiz",
                    title=f"Advanced Challenge: {topic}",
                    description=f"You demonstrate strong mastery in {topic}. Test yourself with Hard analytical questions.",
                    suggested_action="Generate and complete a Hard difficulty quiz with multi-concept questions.",
                    reason=f"Outstanding accuracy of {s['accuracy']}% across {s['attempted_questions']} questions exceeds the 85% mastery threshold.",
                    related_document_id=s.get("related_document_id"),
                    related_summary_id=s.get("related_summary_id"),
                    related_quiz_id=s.get("related_quiz_id"),
                    priority="low",
                    status="pending",
                )
                db.session.add(rec)
                new_recs.append(rec)
                existing_keys.add((topic, "advanced_quiz"))

        if new_recs:
            db.session.commit()

        # Return all pending recommendations for the user
        return (
            Recommendation.query.filter_by(user_id=user_id, status="pending")
            .order_by(
                db.case(
                    (Recommendation.priority == "high", 1),
                    (Recommendation.priority == "medium", 2),
                    else_=3,
                ),
                Recommendation.created_at.desc(),
            )
            .all()
        )


# Singleton instance
recommendation_engine = RecommendationEngine()

