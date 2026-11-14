"""
Unit tests for Translation Chunking and Reassembly Service.
"""
from backend.app.ai.translation_chunking_service import translation_chunking_service


SAMPLE_ACADEMIC_SUMMARY = """
Machine learning models learn representations directly from data without explicit manual programming.
Supervised algorithms minimize loss using gradient-based optimization algorithms.

Unsupervised techniques discover clusters and latent factor spaces in high-dimensional distributions.
Deep architectures utilize backpropagation across multiple linear and non-linear layers.
"""


def test_chunking_and_reassembly():
    chunks = translation_chunking_service.create_translation_chunks(
        SAMPLE_ACADEMIC_SUMMARY,
        max_tokens=40
    )
    assert len(chunks) >= 2

    # Verify chunk structure
    for c in chunks:
        assert "chunk_index" in c
        assert "text" in c
        assert len(c["text"]) > 0

    # Simulate translation and reassembly
    translated_chunks = []
    for c in chunks:
        translated_chunks.append({
            "chunk_index": c["chunk_index"],
            "translated_text": f"[Trans] {c['text']}",
            "is_paragraph_end": c["is_paragraph_end"]
        })

    full_reassembled = translation_chunking_service.reassemble_chunks(translated_chunks)
    assert len(full_reassembled) > len(SAMPLE_ACADEMIC_SUMMARY)
    assert "[Trans]" in full_reassembled
    assert "\n\n" in full_reassembled  # Paragraph boundary preserved


def test_chunking_empty_text():
    chunks = translation_chunking_service.create_translation_chunks("")
    assert chunks == []
    reassembled = translation_chunking_service.reassemble_chunks([])
    assert reassembled == ""

