"""
Answer Evaluation Service.
Performs rigorous server-side evaluation of student quiz responses across
all question types: MCQ, True/False, One-Word, and Fill-in-the-Blanks.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnswerEvaluationService:
    """Evaluates student quiz submissions with type-specific answer normalization."""

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Strips surrounding whitespace, collapses internal whitespace, and lowers case."""
        if not text:
            return ""
        clean = re.sub(r"\s+", " ", str(text)).strip().lower()
        return clean

    @classmethod
    def evaluate_mcq(cls, selected_answer: Optional[str], correct_answer: str, options: Optional[List[str]] = None) -> bool:
        """
        Evaluates Multiple Choice Question responses.
        Matches either option index/letter (e.g., 'A', 'B') or direct text match.
        """
        if not selected_answer:
            return False

        norm_sel = cls.normalize_text(selected_answer)
        norm_cor = cls.normalize_text(correct_answer)

        # Direct text match
        if norm_sel == norm_cor:
            return True

        # Check if correct answer is a letter and selected is option text or vice versa
        letters = ["a", "b", "c", "d"]
        if options and isinstance(options, list):
            # If selected is 'a', 'b', 'c', 'd'
            if norm_sel in letters:
                sel_idx = letters.index(norm_sel)
                if 0 <= sel_idx < len(options):
                    if cls.normalize_text(options[sel_idx]) == norm_cor:
                        return True

            # If correct is 'a', 'b', 'c', 'd'
            if norm_cor in letters:
                cor_idx = letters.index(norm_cor)
                if 0 <= cor_idx < len(options):
                    if norm_sel == cls.normalize_text(options[cor_idx]):
                        return True

        return False

    @classmethod
    def evaluate_true_false(cls, selected_answer: Optional[str], correct_answer: str) -> bool:
        """
        Evaluates True/False responses with boolean normalization.
        """
        if not selected_answer:
            return False

        norm_sel = cls.normalize_text(selected_answer)
        norm_cor = cls.normalize_text(correct_answer)

        true_aliases = {"true", "t", "1", "yes", "y", "correct"}
        false_aliases = {"false", "f", "0", "no", "n", "incorrect"}

        is_sel_true = norm_sel in true_aliases
        is_sel_false = norm_sel in false_aliases

        is_cor_true = norm_cor in true_aliases
        is_cor_false = norm_cor in false_aliases

        if is_sel_true and is_cor_true:
            return True
        if is_sel_false and is_cor_false:
            return True

        return False

    @classmethod
    def evaluate_one_word(
        cls,
        selected_answer: Optional[str],
        correct_answer: str,
        acceptable_alternatives: Optional[List[str]] = None
    ) -> bool:
        """
        Evaluates concise One-Word responses.
        Normalizes punctuation, casing, and compares against answer and allowed alternatives.
        """
        if not selected_answer:
            return False

        norm_sel = re.sub(r"[^\w\s]", "", cls.normalize_text(selected_answer))
        norm_cor = re.sub(r"[^\w\s]", "", cls.normalize_text(correct_answer))

        if norm_sel == norm_cor:
            return True

        if acceptable_alternatives:
            for alt in acceptable_alternatives:
                norm_alt = re.sub(r"[^\w\s]", "", cls.normalize_text(alt))
                if norm_sel == norm_alt:
                    return True

        return False

    @classmethod
    def evaluate_fill_blank(
        cls,
        selected_answer: Optional[str],
        correct_answer: str,
        acceptable_alternatives: Optional[List[str]] = None
    ) -> bool:
        """
        Evaluates Fill-in-the-Blank responses using exact normalized matching.
        """
        return cls.evaluate_one_word(selected_answer, correct_answer, acceptable_alternatives)

    @classmethod
    def evaluate_question(
        cls,
        question_type: str,
        selected_answer: Optional[str],
        correct_answer: str,
        options: Optional[List[str]] = None,
        acceptable_alternatives: Optional[List[str]] = None
    ) -> bool:
        """
        Routes evaluation based on question type.
        """
        q_type = (question_type or "mcq").lower().strip()

        if q_type == "mcq":
            return cls.evaluate_mcq(selected_answer, correct_answer, options)
        elif q_type == "true_false":
            return cls.evaluate_true_false(selected_answer, correct_answer)
        elif q_type == "one_word":
            return cls.evaluate_one_word(selected_answer, correct_answer, acceptable_alternatives)
        elif q_type == "fill_blank":
            return cls.evaluate_fill_blank(selected_answer, correct_answer, acceptable_alternatives)
        else:
            norm_sel = cls.normalize_text(selected_answer)
            norm_cor = cls.normalize_text(correct_answer)
            return norm_sel == norm_cor

    @classmethod
    def calculate_score(
        cls,
        questions: List[Any],
        submitted_responses: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        Evaluates a complete quiz attempt against question records.

        Args:
            questions: List of Question models or question dicts.
            submitted_responses: Mapping of question_id -> user submitted answer string.

        Returns:
            Dict containing score, total_questions, percentage, and evaluated response items.
        """
        total = len(questions)
        if total == 0:
            return {
                "score": 0,
                "total_questions": 0,
                "percentage": 0.0,
                "evaluations": []
            }

        correct_count = 0
        evaluations: List[Dict[str, Any]] = []

        for q in questions:
            # Handle both ORM object and dictionary
            q_id = q.id if hasattr(q, "id") else q.get("id")
            q_text = q.question_text if hasattr(q, "question_text") else q.get("question_text")
            q_type = q.question_type if hasattr(q, "question_type") else q.get("question_type")
            q_options = q.options if hasattr(q, "options") else q.get("options")
            q_correct = q.correct_answer if hasattr(q, "correct_answer") else q.get("correct_answer")
            q_expl = q.explanation if hasattr(q, "explanation") else q.get("explanation")

            selected = submitted_responses.get(q_id)
            is_correct = cls.evaluate_question(
                question_type=q_type,
                selected_answer=selected,
                correct_answer=q_correct,
                options=q_options
            )

            if is_correct:
                correct_count += 1

            evaluations.append({
                "question_id": q_id,
                "question_text": q_text,
                "question_type": q_type,
                "options": q_options,
                "selected_answer": selected,
                "correct_answer": q_correct,
                "is_correct": is_correct,
                "explanation": q_expl
            })

        percentage = round((correct_count / total) * 100.0, 2)

        return {
            "score": correct_count,
            "total_questions": total,
            "percentage": percentage,
            "evaluations": evaluations
        }


# Global evaluation instance
answer_evaluation_service = AnswerEvaluationService()

