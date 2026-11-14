"""Text Quality Assessment and Statistical Analysis Service.

Computes comprehensive document metrics (words, characters, sentences, paragraphs),
detects noise and corruption, and categorizes extraction quality as HIGH, MEDIUM, LOW, or FAILED.
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ainotes.text_quality")


def assess_text_quality(
    text: str,
    total_pages: int = 1,
    ocr_pages_count: int = 0,
    ocr_confidence: float = 0.0,
    extraction_warnings: List[str] = None
) -> Dict[str, Any]:
    """Evaluates readability, completeness, and noise ratio of extracted text.

    Args:
        text (str): Cleaned extracted text.
        total_pages (int): Document page count.
        ocr_pages_count (int): Number of pages processed with OCR.
        ocr_confidence (float): Average OCR confidence (0-100).
        extraction_warnings (List[str]): Prior warnings from extractors.

    Returns:
        Dict[str, Any]: Quality evaluation dictionary with quality status and warnings.
    """
    warnings = list(extraction_warnings or [])

    if not text or not text.strip():
        return {
            "quality": "FAILED",
            "total_characters": 0,
            "total_words": 0,
            "total_sentences": 0,
            "total_paragraphs": 0,
            "total_pages": total_pages,
            "ocr_pages_count": ocr_pages_count,
            "ocr_confidence": ocr_confidence,
            "warnings": ["No readable text could be extracted from this document."]
        }

    clean_content = text.strip()
    total_characters = len(clean_content)

    # Word count (splitting by whitespace)
    words = clean_content.split()
    total_words = len(words)

    # Paragraph count (splitting by double newline)
    paragraphs = [p for p in re.split(r"\n\s*\n", clean_content) if p.strip()]
    total_paragraphs = len(paragraphs)

    # Sentence count heuristic (splitting on punctuation followed by space/newline)
    sentences = [s for s in re.split(r"[.!?]+[\s\n]+", clean_content) if s.strip()]
    total_sentences = max(1, len(sentences)) if total_words > 0 else 0

    # Noise and character ratio analysis
    # Alphabetic & Unicode word characters vs total non-space characters
    non_space_chars = len(re.sub(r"\s", "", clean_content))
    alphanumeric_chars = len(re.findall(r"\w", clean_content, flags=re.UNICODE))
    alpha_ratio = (alphanumeric_chars / non_space_chars) if non_space_chars > 0 else 0.0

    # Quality classification rules
    quality = "HIGH"

    if total_words == 0:
        quality = "FAILED"
        warnings.append("Extracted text contains 0 recognizable words.")
    elif total_words < 15:
        quality = "LOW"
        warnings.append("Very low word count (< 15 words). Document content may be incomplete.")
    elif total_words < 50:
        quality = "MEDIUM"
        warnings.append("Brief document (< 50 words). Summary output may be concise.")

    if non_space_chars > 0 and alpha_ratio < 0.5:
        if quality == "HIGH":
            quality = "MEDIUM"
        warnings.append("High symbol-to-text noise ratio detected. Formatting or scanning noise may be present.")

    if ocr_pages_count > 0 and ocr_confidence > 0 and ocr_confidence < 50:
        if quality == "HIGH":
            quality = "MEDIUM"
        warnings.append(f"Average OCR confidence was low ({ocr_confidence:.1f}%). Verification recommended.")

    return {
        "quality": quality,
        "total_characters": total_characters,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "total_paragraphs": total_paragraphs,
        "total_pages": max(1, total_pages),
        "ocr_pages_count": ocr_pages_count,
        "ocr_confidence": round(ocr_confidence, 2),
        "warnings": warnings
    }
