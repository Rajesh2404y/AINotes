"""Recursive Map-Reduce Summarization Service.

Executes distributed-style summarization across long documents:
- Map Phase: Summarizes individual chunks independently.
- Reduce Phase: Merges intermediate summaries and synthesizes a unified document summary.
- Recursive Phase: Re-chunks and re-summarizes intermediate outputs when documents span entire textbooks.
"""

import logging
from typing import List, Dict, Any, Optional
from backend.app.ai.chunking_service import chunking_service
from backend.app.utils.token_utils import count_tokens

logger = logging.getLogger("ainotes.map_reduce")


class MapReduceService:
    """Manages multi-stage map-reduce summarization with depth recursion guards."""

    def __init__(self, max_recursion_depth: int = 4):
        self.max_recursion_depth = max_recursion_depth

    def run_map_reduce(
        self,
        chunks: List[Dict[str, Any]],
        summarize_fn,
        tokenizer=None,
        max_input_tokens: int = 900,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Runs the map-reduce pipeline across input chunks.

        Args:
            chunks: List of chunk dicts from chunking_service.
            summarize_fn: Callable taking (text, generation_params) -> str.
            tokenizer: Tokenizer for token count verification.
            max_input_tokens: Max context length for the model.
            generation_params: Hyperparameters for text generation.

        Returns:
            Dict[str, Any]: Final summary text, metadata, and chunk summaries.
        """
        if not chunks:
            return {
                "summary": "",
                "total_chunks": 0,
                "reduction_passes": 0,
                "intermediate_summaries": []
            }

        # Fast path: Single chunk
        if len(chunks) == 1:
            single_text = chunks[0]["text"]
            logger.info("Single chunk document detected. Generating direct summary.")
            final_text = summarize_fn(single_text, generation_params or {})
            return {
                "summary": final_text,
                "total_chunks": 1,
                "reduction_passes": 0,
                "intermediate_summaries": [final_text]
            }

        # -------------------------------------------------------------
        # 1. MAP STAGE: Summarize each chunk independently
        # -------------------------------------------------------------
        logger.info("Map phase: Summarizing %d individual chunks...", len(chunks))
        intermediate_summaries: List[str] = []
        map_gen_params = dict(generation_params or {})
        # Map stage produces concise intermediate representations
        map_gen_params["max_length"] = min(map_gen_params.get("max_length", 250), 200)
        map_gen_params["min_length"] = min(map_gen_params.get("min_length", 50), 40)

        for chunk in chunks:
            try:
                chunk_summary = summarize_fn(chunk["text"], map_gen_params)
                if chunk_summary and chunk_summary.strip():
                    intermediate_summaries.append(chunk_summary.strip())
            except Exception as exc:
                logger.warning("Map failed on chunk #%d: %s. Using snippet fallback.", chunk.get("chunk_index", 0), exc)
                # Fallback to initial sentences rather than discarding chunk
                words = chunk["text"].split()
                intermediate_summaries.append(" ".join(words[:50]))

        if not intermediate_summaries:
            raise RuntimeError("Map phase failed to produce any intermediate summaries.")

        # -------------------------------------------------------------
        # 2. REDUCE & RECURSIVE STAGE
        # -------------------------------------------------------------
        current_intermediates = list(intermediate_summaries)
        depth = 0

        while depth < self.max_recursion_depth:
            combined_text = "\n\n".join(current_intermediates)
            combined_tokens = count_tokens(combined_text, tokenizer)

            logger.info(
                "Reduce phase depth %d: %d intermediate items (%d tokens). Max input: %d.",
                depth, len(current_intermediates), combined_tokens, max_input_tokens
            )

            # If combined summaries fit cleanly into model context, perform final reduction
            if combined_tokens <= max_input_tokens:
                logger.info("Intermediate summaries fit into context. Synthesizing final summary.")
                final_summary = summarize_fn(combined_text, generation_params or {})
                return {
                    "summary": final_summary,
                    "total_chunks": len(chunks),
                    "reduction_passes": depth + 1,
                    "intermediate_summaries": intermediate_summaries
                }

            # Otherwise, re-chunk the intermediate summaries and reduce again
            depth += 1
            logger.info("Recursively re-chunking intermediate summaries at depth %d...", depth)
            intermediate_chunks = chunking_service.create_chunks(
                combined_text,
                tokenizer=tokenizer,
                max_tokens=max_input_tokens,
                overlap_tokens=50
            )

            next_level_intermediates = []
            for sub_chunk in intermediate_chunks:
                try:
                    sub_sum = summarize_fn(sub_chunk["text"], map_gen_params)
                    if sub_sum and sub_sum.strip():
                        next_level_intermediates.append(sub_sum.strip())
                except Exception as exc:
                    logger.warning("Recursive reduction failed on intermediate chunk: %s", exc)

            current_intermediates = next_level_intermediates if next_level_intermediates else current_intermediates[:2]

        # Final fallback if max recursion depth reached
        logger.warning("Maximum recursion depth (%d) reached. Generating best-effort final reduction.", self.max_recursion_depth)
        truncated_combined = "\n\n".join(current_intermediates)[:max_input_tokens * 3]
        final_summary = summarize_fn(truncated_combined, generation_params or {})

        return {
            "summary": final_summary,
            "total_chunks": len(chunks),
            "reduction_passes": depth,
            "intermediate_summaries": intermediate_summaries
        }


# Global map-reduce service instance
map_reduce_service = MapReduceService()

