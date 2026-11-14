"""Text Cleaning and Preprocessing Service.

Implements Unicode NFKC normalization, whitespace and line-break standardization,
control character removal, and sentence boundary correction while strictly preserving
educational content, headings, lists, mathematical equations, and Tamil/Unicode scripts.
"""

import re
import unicodedata
import logging

logger = logging.getLogger("ainotes.text_cleaning")


def clean_text(raw_text: str) -> str:
    """Performs non-destructive, formatting-preserving cleaning of extracted text.

    Args:
        raw_text (str): Raw extracted document text.

    Returns:
        str: Normalized and standardized text.
    """
    if not raw_text or not isinstance(raw_text, str):
        return ""

    # 1. Unicode Normalization (NFKC standardizes compatibility characters without losing scripts)
    normalized = unicodedata.normalize("NFKC", raw_text)

    # 2. Standardize Newlines
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Remove non-printable control characters, preserving \n, \t, and Unicode characters
    # Retains basic ASCII controls \t (9), \n (10), and strip all others below 32 or in 127-159
    normalized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", normalized)

    # 4. Standardize strange unicode spaces (non-breaking space, thin space, zero-width space)
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\u200b", "")  # zero-width space
    normalized = normalized.replace("\ufeff", "")  # byte order mark

    # 5. Normalize intra-line spaces (multiple spaces -> single space, preserving tabs and newlines)
    lines = normalized.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned_line = re.sub(r" {2,}", " ", line).strip()
        cleaned_lines.append(cleaned_line)

    reconstructed = "\n".join(cleaned_lines)

    # 6. Collapse excessive blank lines (more than 2 consecutive newlines -> 2 newlines)
    reconstructed = re.sub(r"\n{3,}", "\n\n", reconstructed)

    # 7. Normalize sentence boundaries for punctuation spacing (horizontal spaces only)
    # e.g., "word . Next" -> "word. Next" (without altering newlines)
    reconstructed = re.sub(r"([a-zA-Z0-9])[ \t]+([.,;:!?])[ \t]*", r"\1\2 ", reconstructed)

    # 8. Clean up bullet points to standard unicode bullet
    reconstructed = re.sub(r"^[•·○][ \t]*", "• ", reconstructed, flags=re.MULTILINE)

    return reconstructed.strip()
