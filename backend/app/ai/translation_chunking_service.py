"""
Translation Chunking and Reassembly Service.
Splits long academic summaries into coherent segments along paragraph and sentence boundaries,
ensuring model context window compliance while preserving structure, headings, lists,
and Unicode script integrity.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from backend.app.utils.token_utils import count_tokens, split_into_paragraphs, split_into_sentences

logger = logging.getLogger(__name__)


class TranslationChunkingService:
    """Handles semantic segmentation and ordered reassembly for long-form translations."""

    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 40):
        self.default_max_tokens = max_tokens
        self.default_overlap = overlap_tokens

    def create_translation_chunks(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        tokenizer: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Partitions text into structured chunks for sequential translation.
        Preserves paragraph and sentence boundaries without duplicate overlap in reconstructed text.
        """
        if not text or not text.strip():
            return []

        limit = max_tokens or self.default_max_tokens
        paragraphs = split_into_paragraphs(text)
        chunks: List[Dict[str, Any]] = []

        current_sentences: List[str] = []
        current_tokens = 0
        chunk_idx = 0

        for p_idx, para in enumerate(paragraphs):
            sentences = split_into_sentences(para)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue

                s_tokens = count_tokens(s_clean, tokenizer)

                # If adding this sentence exceeds chunk budget, flush accumulated sentences
                if current_sentences and (current_tokens + s_tokens > limit):
                    chunk_text = " ".join(current_sentences)
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "text": chunk_text,
                        "token_count": current_tokens,
                        "is_paragraph_end": False
                    })
                    chunk_idx += 1
                    current_sentences = [s_clean]
                    current_tokens = s_tokens
                else:
                    current_sentences.append(s_clean)
                    current_tokens += s_tokens

            # Mark paragraph boundary if sentences ended
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "chunk_index": chunk_idx,
                    "text": chunk_text,
                    "token_count": current_tokens,
                    "is_paragraph_end": True
                })
                chunk_idx += 1
                current_sentences = []
                current_tokens = 0

        # Flush any remaining
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append({
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "token_count": current_tokens,
                "is_paragraph_end": True
            })

        logger.debug("Partitioned document into %d translation chunks.", len(chunks))
        return chunks

    def reassemble_chunks(self, translated_chunks: List[Dict[str, Any]]) -> str:
        """
        Reconstructs the full translated text preserving original paragraph breaks and order.
        """
        if not translated_chunks:
            return ""

        # Sort strictly by chunk_index
        sorted_chunks = sorted(translated_chunks, key=lambda c: c.get("chunk_index", 0))

        paragraphs: List[str] = []
        current_para_parts: List[str] = []

        for c in sorted_chunks:
            text_part = c.get("translated_text", "").strip()
            if not text_part:
                continue

            current_para_parts.append(text_part)

            if c.get("is_paragraph_end", False):
                paragraphs.append(" ".join(current_para_parts))
                current_para_parts = []

        if current_para_parts:
            paragraphs.append(" ".join(current_para_parts))

        # Join paragraphs with double newlines
        return "\n\n".join(p for p in paragraphs if p.strip())


# Global chunking instance
translation_chunking_service = TranslationChunkingService()

