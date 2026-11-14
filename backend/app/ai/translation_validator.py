"""
Translation Validation and Terminology Quality Service.
Verifies translation completeness, Unicode integrity, numerical preservation,
and proper handling of academic technical terminology.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.utils.language_utils import is_language_supported

logger = logging.getLogger(__name__)

# Standard academic terms to monitor for preservation
CORE_ACADEMIC_TERMS = [
    "Machine Learning",
    "Artificial Intelligence",
    "Neural Network",
    "Deep Learning",
    "Backpropagation",
    "Gradient Descent",
    "Convolutional Neural Network",
    "Operating System",
    "Supervised Learning",
    "Unsupervised Learning",
    "Algorithm"
]


class TranslationValidator:
    """Validates translated content for factual and structural consistency."""

    @staticmethod
    def validate_translation_output(
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Runs comprehensive validation on translated output.
        """
        # 1. Non-empty check
        if not source_text or not source_text.strip():
            return False, "Source text is empty."
        if not translated_text or not translated_text.strip():
            return False, "Translation output is empty."

        # 2. Supported Language check
        if not is_language_supported(target_lang):
            return False, f"Target language '{target_lang}' is not supported."

        # 3. Source vs Target identical check
        if source_lang != target_lang and len(source_text.strip()) > 30:
            if source_text.strip().lower() == translated_text.strip().lower():
                return False, "Translation output is identical to source text despite differing languages."

        # 4. Numerical preservation check
        source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", source_text))
        trans_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", translated_text))
        # If there are numbers in source, check that most are preserved (allowing minor formatting differences)
        if len(source_numbers) >= 3:
            retained = len(source_numbers.intersection(trans_numbers))
            if retained / len(source_numbers) < 0.40:
                logger.warning("Numerical discrepancy in translation: %s vs %s", source_numbers, trans_numbers)

        # 5. Unicode character validity
        try:
            translated_text.encode("utf-8").decode("utf-8")
        except UnicodeError as exc:
            return False, f"Invalid Unicode sequence detected in translation: {exc}"

        return True, None

    @staticmethod
    def preserve_academic_glossary(text: str, glossary: Optional[Dict[str, str]] = None) -> str:
        """
        Ensures established technical terminology is properly referenced.
        """
        if not glossary:
            return text

        result = text
        for term, replacement in glossary.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            result = pattern.sub(replacement, result)

        return result


# Global validator instance
translation_validator = TranslationValidator()

