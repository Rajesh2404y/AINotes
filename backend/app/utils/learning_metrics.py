"""Learning Analytics Metrics and Statistical Calculations.

Provides deterministic mathematical functions for evaluating topic accuracy,
performance categorization, learning trajectory trends, and difficulty adaptation.
"""

from typing import List, Tuple


def calculate_accuracy(correct: int, total: int) -> float:
    """Calculates percentage accuracy rounded to 2 decimal places.

    Args:
        correct: Number of correct answers.
        total: Total attempted questions.

    Returns:
        float: Accuracy percentage (0.0 to 100.0).
    """
    if not total or total <= 0:
        return 0.0
    return round((max(0, correct) / total) * 100.0, 2)


def classify_topic_status(
    accuracy: float,
    attempts: int,
    min_attempts: int = 3,
    weak_threshold: float = 50.0,
    moderate_threshold: float = 70.0,
    strong_threshold: float = 85.0,
) -> Tuple[str, str]:
    """Classifies learning performance status with explainable diagnostic evidence.

    Categories:
    - 'Insufficient Data': Fewer than min_attempts attempted.
    - 'Needs Improvement': Accuracy below weak_threshold (< 50%).
    - 'Developing': Accuracy between weak and moderate threshold (50% - 69.9%).
    - 'Good': Accuracy between moderate and strong threshold (70% - 84.9%).
    - 'Strong': Accuracy at or above strong threshold (>= 85%).

    Returns:
        Tuple[str, str]: (status_label, explainable_reason)
    """
    if attempts < min_attempts:
        return (
            "Insufficient Data",
            f"Only {attempts} question(s) attempted. A minimum of {min_attempts} attempts are required for reliable classification.",
        )

    if accuracy < weak_threshold:
        return (
            "Needs Improvement",
            f"Accuracy of {accuracy}% is below the weak-topic threshold ({weak_threshold}%). Targeted revision is recommended.",
        )
    elif accuracy < moderate_threshold:
        return (
            "Developing",
            f"Accuracy of {accuracy}% is between {weak_threshold}% and {moderate_threshold}%, demonstrating developing understanding.",
        )
    elif accuracy < strong_threshold:
        return (
            "Good",
            f"Accuracy of {accuracy}% is between {moderate_threshold}% and {strong_threshold}%, demonstrating solid comprehension.",
        )
    else:
        return (
            "Strong",
            f"Accuracy of {accuracy}% meets or exceeds the strong-topic threshold ({strong_threshold}%). Excellent topic mastery.",
        )


def calculate_trend(scores: List[float]) -> str:
    """Calculates learning performance trend across chronologically ordered scores.

    Args:
        scores: Chronological list of percentage scores.

    Returns:
        str: 'improving', 'declining', 'consistent', or 'insufficient_data'.
    """
    if not scores or len(scores) < 2:
        return "insufficient_data"

    # Split into earlier half and later half
    mid = len(scores) // 2
    earlier = scores[:mid]
    recent = scores[mid:]

    avg_earlier = sum(earlier) / len(earlier)
    avg_recent = sum(recent) / len(recent)
    delta = avg_recent - avg_earlier

    if delta >= 8.0:
        return "improving"
    elif delta <= -8.0:
        return "declining"
    else:
        return "consistent"


def recommend_adaptive_difficulty(
    topic_accuracy: float,
    attempts: int,
    min_attempts: int = 3,
) -> Tuple[str, str]:
    """Determines adaptive quiz difficulty tier with transparent diagnostic justification.

    Rules:
    - Insufficient data (< min_attempts): 'easy' for baseline calibration.
    - Low accuracy (< 50%): 'easy' to rebuild foundational concepts.
    - Moderate accuracy (50% - 79.9%): 'medium' for balanced practice.
    - High accuracy (>= 80% with >= min_attempts): 'hard' for cognitive challenge.

    Returns:
        Tuple[str, str]: (difficulty_tier, reason)
    """
    if attempts < min_attempts:
        return (
            "easy",
            f"Baseline calibration: Only {attempts} question(s) recorded in this topic. Easy difficulty is recommended to establish initial proficiency.",
        )

    if topic_accuracy < 50.0:
        return (
            "easy",
            f"Recent accuracy is {topic_accuracy}%, which is below 50%. Foundational Easy difficulty is recommended to reinforce core concepts.",
        )
    elif topic_accuracy < 80.0:
        return (
            "medium",
            f"Current accuracy is {topic_accuracy}% (between 50% and 80%). Medium difficulty is recommended for balanced comprehension and recall.",
        )
    else:
        return (
            "hard",
            f"Consistently strong performance with {topic_accuracy}% accuracy across {attempts} questions. Hard difficulty is recommended for higher-order reasoning.",
        )

