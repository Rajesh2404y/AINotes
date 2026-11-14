"""
Language Detection Service.
Detects source text language using Unicode script block analysis and linguistic patterns.
Falls back safely to manual language selection when confidence is insufficient.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from backend.app.utils.language_utils import CODE_TO_LANG, is_language_supported

logger = logging.getLogger(__name__)

# Unicode ranges for accurate script classification
SCRIPT_PATTERNS = [
    (re.compile(r"[\u0B80-\u0BFF]"), "ta"),  # Tamil
    (re.compile(r"[\u0900-\u097F]"), "hi"),  # Devanagari (Hindi)
    (re.compile(r"[\u0C00-\u0C7F]"), "te"),  # Telugu
    (re.compile(r"[\u0D00-\u0D7F]"), "ml"),  # Malayalam
    (re.compile(r"[\u0C80-\u0CFF]"), "kn"),  # Kannada
]


class LanguageDetectionService:
    """Detects text language with deterministic Unicode script identification."""

    @staticmethod
    def detect_language(text: str) -> Dict[str, Any]:
        """
        Analyzes source text to determine the dominant language.

        Returns:
            Dict: {'language': str, 'confidence': float, 'reliable': bool, 'method': str}
        """
        if not text or not text.strip():
            return {
                "language": "en",
                "confidence": 0.0,
                "reliable": False,
                "method": "default_empty"
            }

        clean_text = text.strip()
        total_chars = len(clean_text)

        # 1. Non-Latin Script Range Analysis (Extremely high accuracy for Indic scripts)
        for pattern, lang_code in SCRIPT_PATTERNS:
            matches = len(pattern.findall(clean_text))
            if matches > 5 or (total_chars > 0 and (matches / total_chars) > 0.15):
                return {
                    "language": lang_code,
                    "confidence": round(min(1.0, matches / max(total_chars * 0.5, 1)), 2),
                    "reliable": True,
                    "method": "unicode_script_analysis"
                }

        # 2. Latin-based Diacritics and Common Grammatical Markers Analysis (French, German, Spanish)
        fr_stopwords = {"le", "la", "les", "des", "du", "et", "est", "dans", "pour", "une", "un"}
        de_stopwords = {"der", "die", "das", "den", "dem", "und", "ist", "mit", "für", "ein", "eine"}
        es_stopwords = {"el", "los", "las", "del", "en", "para", "por", "un", "una", "es"}

        words_lower = [w.lower() for w in re.findall(r"\b\w+\b", clean_text)]
        fr_chars = len(re.findall(r"[èêëàâùûîïçœ]", clean_text, re.IGNORECASE))
        de_chars = len(re.findall(r"[äöüß]", clean_text, re.IGNORECASE))
        es_chars = len(re.findall(r"[áíóúñ¿¡]", clean_text, re.IGNORECASE))

        fr_score = sum(1 for w in words_lower if w in fr_stopwords) + fr_chars
        de_score = sum(1 for w in words_lower if w in de_stopwords) + de_chars
        es_score = sum(1 for w in words_lower if w in es_stopwords) + es_chars

        if fr_score > de_score and fr_score > es_score and fr_score >= 2:
            return {"language": "fr", "confidence": 0.88, "reliable": True, "method": "lexical_analysis"}
        elif de_score > fr_score and de_score > es_score and de_score >= 2:
            return {"language": "de", "confidence": 0.88, "reliable": True, "method": "lexical_analysis"}
        elif es_score > fr_score and es_score > de_score and es_score >= 2:
            return {"language": "es", "confidence": 0.88, "reliable": True, "method": "lexical_analysis"}

        # 3. Default to English for standard Latin educational text
        words = re.findall(r"\b[A-Za-z]+\b", clean_text)
        if len(words) >= 5:
            return {
                "language": "en",
                "confidence": 0.90,
                "reliable": True,
                "method": "latin_lexical_analysis"
            }

        return {
            "language": "en",
            "confidence": 0.50,
            "reliable": False,
            "method": "fallback"
        }


# Global detector instance
language_detection_service = LanguageDetectionService()

