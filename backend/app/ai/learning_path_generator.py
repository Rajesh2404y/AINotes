"""Adaptive Learning Path Generator.

Builds structured, sequential educational pathways tailored to user knowledge gaps
and available study materials (summaries, key takeaways, definitions, and quizzes).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.ai.adaptive_difficulty_service import adaptive_difficulty_service
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.learning_path import LearningPath, LearningPathActivity
from backend.app.models.quiz import Quiz
from backend.app.models.summary import Summary

logger = logging.getLogger(__name__)


class LearningPathGenerator:
    """Generates sequential milestone curriculum paths from user study assets."""

    def generate_path(
        self,
        user_id: int,
        target_topic: str,
        document_id: Optional[int] = None,
        summary_id: Optional[int] = None,
    ) -> LearningPath:
        """Constructs an adaptive 4-stage sequential learning path.

        Stages:
        1. Summary Ingestion & Overview (`summary_review`)
        2. Key Takeaways Study (`takeaways_study`)
        3. Technical Definitions & Terminology Drill (`definitions_review`)
        4. Adaptive Practice Assessment (`quiz_practice`)

        Args:
            user_id: Owner student ID.
            target_topic: Conceptual topic being addressed.
            document_id: Optional associated document ID.
            summary_id: Optional associated summary ID.

        Returns:
            LearningPath: Persisted learning path record with initialized child activities.
        """
        # Validate or discover associated resources
        doc = None
        summ = None

        if document_id:
            doc = db.session.get(Document, document_id)
            if doc and doc.user_id != user_id:
                doc = None

        if summary_id:
            summ = db.session.get(Summary, summary_id)
            if summ and summ.user_id != user_id:
                summ = None

        # Auto-link document if summary has one
        if summ and not doc and summ.document_id:
            doc = db.session.get(Document, summ.document_id)

        # Auto-link summary if doc has one
        if doc and not summ:
            summ = Summary.query.filter_by(document_id=doc.id, user_id=user_id).first()

        # If neither provided, find first user summary or document
        if not summ and not doc:
            summ = Summary.query.filter_by(user_id=user_id).first()
            if summ and summ.document_id:
                doc = db.session.get(Document, summ.document_id)

        # Compute recommended difficulty for the assessment stage
        diff_info = adaptive_difficulty_service.recommend_difficulty(user_id, topic=target_topic)
        rec_diff = diff_info["recommended_difficulty"]

        # Create Learning Path Entity
        clean_topic = target_topic.strip().title()
        title = f"Adaptive Path: {clean_topic} Mastery"
        description = (
            f"A structured, 4-stage reinforcement path designed to master {clean_topic}. "
            f"Includes conceptual reading, definition review, and a {rec_diff.capitalize()}-level practice quiz."
        )

        learning_path = LearningPath(
            user_id=user_id,
            title=title,
            description=description,
            target_topic=clean_topic,
            related_document_id=doc.id if doc else None,
            related_summary_id=summ.id if summ else None,
            status="not_started",
            progress_percentage=0.0,
        )
        db.session.add(learning_path)
        db.session.flush()  # Generates learning_path.id

        # Activity 1: Summary Review
        act1 = LearningPathActivity(
            learning_path_id=learning_path.id,
            activity_type="summary_review",
            activity_title=f"Review Conceptual Summary: {clean_topic}",
            resource_id=summ.id if summ else (doc.id if doc else None),
            sequence_number=1,
            status="pending",
        )

        # Activity 2: Key Takeaways Study
        act2 = LearningPathActivity(
            learning_path_id=learning_path.id,
            activity_type="takeaways_study",
            activity_title=f"Study Key Takeaways for {clean_topic}",
            resource_id=summ.id if summ else None,
            sequence_number=2,
            status="pending",
        )

        # Activity 3: Definitions Review
        act3 = LearningPathActivity(
            learning_path_id=learning_path.id,
            activity_type="definitions_review",
            activity_title=f"Revise Core Definitions & Formulae: {clean_topic}",
            resource_id=summ.id if summ else None,
            sequence_number=3,
            status="pending",
        )

        # Activity 4: Practice Quiz
        # Find existing quiz or register placeholder
        existing_quiz = None
        if summ:
            existing_quiz = Quiz.query.filter_by(summary_id=summ.id, user_id=user_id).first()
        elif doc:
            existing_quiz = Quiz.query.filter_by(document_id=doc.id, user_id=user_id).first()

        act4 = LearningPathActivity(
            learning_path_id=learning_path.id,
            activity_type="quiz_practice",
            activity_title=f"Attempt {rec_diff.capitalize()} Practice Assessment: {clean_topic}",
            resource_id=existing_quiz.id if existing_quiz else None,
            sequence_number=4,
            status="pending",
        )

        db.session.add_all([act1, act2, act3, act4])
        db.session.commit()

        return learning_path


# Singleton instance
learning_path_generator = LearningPathGenerator()

