"""
NLLB-200 Transformer Translation Engine.
Optimized Singleton inference engine for facebook/nllb-200-distilled-600M.
Implements lazy loading, thread-safe synchronization, torch.inference_mode(),
batch processing, token-aware budgeting, and GPU/CPU device optimization.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

import torch

from backend.app.utils.language_utils import get_nllb_code

logger = logging.getLogger("ainotes.nllb_engine")


def is_testing_environment() -> bool:
    """Detects whether execution is running inside a test runner or testing environment."""
    return (
        os.getenv("FLASK_ENV") == "testing"
        or os.getenv("PYTEST_CURRENT_TEST") is not None
        or "pytest" in sys.modules
    )


class NLLBEngine:
    """Singleton inference manager for NLLB Transformer models."""

    _instance: Optional[NLLBEngine] = None
    _lock = threading.Lock()

    def __new__(cls) -> NLLBEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._model_name = os.getenv("TRANSLATION_MODEL", "facebook/nllb-200-distilled-600M")
        self._tokenizer: Optional[Any] = None
        self._model: Optional[Any] = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_lock = threading.Lock()
        self._model_load_attempted = False
        self._model_available = False
        self._model_error: Optional[str] = None
        self._initialized = True

        logger.info(
            "NLLBEngine initialized (target device: %s, model: %s)",
            self._device, self._model_name
        )

    def get_tokenizer(self) -> Optional[Any]:
        """Lazy thread-safe tokenizer acquisition."""
        if self._tokenizer is not None:
            return self._tokenizer

        if is_testing_environment():
            return None

        with self._load_lock:
            if self._tokenizer is None:
                try:
                    from transformers import AutoTokenizer
                    logger.info("Loading NLLB tokenizer for %s...", self._model_name)
                    # Attempt loading from local HF cache first for zero network latency
                    try:
                        self._tokenizer = AutoTokenizer.from_pretrained(
                            self._model_name,
                            local_files_only=True
                        )
                    except Exception:
                        self._tokenizer = AutoTokenizer.from_pretrained(
                            self._model_name,
                            local_files_only=False
                        )
                    logger.info("NLLB tokenizer loaded successfully (vocab: %d)", len(self._tokenizer))
                except Exception as exc:
                    logger.warning("Could not load NLLB tokenizer: %s", exc)
                    self._tokenizer = None

        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """Token-level counting using the cached NLLB tokenizer, falling back to word heuristic."""
        tok = self.get_tokenizer()
        if tok is not None:
            try:
                return len(tok.encode(text, add_special_tokens=False))
            except Exception:
                pass
        return max(1, len(text.split()) * 4 // 3)

    def is_model_loaded(self) -> bool:
        """Returns True if the PyTorch transformer model weights are actively resident in memory."""
        return self._model is not None and self._model_available

    def load_model(self) -> bool:
        """
        Loads the Seq2Seq transformer weights once with double-checked locking.
        Sets model to eval() mode and optimizes device threads.
        """
        if self._model_available and self._model is not None:
            return True

        if self._model_load_attempted and not self._model_available:
            return False

        with self._load_lock:
            if self._model_available and self._model is not None:
                return True

            self._model_load_attempted = True
            try:
                from transformers import AutoModelForSeq2SeqLM

                tok = self.get_tokenizer()
                if tok is None:
                    raise RuntimeError("Tokenizer required before model initialization.")

                logger.info("Loading NLLB model weights (%s) on %s...", self._model_name, self._device)

                # Configure CPU thread utilization for low inference latency
                if self._device == "cpu":
                    torch.set_num_threads(min(4, os.cpu_count() or 4))

                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self._model_name,
                    local_files_only=True  # Avoid blocking downloads on live requests if not cached
                )

                model.eval()

                if self._device == "cuda":
                    model = model.to("cuda")
                    if hasattr(torch, "float16"):
                        model = model.half()

                self._model = model
                self._model_available = True
                logger.info("NLLB Seq2Seq model loaded successfully on %s.", self._device)
                return True

            except Exception as exc:
                self._model_available = False
                self._model_error = str(exc)
                logger.warning(
                    "NLLB model weights not resident locally (%s); fast concurrent fallback active.",
                    exc
                )
                return False

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        batch_size: int = 4
    ) -> Optional[List[str]]:
        """
        Performs batched sequence-to-sequence translation using torch.inference_mode().
        Preserves original chunk ordering and skips gradient computations.
        """
        if not texts:
            return []

        if not self.load_model():
            return None

        tok = self.get_tokenizer()
        if tok is None or self._model is None:
            return None

        src_nllb = get_nllb_code(source_lang)
        tgt_nllb = get_nllb_code(target_lang)

        try:
            target_lang_id = tok.convert_tokens_to_ids(tgt_nllb)
            if target_lang_id is None or target_lang_id == tok.unk_token_id:
                logger.warning("Target language code '%s' not recognized by tokenizer.", tgt_nllb)
                return None

            results: List[str] = []

            with torch.inference_mode():
                for idx in range(0, len(texts), batch_size):
                    batch = texts[idx: idx + batch_size]
                    encoded = tok(
                        batch,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=512
                    ).to(self._device)

                    generated_tokens = self._model.generate(
                        **encoded,
                        forced_bos_token_id=target_lang_id,
                        max_new_tokens=256,
                        num_beams=1,  # Greedy search: 3-4x faster inference with high accuracy
                        early_stopping=True
                    )

                    decoded = tok.batch_decode(generated_tokens, skip_special_tokens=True)
                    for item in decoded:
                        results.append(item.strip())

            return results

        except Exception as exc:
            logger.exception("Error during NLLB batch inference: %s", exc)
            return None


# Global singleton instance
nllb_engine = NLLBEngine()
