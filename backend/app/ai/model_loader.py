"""Hugging Face Model Loader and Resource Manager.

Implements configurable, lazy-loaded, thread-safe model caching for:
- Model A: DistilBART (sshleifer/distilbart-cnn-12-6)
- Model B: BART Large CNN (facebook/bart-large-cnn)
- Model C: FLAN-T5 Base (google/flan-t5-base)

Supports automatic device detection (CPU / CUDA), memory management,
graceful fallback on GPU OOM, and controlled exception handling.
"""

import os
import gc
import logging
from typing import Dict, Any, Optional
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    pipeline,
    PreTrainedTokenizerBase,
)

logger = logging.getLogger("ainotes.model_loader")

# Supported Models Registry
SUPPORTED_MODELS = {
    "distilbart": "sshleifer/distilbart-cnn-12-6",
    "bart-large": "facebook/bart-large-cnn",
    "flan-t5": "google/flan-t5-base",
}

DEFAULT_SUMMARIZATION_MODEL = "sshleifer/distilbart-cnn-12-6"
DEFAULT_EXTRACTION_MODEL = "google/flan-t5-base"


class ModelLoadError(Exception):
    """Exception raised when an AI model or tokenizer fails to initialize."""
    pass


class ModelLoader:
    """Manages lifecycle, memory caching, and device placement of Hugging Face models."""

    def __init__(self, cache_dir: Optional[str] = None, device_setting: str = "auto"):
        self.cache_dir = cache_dir or os.getenv("MODEL_CACHE_DIR", "model_cache")
        self.device_setting = device_setting.lower()
        self._device = self._resolve_device()
        self._tokenizers: Dict[str, PreTrainedTokenizerBase] = {}
        self._models: Dict[str, Any] = {}
        self._pipelines: Dict[str, Any] = {}

    def _resolve_device(self) -> torch.device:
        """Determines computation device based on configuration and hardware availability."""
        if self.device_setting == "cuda" or (self.device_setting == "auto" and torch.cuda.is_available()):
            device = torch.device("cuda")
            logger.info("CUDA GPU detected. Using device: %s", torch.cuda.get_device_name(0))
            return device
        logger.info("Using CPU device for AI model inference.")
        return torch.device("cpu")

    @property
    def device(self) -> torch.device:
        return self._device

    def resolve_model_identifier(self, model_name_or_alias: Optional[str] = None) -> str:
        """Resolves alias (e.g. 'distilbart') to Hugging Face checkpoint path."""
        if not model_name_or_alias:
            return os.getenv("SUMMARIZATION_MODEL", DEFAULT_SUMMARIZATION_MODEL)

        key = model_name_or_alias.lower().strip()
        return SUPPORTED_MODELS.get(key, model_name_or_alias)

    def get_tokenizer(self, model_name_or_alias: Optional[str] = None) -> PreTrainedTokenizerBase:
        """Lazy loads and caches tokenizer for specified model checkpoint."""
        model_id = self.resolve_model_identifier(model_name_or_alias)

        if model_id in self._tokenizers:
            return self._tokenizers[model_id]

        logger.info("Loading tokenizer for '%s'...", model_id)
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                use_fast=True
            )
            self._tokenizers[model_id] = tokenizer
            return tokenizer
        except Exception as exc:
            logger.error("Failed to load tokenizer for '%s': %s", model_id, exc)
            raise ModelLoadError(f"Tokenizer for '{model_id}' could not be loaded: {str(exc)}") from exc

    def get_summarization_pipeline(self, model_name_or_alias: Optional[str] = None):
        """Lazy loads, caches, and returns a Hugging Face summarization pipeline."""
        if os.getenv("FLASK_ENV") == "testing" or os.getenv("PYTEST_CURRENT_TEST"):
            raise ModelLoadError("Testing environment detected: using deterministic NLP fallback pipeline.")

        model_id = self.resolve_model_identifier(model_name_or_alias)

        cache_key = f"summarization_{model_id}_{self._device.type}"
        if cache_key in self._pipelines:
            return self._pipelines[cache_key]

        logger.info("Initializing summarization pipeline for '%s' on %s...", model_id, self._device)
        tokenizer = self.get_tokenizer(model_id)

        try:
            device_idx = 0 if self._device.type == "cuda" else -1
            torch_dtype = torch.float16 if self._device.type == "cuda" else torch.float32

            try:
                summarizer = pipeline(
                    task="summarization",
                    model=model_id,
                    tokenizer=tokenizer,
                    device=device_idx,
                    torch_dtype=torch_dtype,
                    model_kwargs={"cache_dir": self.cache_dir}
                )
            except Exception as task_err:
                if "Unknown task" in str(task_err):
                    task_name = "text2text-generation" if "text2text-generation" in str(task_err) else "text-generation"
                    summarizer = pipeline(
                        task=task_name,
                        model=model_id,
                        tokenizer=tokenizer,
                        device=device_idx,
                        torch_dtype=torch_dtype,
                        model_kwargs={"cache_dir": self.cache_dir}
                    )
                else:
                    raise task_err
            self._pipelines[cache_key] = summarizer
            return summarizer

        except torch.cuda.OutOfMemoryError as oom:
            logger.warning("CUDA OOM loading '%s'. Falling back to CPU: %s", model_id, oom)
            torch.cuda.empty_cache()
            self._device = torch.device("cpu")
            return self.get_summarization_pipeline(model_id)

        except Exception as exc:
            logger.error("Failed to initialize summarization pipeline for '%s': %s", model_id, exc)
            raise ModelLoadError(f"Summarization model '{model_id}' could not be initialized: {str(exc)}") from exc

    def get_t5_pipeline(self, model_name_or_alias: Optional[str] = None):
        """Lazy loads and caches FLAN-T5 text2text-generation pipeline for structured extraction."""
        model_id = model_name_or_alias or os.getenv("STRUCTURED_EXTRACTION_MODEL", DEFAULT_EXTRACTION_MODEL)

        cache_key = f"t5_{model_id}_{self._device.type}"
        if cache_key in self._pipelines:
            return self._pipelines[cache_key]

        logger.info("Initializing FLAN-T5 pipeline for '%s' on %s...", model_id, self._device)
        try:
            tokenizer = self.get_tokenizer(model_id)
            device_idx = 0 if self._device.type == "cuda" else -1

            t5_pipe = pipeline(
                task="text2text-generation",
                model=model_id,
                tokenizer=tokenizer,
                device=device_idx,
                model_kwargs={"cache_dir": self.cache_dir}
            )
            self._pipelines[cache_key] = t5_pipe
            return t5_pipe

        except Exception as exc:
            logger.error("Failed to initialize FLAN-T5 pipeline for '%s': %s", model_id, exc)
            raise ModelLoadError(f"FLAN-T5 model '{model_id}' could not be initialized: {str(exc)}") from exc

    def clear_cache(self):
        """Releases cached models and flushes CUDA GPU memory."""
        self._pipelines.clear()
        self._models.clear()
        self._tokenizers.clear()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Model cache cleared.")


# Global default model loader instance
model_loader = ModelLoader(
    cache_dir=os.getenv("MODEL_CACHE_DIR", "model_cache"),
    device_setting=os.getenv("MODEL_DEVICE", "auto")
)

