"""
Unit tests for Summary Quality Evaluation Service.
"""
from backend.app.ai.summary_quality_service import summary_quality_service


def test_summary_quality_metrics():
    source = (
        "Operating systems coordinate hardware resources and offer an execution platform for applications. "
        "The kernel serves as the central control module managing CPU scheduling, memory allocation, and I/O devices. "
        "Process synchronization prevents race conditions when concurrent processes access shared memory."
    )
    summary = (
        "Operating systems coordinate hardware resources. The kernel manages CPU scheduling and memory allocation. "
        "Process synchronization prevents race conditions."
    )

    result = summary_quality_service.evaluate(source, summary)
    assert result["source_word_count"] > 0
    assert result["summary_word_count"] > 0
    assert 0 <= result["compression_ratio"] <= 100
    assert result["grounding_score"] >= 80.0
    assert result["quality_grade"] in {"HIGH", "MEDIUM", "LOW"}


def test_summary_quality_empty():
    result = summary_quality_service.evaluate("", "")
    assert result["quality_grade"] == "LOW"
    assert result["compression_ratio"] == 0.0
