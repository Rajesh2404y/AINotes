"""Unit tests for Learning Analytics Metrics.
"""

from backend.app.utils.learning_metrics import (
    calculate_accuracy,
    calculate_trend,
    classify_topic_status,
    recommend_adaptive_difficulty,
)


def test_calculate_accuracy():
    """Verifies percentage accuracy calculation and zero-division handling."""
    assert calculate_accuracy(0, 0) == 0.0
    assert calculate_accuracy(5, 0) == 0.0
    assert calculate_accuracy(0, 10) == 0.0
    assert calculate_accuracy(5, 10) == 50.0
    assert calculate_accuracy(1, 3) == 33.33
    assert calculate_accuracy(10, 10) == 100.0


def test_classify_topic_status_insufficient_attempts():
    """Verifies that fewer than minimum attempts yield 'Insufficient Data'."""
    status, reason = classify_topic_status(accuracy=20.0, attempts=2, min_attempts=3)
    assert status == "Insufficient Data"
    assert "minimum of 3" in reason


def test_classify_topic_status_threshold_boundaries():
    """Verifies exact threshold boundaries for weak, moderate, good, and strong classifications."""
    # Weak: < 50.0
    status, reason = classify_topic_status(accuracy=49.9, attempts=5)
    assert status == "Needs Improvement"

    # Moderate: 50.0 to < 70.0
    status, _ = classify_topic_status(accuracy=50.0, attempts=5)
    assert status == "Developing"

    status, _ = classify_topic_status(accuracy=69.9, attempts=5)
    assert status == "Developing"

    # Good: 70.0 to < 85.0
    status, _ = classify_topic_status(accuracy=70.0, attempts=5)
    assert status == "Good"

    status, _ = classify_topic_status(accuracy=84.9, attempts=5)
    assert status == "Good"

    # Strong: >= 85.0
    status, _ = classify_topic_status(accuracy=85.0, attempts=5)
    assert status == "Strong"

    status, _ = classify_topic_status(accuracy=100.0, attempts=5)
    assert status == "Strong"


def test_calculate_trend():
    """Verifies longitudinal score trajectory calculations."""
    assert calculate_trend([]) == "insufficient_data"
    assert calculate_trend([80.0]) == "insufficient_data"

    # Steady / consistent
    assert calculate_trend([70.0, 72.0, 71.0, 73.0]) == "consistent"

    # Improving (recent half >= earlier half + 8)
    assert calculate_trend([50.0, 50.0, 80.0, 85.0]) == "improving"

    # Declining (recent half <= earlier half - 8)
    assert calculate_trend([90.0, 85.0, 60.0, 55.0]) == "declining"


def test_recommend_adaptive_difficulty():
    """Verifies adaptive difficulty recommendation rules."""
    # Insufficient attempts
    diff, reason = recommend_adaptive_difficulty(topic_accuracy=95.0, attempts=1, min_attempts=3)
    assert diff == "easy"
    assert "Baseline" in reason

    # Low accuracy (< 50%) -> easy
    diff, reason = recommend_adaptive_difficulty(topic_accuracy=42.0, attempts=5)
    assert diff == "easy"
    assert "42.0%" in reason

    # Moderate accuracy (50% - 79.9%) -> medium
    diff, reason = recommend_adaptive_difficulty(topic_accuracy=65.0, attempts=5)
    assert diff == "medium"
    assert "65.0%" in reason

    # High accuracy (>= 80%) -> hard
    diff, reason = recommend_adaptive_difficulty(topic_accuracy=88.0, attempts=6)
    assert diff == "hard"
    assert "88.0%" in reason

