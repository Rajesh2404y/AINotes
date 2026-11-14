"""
Unit tests for AI Multi-Tier Summarization Service.
"""
import pytest
from backend.app.ai.summarization_service import summarization_service


SAMPLE_TEXT = """
Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural
intelligence of humans and animals. AI research has been defined as the field of study of intelligent
agents, which refers to any system that perceives its environment and takes actions that maximize
its chance of achieving its goals. The term "artificial intelligence" had previously been used to
describe machines that mimic and display "human" cognitive skills that are associated with the human mind,
such as "learning" and "problem-solving". This definition has since been rejected by major AI researchers
who now describe AI in terms of rationality and acting rationally, which does not limit how intelligence
can be articulated. Machine learning is a prominent subset of AI focused on algorithms that learn from
historical data.
"""


def test_summarization_modes():
    # Test short mode
    res_short = summarization_service.generate_summary(SAMPLE_TEXT, mode="short")
    assert res_short["mode"] == "short"
    assert len(res_short["summary_text"]) > 0
    assert res_short["generated_token_count"] > 0

    # Test medium mode
    res_med = summarization_service.generate_summary(SAMPLE_TEXT, mode="medium")
    assert res_med["mode"] == "medium"
    assert len(res_med["summary_text"]) > 0

    # Test detailed mode
    res_det = summarization_service.generate_summary(SAMPLE_TEXT, mode="detailed")
    assert res_det["mode"] == "detailed"
    assert len(res_det["summary_text"]) > 0


def test_summarization_invalid_mode():
    with pytest.raises(ValueError, match="Invalid mode"):
        summarization_service.generate_summary(SAMPLE_TEXT, mode="super_long")


def test_summarization_empty_text():
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        summarization_service.generate_summary("   ", mode="medium")
