"""Tokenization, Sentence Splitting, and Text Boundary Utilities.

Provides tokenizer-aware token counting and non-destructive sentence/paragraph splitting
while preserving mathematical expressions, code blocks, lists, and Unicode characters.
"""

import re
import logging
from typing import List, Optional

logger = logging.getLogger("ainotes.token_utils")


def split_into_paragraphs(text: str) -> List[str]:
    """Splits text into paragraphs on double line-breaks, stripping empty entries."""
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paragraphs if paragraphs else [text.strip()]


def split_into_sentences(text: str) -> List[str]:
    """Splits text into coherent sentences without mangling decimals, abbreviations, or formulas.

    Uses regex with negative lookbehind/lookahead for common abbreviations (Dr., e.g., i.e., vs.)
    and numbers (e.g. 3.14).
    """
    if not text:
        return []

    # Clean text of extreme whitespace while keeping newlines
    clean = text.strip()

    # Pattern: End of sentence (. ! ?) followed by whitespace, not preceded by known abbreviations or numbers
    # We protect common abbreviations
    protected = re.sub(r"\b(e\.g\.|i\.e\.|etc\.|vs\.|Dr\.|Prof\.|Mr\.|Mrs\.|Ms\.|Fig\.|Eq\.)", lambda m: m.group(0).replace(".", "@DOT@"), clean)

    # Split on sentence terminals
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'‘“(\[])", protected)

    sentences = []
    for s in raw_sentences:
        restored = s.replace("@DOT@", ".").strip()
        if restored:
            sentences.append(restored)

    if not sentences and clean:
        sentences = [clean]

    return sentences


def estimate_token_count(text: str) -> int:
    """Heuristic token count estimation (~1.33 tokens per word, or 4 chars per token).

    Used as an ultra-fast fallback when Hugging Face tokenizer is not instantiated.
    """
    if not text:
        return 0
    words = text.split()
    return max(1, int(len(words) * 1.35))


def count_tokens(text: str, tokenizer=None) -> int:
    """Calculates exact token count using model tokenizer, with heuristic fallback."""
    if not text:
        return 0

    if tokenizer is not None:
        try:
            tokens = tokenizer.encode(text, truncation=False, add_special_tokens=False)
            return len(tokens)
        except Exception as exc:
            logger.debug("Tokenizer token counting failed (%s), falling back to heuristic: %s", type(tokenizer), exc)

    return estimate_token_count(text)

