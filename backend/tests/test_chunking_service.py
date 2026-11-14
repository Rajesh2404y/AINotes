"""
Unit tests for Tokenizer-Aware Chunking Service.
"""
import pytest
from backend.app.ai.chunking_service import chunking_service
from backend.app.utils.token_utils import estimate_token_count, split_into_sentences


def test_split_into_sentences():
    text = "Machine learning is fascinating. It allows computers to learn from data. What about deep learning?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Machine learning is fascinating."
    assert sentences[1] == "It allows computers to learn from data."
    assert sentences[2] == "What about deep learning?"


def test_estimate_token_count():
    text = "Artificial intelligence and machine learning."
    count = estimate_token_count(text)
    assert count > 0
    assert abs(count - len(text.split())) <= 3


def test_chunk_text_single_chunk():
    text = "This is a short educational paragraph that easily fits into a single token budget."
    chunks = chunking_service.chunk_text(text, max_tokens=100)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == text
    assert chunks[0].token_count > 0


def test_chunk_text_multiple_chunks():
    # Construct a long text with multiple sentences
    sentences = [
        f"Sentence number {i} provides critical context regarding computational complexity and algorithms."
        for i in range(40)
    ]
    long_text = " ".join(sentences)

    chunks = chunking_service.chunk_text(long_text, max_tokens=60, overlap_tokens=15)
    assert len(chunks) > 1

    # Verify indices are sequential
    for i, c in enumerate(chunks):
        assert c.index == i
        assert len(c.text) > 0
        assert c.token_count <= 80  # Max tokens plus sentence margin


def test_chunk_text_empty_input():
    chunks = chunking_service.chunk_text("")
    assert chunks == []
