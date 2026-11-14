"""Tokenizer-Aware Text Chunking Service.

Partitions long academic documents and textbooks into coherent, overlapping chunks
while strictly respecting model token limits, preserving paragraph and sentence boundaries,
and maintaining chronological document context.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.app.utils.token_utils import (
    split_into_paragraphs,
    split_into_sentences,
    count_tokens,
)

logger = logging.getLogger("ainotes.chunking_service")


class ChunkingService:
    """Provides semantic sentence-boundary chunking with token overlap."""

    def __init__(self, default_max_tokens: int = 900, default_overlap_tokens: int = 100):
        self.default_max_tokens = default_max_tokens
        self.default_overlap_tokens = default_overlap_tokens

    def create_chunks(
        self,
        text: str,
        tokenizer: Optional[Any] = None,
        max_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Splits source text into a sequential list of tokenizer-aware overlapping chunks.

        Args:
            text (str): Source document content.
            tokenizer: PreTrainedTokenizer or None (uses heuristic token count).
            max_tokens (int): Maximum token limit per chunk.
            overlap_tokens (int): Overlap tokens preserved between sequential chunks.

        Returns:
            List[Dict[str, Any]]: List of structured chunk dictionaries.
        """
        if not text or not text.strip():
            return []

        clean_text = text.strip()
        limit = max_tokens or self.default_max_tokens
        overlap = overlap_tokens if overlap_tokens is not None else self.default_overlap_tokens

        # Ensure overlap is strictly less than max_tokens
        if overlap >= limit:
            overlap = limit // 4

        # Fast path: Entire document fits within token limit
        total_tokens = count_tokens(clean_text, tokenizer)
        if total_tokens <= limit:
            return [{
                "chunk_index": 0,
                "text": clean_text,
                "token_count": total_tokens,
                "char_count": len(clean_text),
                "sentence_count": len(split_into_sentences(clean_text))
            }]

        # Deconstruct into paragraphs and sentences
        paragraphs = split_into_paragraphs(clean_text)
        all_sentences: List[str] = []
        for para in paragraphs:
            para_sents = split_into_sentences(para)
            all_sentences.extend(para_sents)

        if not all_sentences:
            all_sentences = [clean_text]

        chunks: List[Dict[str, Any]] = []
        current_chunk_sentences: List[str] = []
        current_tokens = 0
        chunk_idx = 0

        i = 0
        while i < len(all_sentences):
            sent = all_sentences[i]
            sent_tokens = count_tokens(sent, tokenizer)

            # If a single sentence exceeds max_tokens on its own, split by words
            if sent_tokens > limit:
                words = sent.split()
                sub_sentence = []
                sub_tokens = 0
                for w in words:
                    w_tokens = count_tokens(w + " ", tokenizer)
                    if sub_tokens + w_tokens > limit and sub_sentence:
                        # Flush current
                        text_piece = " ".join(sub_sentence)
                        chunks.append({
                            "chunk_index": chunk_idx,
                            "text": text_piece,
                            "token_count": count_tokens(text_piece, tokenizer),
                            "char_count": len(text_piece),
                            "sentence_count": 1
                        })
                        chunk_idx += 1
                        sub_sentence = [w]
                        sub_tokens = w_tokens
                    else:
                        sub_sentence.append(w)
                        sub_tokens += w_tokens

                if sub_sentence:
                    text_piece = " ".join(sub_sentence)
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "text": text_piece,
                        "token_count": count_tokens(text_piece, tokenizer),
                        "char_count": len(text_piece),
                        "sentence_count": 1
                    })
                    chunk_idx += 1
                i += 1
                continue

            # Standard accumulation
            if current_tokens + sent_tokens <= limit:
                current_chunk_sentences.append(sent)
                current_tokens += sent_tokens
                i += 1
            else:
                # Finalize current chunk
                if current_chunk_sentences:
                    chunk_text = " ".join(current_chunk_sentences).strip()
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "text": chunk_text,
                        "token_count": count_tokens(chunk_text, tokenizer),
                        "char_count": len(chunk_text),
                        "sentence_count": len(current_chunk_sentences)
                    })
                    chunk_idx += 1

                # Calculate overlap sentences from the end of current chunk
                overlap_sentences: List[str] = []
                accum_overlap_tokens = 0
                for s in reversed(current_chunk_sentences):
                    st = count_tokens(s, tokenizer)
                    if accum_overlap_tokens + st <= overlap:
                        overlap_sentences.insert(0, s)
                        accum_overlap_tokens += st
                    else:
                        break

                current_chunk_sentences = list(overlap_sentences)
                current_tokens = accum_overlap_tokens

        # Flush any trailing sentences
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences).strip()
            # Avoid duplicate trailing chunk if identical to last
            if not chunks or chunks[-1]["text"] != chunk_text:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "text": chunk_text,
                    "token_count": count_tokens(chunk_text, tokenizer),
                    "char_count": len(chunk_text),
                    "sentence_count": len(current_chunk_sentences)
                })

        return chunks

    def chunk_text(self, text: str, max_tokens: Optional[int] = None, overlap_tokens: Optional[int] = None):
        """Convenience method returning a list of Chunk objects."""
        raw_chunks = self.create_chunks(text=text, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        
        class ChunkItem:
            def __init__(self, data: Dict[str, Any]):
                self.index = data["chunk_index"]
                self.text = data["text"]
                self.token_count = data["token_count"]
                self.char_count = data["char_count"]
                self.sentence_count = data["sentence_count"]

            def __repr__(self):
                return f"<Chunk {self.index}: {self.token_count} tokens>"

        return [ChunkItem(c) for c in raw_chunks]


# Global chunking service instance
chunking_service = ChunkingService()

