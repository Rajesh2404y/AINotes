"""Learning Performance Analysis and Topic Mapping Engine.

Analyzes real quiz attempts, responses, and questions to derive topic-level accuracy,
cognitive difficulty breakdown, question type performance, and longitudinal learning trends.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.question import Question
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.quiz_response import QuizResponse
from backend.app.models.summary import Summary
from backend.app.utils.learning_metrics import (
    calculate_accuracy,
    calculate_trend,
    classify_topic_status,
)

logger = logging.getLogger(__name__)


class LearningAnalysisService:
    """Evaluates user learning metrics grounded in actual database records."""

    def __init__(self):
        self.weak_threshold = float(os.getenv("WEAK_TOPIC_THRESHOLD", 50.0))
        self.moderate_threshold = float(os.getenv("MODERATE_TOPIC_THRESHOLD", 70.0))
        self.strong_threshold = float(os.getenv("STRONG_TOPIC_THRESHOLD", 85.0))
        self.min_attempts = int(os.getenv("MIN_ATTEMPTS_FOR_CLASSIFICATION", 3))

    def map_question_to_topic(
        self,
        question: Question,
        quiz: Optional[Quiz] = None,
        summary: Optional[Summary] = None,
        document: Optional[Document] = None,
    ) -> str:
        """Deterministically maps an assessment question to a conceptual topic.

        Hierarchy:
        1. Exact keyword or definition term match from the source Summary.
        2. Document Title or sanitized original filename.
        3. Structured question source reference metadata.
        4. Fallback to 'General Concepts' if unmapped.

        Returns:
            str: Resolved topic name.
        """
        if not question:
            return "Unknown"

        q_quiz = quiz or question.quiz
        q_summary = summary or (q_quiz.summary if q_quiz else None)
        q_document = document or (q_quiz.document if q_quiz else None)

        text = (question.question_text or "").lower()

        # 1. Match against Summary definitions and keywords
        if q_summary:
            # Check definitions first (high semantic value)
            if q_summary.definitions and isinstance(q_summary.definitions, list):
                for item in q_summary.definitions:
                    if isinstance(item, dict) and "term" in item:
                        term = str(item["term"]).strip()
                        if term and len(term) >= 3:
                            pattern = rf"\b{re.escape(term.lower())}\b"
                            if re.search(pattern, text):
                                return term.title()

            # Check extracted keywords
            if q_summary.keywords and isinstance(q_summary.keywords, list):
                for kw in q_summary.keywords:
                    kw_str = str(kw).strip()
                    if kw_str and len(kw_str) >= 3:
                        pattern = rf"\b{re.escape(kw_str.lower())}\b"
                        if re.search(pattern, text):
                            return kw_str.title()

        # 2. Match against Document title or filename
        if q_document:
            doc_title = getattr(q_document, "title", None)
            if doc_title and doc_title.strip():
                return doc_title.strip()
            if q_document.original_filename:
                # Sanitize filename: remove extension, replace delimiters with spaces
                raw_name = os.path.splitext(q_document.original_filename)[0]
                clean_name = re.sub(r"[_\-\.]+", " ", raw_name).strip().title()
                if clean_name:
                    return clean_name

        # 3. Match against question source_reference
        if question.source_reference:
            ref = question.source_reference.strip()
            if ref.startswith("Document:"):
                raw_doc = ref.replace("Document:", "").strip()
                cleaned = os.path.splitext(raw_doc)[0]
                cleaned = re.sub(r"[_\-\.]+", " ", cleaned).strip().title()
                if cleaned:
                    return cleaned
            elif not ref.lower().startswith("document sentence context") and len(ref) > 3:
                return ref.title()

        return "General Concepts"

    def analyze_user_learning(self, user_id: int) -> Dict[str, Any]:
        """Performs comprehensive multi-dimensional learning analysis for a user.

        Args:
            user_id: Primary key of authenticated student.

        Returns:
            Dict containing holistic metrics, topic breakdowns, difficulty distribution,
            question-type accuracy, and identified learning deficits.
        """
        # Fetch all completed attempts in chronological sequence
        attempts = (
            QuizAttempt.query.filter_by(user_id=user_id)
            .order_by(QuizAttempt.completed_at.asc())
            .all()
        )

        if not attempts:
            return {
                "total_quizzes_attempted": 0,
                "average_quiz_score": 0.0,
                "highest_quiz_score": 0.0,
                "recent_performance": {
                    "scores": [],
                    "average": 0.0,
                    "trend": "insufficient_data",
                },
                "topic_performance": {},
                "difficulty_performance": {
                    "easy": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                    "medium": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                    "hard": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                },
                "question_type_performance": {
                    "mcq": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                    "true_false": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                    "one_word": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                    "fill_blank": {"attempted": 0, "correct": 0, "accuracy": 0.0},
                },
                "weak_topics": [],
                "moderate_topics": [],
                "good_topics": [],
                "strong_topics": [],
                "insufficient_data_topics": [],
                "repeated_incorrect_count": 0,
            }

        attempt_percentages = [float(a.percentage) for a in attempts]
        avg_score = round(sum(attempt_percentages) / len(attempt_percentages), 2)
        highest_score = round(max(attempt_percentages), 2)

        # Recent 5 attempts
        recent_5 = attempt_percentages[-5:]
        recent_avg = round(sum(recent_5) / len(recent_5), 2)
        overall_trend = calculate_trend(attempt_percentages)

        # Topic aggregation data structures
        topic_data: Dict[str, Dict[str, Any]] = {}
        difficulty_data = {
            "easy": {"attempted": 0, "correct": 0},
            "medium": {"attempted": 0, "correct": 0},
            "hard": {"attempted": 0, "correct": 0},
        }
        type_data = {
            "mcq": {"attempted": 0, "correct": 0},
            "true_false": {"attempted": 0, "correct": 0},
            "one_word": {"attempted": 0, "correct": 0},
            "fill_blank": {"attempted": 0, "correct": 0},
        }

        # Track question-level failure counts for recurring mistakes
        question_failures: Dict[int, int] = {}
        associated_doc_ids: Dict[str, Optional[int]] = {}
        associated_summary_ids: Dict[str, Optional[int]] = {}
        associated_quiz_ids: Dict[str, Optional[int]] = {}

        for attempt in attempts:
            quiz = attempt.quiz
            # Load all responses in this attempt
            responses = QuizResponse.query.filter_by(attempt_id=attempt.id).all()
            for resp in responses:
                q = resp.question
                if not q:
                    continue

                topic = self.map_question_to_topic(q, quiz=quiz)

                if topic not in topic_data:
                    topic_data[topic] = {
                        "attempted_questions": 0,
                        "correct_answers": 0,
                        "scores": [],
                        "last_attempted_at": None,
                    }
                    associated_doc_ids[topic] = quiz.document_id if quiz else None
                    associated_summary_ids[topic] = quiz.summary_id if quiz else None
                    associated_quiz_ids[topic] = quiz.id if quiz else None

                topic_data[topic]["attempted_questions"] += 1
                topic_data[topic]["last_attempted_at"] = (
                    attempt.completed_at.isoformat() if attempt.completed_at else None
                )

                if resp.is_correct:
                    topic_data[topic]["correct_answers"] += 1
                    topic_data[topic]["scores"].append(100.0)
                else:
                    topic_data[topic]["scores"].append(0.0)
                    question_failures[q.id] = question_failures.get(q.id, 0) + 1

                # Difficulty breakdown
                diff = (quiz.difficulty if quiz and quiz.difficulty else "medium").lower()
                if diff in difficulty_data:
                    difficulty_data[diff]["attempted"] += 1
                    if resp.is_correct:
                        difficulty_data[diff]["correct"] += 1

                # Question type breakdown
                q_type = (q.question_type or "mcq").lower()
                if q_type == "true_false" or q_type == "true/false":
                    norm_type = "true_false"
                elif q_type in ("one_word", "oneword"):
                    norm_type = "one_word"
                elif q_type in ("fill_blank", "fill_in_the_blank", "fill_in_blank"):
                    norm_type = "fill_blank"
                else:
                    norm_type = "mcq"

                if norm_type in type_data:
                    type_data[norm_type]["attempted"] += 1
                    if resp.is_correct:
                        type_data[norm_type]["correct"] += 1

        # Classify each topic
        classified_topics: Dict[str, Dict[str, Any]] = {}
        weak_topics: List[Dict[str, Any]] = []
        moderate_topics: List[Dict[str, Any]] = []
        good_topics: List[Dict[str, Any]] = []
        strong_topics: List[Dict[str, Any]] = []
        insufficient_topics: List[Dict[str, Any]] = []

        for topic_name, metrics in topic_data.items():
            att = metrics["attempted_questions"]
            corr = metrics["correct_answers"]
            acc = calculate_accuracy(corr, att)
            status, reason = classify_topic_status(
                acc,
                att,
                min_attempts=self.min_attempts,
                weak_threshold=self.weak_threshold,
                moderate_threshold=self.moderate_threshold,
                strong_threshold=self.strong_threshold,
            )
            t_trend = calculate_trend(metrics["scores"])

            entry = {
                "topic": topic_name,
                "attempted_questions": att,
                "correct_answers": corr,
                "accuracy": acc,
                "performance_status": status,
                "trend": t_trend,
                "reason": reason,
                "last_attempted_at": metrics["last_attempted_at"],
                "related_document_id": associated_doc_ids.get(topic_name),
                "related_summary_id": associated_summary_ids.get(topic_name),
                "related_quiz_id": associated_quiz_ids.get(topic_name),
            }
            classified_topics[topic_name] = entry

            if status == "Needs Improvement":
                weak_topics.append(entry)
            elif status == "Developing":
                moderate_topics.append(entry)
            elif status == "Good":
                good_topics.append(entry)
            elif status == "Strong":
                strong_topics.append(entry)
            else:
                insufficient_topics.append(entry)

        # Count repeated incorrect answers (failed >= 2 times)
        repeated_mistakes = sum(1 for count in question_failures.values() if count >= 2)

        # Final difficulty metrics
        diff_perf = {}
        for d_key, d_vals in difficulty_data.items():
            diff_perf[d_key] = {
                "attempted": d_vals["attempted"],
                "correct": d_vals["correct"],
                "accuracy": calculate_accuracy(d_vals["correct"], d_vals["attempted"]),
            }

        # Final question-type metrics
        type_perf = {}
        for t_key, t_vals in type_data.items():
            type_perf[t_key] = {
                "attempted": t_vals["attempted"],
                "correct": t_vals["correct"],
                "accuracy": calculate_accuracy(t_vals["correct"], t_vals["attempted"]),
            }

        return {
            "total_quizzes_attempted": len(attempts),
            "average_quiz_score": avg_score,
            "highest_quiz_score": highest_score,
            "recent_performance": {
                "scores": recent_5,
                "average": recent_avg,
                "trend": overall_trend,
            },
            "topic_performance": classified_topics,
            "difficulty_performance": diff_perf,
            "question_type_performance": type_perf,
            "weak_topics": weak_topics,
            "moderate_topics": moderate_topics,
            "good_topics": good_topics,
            "strong_topics": strong_topics,
            "insufficient_data_topics": insufficient_topics,
            "repeated_incorrect_count": repeated_mistakes,
        }


# Singleton instance
learning_analysis_service = LearningAnalysisService()
