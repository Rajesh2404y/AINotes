"""
Unit tests for Question Generation Service.
"""
from backend.app.ai.question_generation_service import question_generation_service


SAMPLE_CHAPTER = """
Machine learning is defined as an algorithmic paradigm focused on learning models from empirical data.
Supervised learning refers to the process of training algorithms on labeled datasets where desired outputs are known.
Unsupervised learning is a type of algorithm that detects hidden patterns in unlabeled data.
Deep learning denotes neural networks with multiple layers capable of hierarchical representation learning.
In supervised learning, models iteratively minimize a loss function using gradient descent.
Clustering and principal component analysis are prominent examples of unsupervised techniques.
Overfitting occurs when a statistical model learns noise and details in training data to the extent that it negatively impacts performance on new data.
Regularization techniques such as dropout and weight decay help prevent overfitting in deep neural networks.
"""


def test_generate_quiz_questions_all_types():
    questions = question_generation_service.generate_quiz_questions(
        source_text=SAMPLE_CHAPTER,
        question_types=["mcq", "true_false", "one_word", "fill_blank"],
        difficulty="medium",
        total_questions=8
    )

    assert len(questions) >= 4
    found_types = {q["question_type"] for q in questions}
    assert "mcq" in found_types or "true_false" in found_types

    for q in questions:
        assert len(q["question_text"]) > 10
        assert q["correct_answer"]
        assert q["explanation"]
        assert q["difficulty"] == "medium"
        if q["question_type"] == "mcq":
            assert len(q["options"]) == 4
        elif q["question_type"] == "true_false":
            assert q["options"] == ["True", "False"]
        elif q["question_type"] == "fill_blank":
            assert "______" in q["question_text"]


def test_generate_quiz_questions_mcq_only():
    questions = question_generation_service.generate_quiz_questions(
        source_text=SAMPLE_CHAPTER,
        question_types=["mcq"],
        difficulty="easy",
        total_questions=5
    )
    assert len(questions) >= 2
    for q in questions:
        assert q["question_type"] == "mcq"
        assert len(q["options"]) == 4
        assert q["correct_answer"] in q["options"]


def test_generate_quiz_questions_difficulties():
    for diff in ["easy", "medium", "hard"]:
        questions = question_generation_service.generate_quiz_questions(
            source_text=SAMPLE_CHAPTER,
            question_types=["mcq", "true_false"],
            difficulty=diff,
            total_questions=3
        )
        assert len(questions) > 0
        for q in questions:
            assert q["difficulty"] == diff

