"""
Summary Quality Assessment Service.
Evaluates the quality, compression ratio, readability, and factual grounding
of generated summaries against the source educational document.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SummaryQualityService:
    """Evaluates generated summary quality, compression, and grounding."""

    def evaluate(self, source_text: str, summary_text: str) -> Dict[str, Any]:
        """
        Runs comprehensive evaluation on a generated summary against the source text.
        """
        source_words = [w.lower() for w in re.findall(r"\b\w+\b", source_text or "")]
        summary_words = [w.lower() for w in re.findall(r"\b\w+\b", summary_text or "")]

        source_word_count = len(source_words)
        summary_word_count = len(summary_words)

        if source_word_count == 0 or summary_word_count == 0:
            return {
                "source_word_count": source_word_count,
                "summary_word_count": summary_word_count,
                "compression_ratio": 0.0,
                "grounding_score": 0.0,
                "readability_score": 0.0,
                "quality_grade": "LOW",
                "notes": "Insufficient text for evaluation."
            }

        # 1. Compression Ratio (percentage of reduction)
        compression_ratio = round((1.0 - (summary_word_count / max(source_word_count, 1))) * 100, 2)
        compression_ratio = max(0.0, min(100.0, compression_ratio))

        # 2. Grounding / Factuality Check (vocabulary containment)
        source_vocab = set(source_words)
        grounded_words = sum(1 for w in summary_words if w in source_vocab)
        grounding_score = round((grounded_words / max(summary_word_count, 1)) * 100, 2)

        # 3. Readability: Flesch Reading Ease approximation
        sentences = [s.strip() for s in re.split(r"[.!?]+", summary_text) if s.strip()]
        sentence_count = max(1, len(sentences))
        avg_sentence_len = summary_word_count / sentence_count

        # Syllables estimation
        syllables = 0
        for w in summary_words:
            count = len(re.findall(r"[aeiouy]+", w))
            syllables += max(1, count)
        avg_syllables_per_word = syllables / max(1, summary_word_count)

        flesch_score = 206.835 - (1.015 * avg_sentence_len) - (84.6 * avg_syllables_per_word)
        flesch_score = round(max(0.0, min(100.0, flesch_score)), 2)

        # 4. Overall Quality Grade
        # Ideal: good grounding (>80%), moderate compression (20-90%), readability > 40
        if grounding_score >= 80.0 and summary_word_count >= 15:
            quality_grade = "HIGH"
        elif grounding_score >= 65.0 and summary_word_count >= 10:
            quality_grade = "MEDIUM"
        else:
            quality_grade = "LOW"

        return {
            "source_word_count": source_word_count,
            "summary_word_count": summary_word_count,
            "compression_ratio": compression_ratio,
            "grounding_score": grounding_score,
            "readability_score": flesch_score,
            "quality_grade": quality_grade
        }


# Global singleton instance
summary_quality_service = SummaryQualityService()

