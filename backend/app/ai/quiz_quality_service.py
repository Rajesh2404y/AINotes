"""
Quiz Quality and Diversity Service.
Validates source text sufficiency, monitors question diversity, and prevents
duplicate or semantically redundant questions across generated assessments.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class QuizQualityService:
    """Ensures assessment rigor, diversity, and source sufficiency."""

    @staticmethod
    def assess_source_sufficiency(source_text: str, requested_questions: int) -> Tuple[bool, Optional[str]]:
        """
        Validates whether the source text contains sufficient factual material
        to support the requested number of high-quality questions without hallucination.
        """
        if not source_text or not source_text.strip():
            return False, "Source material is empty."

        words = re.findall(r"\b\w+\b", source_text)
        word_count = len(words)

        # Baseline: at least 40 words for minimum 5 questions, and ~12 words per question
        min_required_words = max(40, requested_questions * 10)
        if word_count < min_required_words:
            return False, (
                f"Source document has only {word_count} words, which is insufficient "
                f"to generate {requested_questions} grounded questions without filler. "
                f"Please select a longer document or request fewer questions."
            )

        return True, None

    @staticmethod
    def calculate_question_similarity(q1: str, q2: str) -> float:
        """Calculates token Jaccard similarity between two questions."""
        tokens1 = set(re.findall(r"\b\w{3,}\b", q1.lower()))
        tokens2 = set(re.findall(r"\b\w{3,}\b", q2.lower()))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / max(union, 1)

    @classmethod
    def deduplicate_questions(cls, questions: List[Dict[str, Any]], max_similarity: float = 0.70) -> List[Dict[str, Any]]:
        """
        Filters out questions that share excessive semantic overlap with previously retained questions.
        """
        retained: List[Dict[str, Any]] = []

        for candidate in questions:
            c_text = candidate.get("question_text", "")
            is_duplicate = False

            for existing in retained:
                e_text = existing.get("question_text", "")
                similarity = cls.calculate_question_similarity(c_text, e_text)
                if similarity >= max_similarity:
                    logger.debug("Deduplicated candidate question (similarity %.2f): %s", similarity, c_text[:40])
                    is_duplicate = True
                    break

            if not is_duplicate:
                retained.append(candidate)

        return retained

    @classmethod
    def evaluate_quiz_quality(cls, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Produces a comprehensive quality metrics audit for the generated quiz.
        """
        total = len(questions)
        if total == 0:
            return {"grade": "POOR", "total": 0, "type_distribution": {}}

        types_count: Dict[str, int] = {}
        for q in questions:
            t = q.get("question_type", "unknown")
            types_count[t] = types_count.get(t, 0) + 1

        return {
            "grade": "EXCELLENT" if total >= 5 else "ADEQUATE",
            "total_questions": total,
            "type_distribution": types_count,
            "has_explanations": all(bool(q.get("explanation")) for q in questions),
            "mcq_has_four_options": all(
                len(q.get("options", [])) == 4 for q in questions if q.get("question_type") == "mcq"
            )
        }


# Global quality service instance
quiz_quality_service = QuizQualityService()

