"""Multi-Tier Summarization Engine.

Supports Short, Medium, and Detailed study summaries using abstractive transformer models
(DistilBART / BART-Large / FLAN-T5) combined with tokenizer-aware recursive map-reduce chunking.
Provides robust offline extractive fallback when transformers are not loaded.
"""

import time
import logging
from typing import Dict, Any, Optional
from backend.app.ai.model_loader import model_loader, ModelLoadError
from backend.app.ai.chunking_service import chunking_service
from backend.app.ai.map_reduce_service import map_reduce_service
from backend.app.utils.token_utils import count_tokens, split_into_sentences

logger = logging.getLogger("ainotes.summarization_service")

# Generation Hyperparameters by Summary Mode
MODE_CONFIGS = {
    "short": {
        "min_length": 50,
        "max_length": 140,
        "length_penalty": 2.0,
        "num_beams": 4,
        "target_desc": "Concise high-yield revision"
    },
    "medium": {
        "min_length": 120,
        "max_length": 280,
        "length_penalty": 1.0,
        "num_beams": 4,
        "target_desc": "Standard conceptual exam prep"
    },
    "detailed": {
        "min_length": 220,
        "max_length": 480,
        "length_penalty": 0.8,
        "num_beams": 4,
        "target_desc": "Comprehensive academic study guide"
    }
}


class SummarizationService:
    """Orchestrates multi-tier summarization with transformer pipelines and chunking."""

    def __init__(self):
        pass

    def _fallback_extractive_summarize(self, text: str, mode: str) -> str:
        """Grounded extractive summarization fallback when transformer pipeline is offline.

        Selects top salient sentences using frequency-based sentence scoring,
        strictly maintaining factual source text without generating hallucinated statements.
        """
        sentences = split_into_sentences(text)
        if not sentences:
            return text

        sentence_counts = {
            "short": max(2, min(4, len(sentences) // 4)),
            "medium": max(4, min(8, len(sentences) // 2)),
            "detailed": max(6, min(14, int(len(sentences) * 0.75)))
        }
        target_count = min(len(sentences), sentence_counts.get(mode, 5))

        # Score sentences by word frequency
        words = [w.lower() for w in text.split() if len(w) > 3]
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        scored = []
        for idx, s in enumerate(sentences):
            s_words = [w.lower() for w in s.split() if len(w) > 3]
            score = sum(freq.get(w, 0) for w in s_words) / max(1, len(s_words))
            # Position bonus for introductory and concluding sentences
            if idx == 0:
                score *= 1.5
            scored.append((score, idx, s))

        # Select top scored sentences and restore original reading order
        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = scored[:target_count]
        top_sentences.sort(key=lambda x: x[1])

        return " ".join(s[2] for s in top_sentences)

    def summarize(
        self,
        text: str,
        summary_type: str = "medium",
        model_name: Optional[str] = None,
        max_chunk_tokens: int = 900
    ) -> Dict[str, Any]:
        """Generates a multi-tier summary (short, medium, or detailed) from document text.

        Args:
            text (str): Cleaned document text.
            summary_type (str): 'short', 'medium', or 'detailed'.
            model_name (str): Model checkpoint name or alias.
            max_chunk_tokens (int): Max context window per chunk.

        Returns:
            Dict[str, Any]: Generated summary and execution metadata.
        """
        start_time = time.time()
        mode = summary_type.lower().strip()
        if mode not in MODE_CONFIGS:
            mode = "medium"

        config = MODE_CONFIGS[mode]
        model_id = model_loader.resolve_model_identifier(model_name)

        # 1. Resolve Tokenizer
        tokenizer = None
        try:
            tokenizer = model_loader.get_tokenizer(model_id)
        except Exception as exc:
            logger.warning("Could not load tokenizer for '%s': %s", model_id, exc)

        source_tokens = count_tokens(text, tokenizer)

        # 2. Chunking
        chunks = chunking_service.create_chunks(
            text=text,
            tokenizer=tokenizer,
            max_tokens=max_chunk_tokens,
            overlap_tokens=100
        )

        total_chunks = len(chunks)
        logger.info(
            "Summarizing document (%d tokens, %d chunks) in '%s' mode using '%s'...",
            source_tokens, total_chunks, mode, model_id
        )

        # 3. Define the atomic chunk summarizer callable
        def run_chunk_inference(chunk_text: str, params: Dict[str, Any]) -> str:
            try:
                pipeline_obj = model_loader.get_summarization_pipeline(model_id)
                # Ensure input does not exceed max model length
                truncated_input = chunk_text
                if tokenizer:
                    encoded = tokenizer(chunk_text, max_length=1024, truncation=True, return_tensors="pt")
                    truncated_input = tokenizer.decode(encoded["input_ids"][0], skip_special_tokens=True)

                output = pipeline_obj(
                    truncated_input,
                    min_length=params.get("min_length", config["min_length"]),
                    max_length=params.get("max_length", config["max_length"]),
                    length_penalty=params.get("length_penalty", config["length_penalty"]),
                    num_beams=params.get("num_beams", config["num_beams"]),
                    do_sample=False
                )
                if output and isinstance(output, list) and "summary_text" in output[0]:
                    return output[0]["summary_text"].strip()
                return self._fallback_extractive_summarize(chunk_text, mode)
            except (ModelLoadError, Exception) as exc:
                logger.warning("Transformer inference unavailable (%s). Using extractive fallback: %s", model_id, exc)
                return self._fallback_extractive_summarize(chunk_text, mode)

        # 4. Execute Map-Reduce
        map_reduce_res = map_reduce_service.run_map_reduce(
            chunks=chunks,
            summarize_fn=run_chunk_inference,
            tokenizer=tokenizer,
            max_input_tokens=max_chunk_tokens,
            generation_params=config
        )

        final_summary = map_reduce_res["summary"].strip()
        generated_tokens = count_tokens(final_summary, tokenizer)
        duration = time.time() - start_time

        logger.info(
            "Summarization complete in %.2fs. Source: %d tokens, Output: %d tokens.",
            duration, source_tokens, generated_tokens
        )

        return {
            "summary_text": final_summary,
            "summary_type": mode,
            "model_name": model_id,
            "source_token_count": source_tokens,
            "generated_token_count": generated_tokens,
            "total_chunks": total_chunks,
            "reduction_passes": map_reduce_res["reduction_passes"],
            "processing_duration": duration
        }

    def generate_summary(self, text: str, mode: str = "medium", **kwargs) -> Dict[str, Any]:
        """Convenience wrapper for generating summaries with mode validation."""
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")
        clean_mode = (mode or "medium").lower().strip()
        if clean_mode not in MODE_CONFIGS:
            raise ValueError(f"Invalid mode '{mode}'. Choose from: short, medium, detailed.")
        res = self.summarize(text=text, summary_type=clean_mode, **kwargs)
        res["mode"] = clean_mode
        return res


# Global summarization service instance
summarization_service = SummarizationService()

