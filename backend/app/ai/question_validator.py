"""
Question Validator Service.
Validates question structure, options, answer keys, duplicates, and pedagogical constraints
prior to database persistence.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_QUESTION_TYPES = {"mcq", "true_false", "one_word", "fill_blank"}
SUPPORTED_DIFFICULTIES = {"easy", "medium", "hard"}


class QuestionValidationError(Exception):
    """Raised when a generated question fails structural or content validation."""
    pass


class QuestionValidator:
    """Validates assessment questions against strict pedagogical and formatting constraints."""

    @staticmethod
    def validate_question(
        question_data: Dict[str, Any],
        seen_question_texts: Optional[Set[str]] = None,
        source_text: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates an individual question dictionary.
        Returns (True, None) if valid, or (False, error_reason) if invalid.
        """
        # 1. Question Text validation
        q_text = question_data.get("question_text", "").strip()
        if not q_text or len(q_text) < 8:
            return False, "Question text is missing or too brief (minimum 8 characters)."

        # 2. Duplicate Detection
        if seen_question_texts is not None:
            norm_q = re.sub(r"\W+", " ", q_text.lower()).strip()
            if norm_q in seen_question_texts:
                return False, f"Duplicate question detected: '{q_text[:40]}...'"
            seen_question_texts.add(norm_q)

        # 3. Question Type
        q_type = question_data.get("question_type", "").lower().strip()
        if q_type not in SUPPORTED_QUESTION_TYPES:
            return False, f"Unsupported question type '{q_type}'. Must be one of: {SUPPORTED_QUESTION_TYPES}"

        # 4. Difficulty validation
        diff = question_data.get("difficulty", "medium").lower().strip()
        if diff not in SUPPORTED_DIFFICULTIES:
            return False, f"Invalid difficulty '{diff}'. Must be one of: {SUPPORTED_DIFFICULTIES}"

        # 5. Explanation validation
        explanation = question_data.get("explanation", "").strip()
        if not explanation or len(explanation) < 5:
            return False, "Question is missing a meaningful explanation."

        # 6. Correct Answer validation
        correct_answer = str(question_data.get("correct_answer", "")).strip()
        if not correct_answer:
            return False, "Question is missing a correct answer."

        # 7. Type-Specific Rules
        if q_type == "mcq":
            options = question_data.get("options")
            if not isinstance(options, list) or len(options) != 4:
                return False, f"MCQ requires exactly 4 options. Found {len(options) if isinstance(options, list) else 0}."

            cleaned_options = [str(opt).strip() for opt in options if str(opt).strip()]
            if len(cleaned_options) != 4:
                return False, "MCQ options contain blank or empty values."

            # Check distinctness
            unique_options = {opt.lower() for opt in cleaned_options}
            if len(unique_options) != 4:
                return False, "MCQ options must all be distinct (no duplicates)."

            # Correct answer must match one of the options or an option key (A, B, C, D)
            valid_keys = {"A", "B", "C", "D", "a", "b", "c", "d"}
            matches_option = correct_answer in cleaned_options or correct_answer.upper() in valid_keys
            if not matches_option:
                return False, f"MCQ correct answer '{correct_answer}' does not match any of the provided options."

        elif q_type == "true_false":
            norm_ans = correct_answer.strip().capitalize()
            if norm_ans not in {"True", "False"}:
                return False, f"True/False question must have correct answer 'True' or 'False'. Got: '{correct_answer}'."

        elif q_type == "one_word":
            words = correct_answer.strip().split()
            if len(words) > 4:
                return False, f"One-word answer should be a concise term/phrase (max 4 words). Got: '{correct_answer}'."

        elif q_type == "fill_blank":
            if "______" not in q_text and "____" not in q_text and "[blank]" not in q_text.lower():
                return False, "Fill-in-the-blank question must contain a blank placeholder (e.g. '______')."

        # 8. Source Grounding Check (optional source text validation)
        if source_text and len(source_text.strip()) > 50:
            source_lower = source_text.lower()
            # The correct answer or significant tokens from the question must appear in source
            key_tokens = [w.lower() for w in re.findall(r"\b[A-Za-z0-9]{4,}\b", correct_answer)]
            if key_tokens and not any(token in source_lower for token in key_tokens):
                # Check if question tokens are grounded
                q_tokens = [w.lower() for w in re.findall(r"\b[A-Za-z0-9]{4,}\b", q_text)]
                grounded_q = sum(1 for token in q_tokens if token in source_lower)
                if grounded_q < 2:
                    return False, "Question content is not sufficiently grounded in the source document."

        return True, None

    @classmethod
    def validate_batch(
        cls,
        questions: List[Dict[str, Any]],
        source_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Filters and returns only valid questions from a candidate batch.
        """
        valid_questions: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()

        for idx, q in enumerate(questions):
            is_valid, reason = cls.validate_question(q, seen_question_texts=seen_texts, source_text=source_text)
            if is_valid:
                valid_questions.append(q)
            else:
                logger.warning("Rejected candidate question [%d]: %s", idx, reason)

        return valid_questions


# Global validator instance
question_validator = QuestionValidator()

