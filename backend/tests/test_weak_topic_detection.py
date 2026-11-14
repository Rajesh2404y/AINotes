"""Unit tests for Weak and Strong Topic Detection Service.
"""

from backend.app.ai.weak_topic_detection import weak_topic_detection_service


def test_detect_topic_classifications_empty():
    """Verifies empty classification payload handling."""
    res = weak_topic_detection_service.detect_topic_classifications({})
    assert res["weak_topics"] == []
    assert res["strong_topics"] == []
    assert res["has_deficits"] is False


def test_detect_topic_classifications_boundaries():
    """Verifies classification groupings and deficit flags."""
    mock_analysis = {
        "weak_topics": [{"topic": "Recursion", "accuracy": 40.0, "attempted_questions": 5}],
        "moderate_topics": [{"topic": "Pointers", "accuracy": 65.0, "attempted_questions": 6}],
        "good_topics": [{"topic": "Hashing", "accuracy": 78.0, "attempted_questions": 5}],
        "strong_topics": [{"topic": "Variables", "accuracy": 92.0, "attempted_questions": 5}],
        "insufficient_data_topics": [{"topic": "Graphs", "accuracy": 100.0, "attempted_questions": 1}],
        "topic_performance": {
            "Recursion": {"accuracy": 40.0, "trend": "declining"},
            "Variables": {"accuracy": 92.0, "trend": "improving"},
        },
        "repeated_incorrect_count": 2,
    }

    result = weak_topic_detection_service.detect_topic_classifications(mock_analysis)
    assert len(result["weak_topics"]) == 1
    assert result["weak_topics"][0]["topic"] == "Recursion"
    assert len(result["strong_topics"]) == 1
    assert result["strong_topics"][0]["topic"] == "Variables"
    assert result["has_deficits"] is True
    assert len(result["declining_topics"]) == 1
    assert result["declining_topics"][0]["topic"] == "Recursion"
    assert len(result["improving_topics"]) == 1
    assert result["improving_topics"][0]["topic"] == "Variables"
    assert result["repeated_mistakes"] == 2

