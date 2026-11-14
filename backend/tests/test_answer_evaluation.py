"""
Unit tests for Answer Evaluation Service.
"""
from backend.app.ai.answer_evaluation_service import answer_evaluation_service


def test_evaluate_mcq():
    options = ["Supervised", "Unsupervised", "Reinforcement", "Evolutionary"]
    # Option text match
    assert answer_evaluation_service.evaluate_mcq("Supervised", "Supervised", options) is True
    assert answer_evaluation_service.evaluate_mcq("supervised ", "Supervised", options) is True
    # Letter match
    assert answer_evaluation_service.evaluate_mcq("A", "Supervised", options) is True
    assert answer_evaluation_service.evaluate_mcq("B", "Supervised", options) is False
    assert answer_evaluation_service.evaluate_mcq("Reinforcement", "Supervised", options) is False


def test_evaluate_true_false():
    assert answer_evaluation_service.evaluate_true_false("True", "True") is True
    assert answer_evaluation_service.evaluate_true_false("true", "True") is True
    assert answer_evaluation_service.evaluate_true_false("T", "True") is True
    assert answer_evaluation_service.evaluate_true_false("1", "True") is True
    assert answer_evaluation_service.evaluate_true_false("False", "True") is False
    assert answer_evaluation_service.evaluate_true_false("f", "False") is True
    assert answer_evaluation_service.evaluate_true_false("0", "False") is True


def test_evaluate_one_word():
    assert answer_evaluation_service.evaluate_one_word("Kernel", "Kernel") is True
    assert answer_evaluation_service.evaluate_one_word("kernel   ", "Kernel") is True
    assert answer_evaluation_service.evaluate_one_word("Operating System", "operating system") is True
    # With alternative
    assert answer_evaluation_service.evaluate_one_word("ML", "Machine Learning", acceptable_alternatives=["ML"]) is True
    assert answer_evaluation_service.evaluate_one_word("Database", "Kernel") is False


def test_calculate_score():
    questions = [
        {"id": 1, "question_text": "Q1", "question_type": "mcq", "options": ["A", "B", "C", "D"], "correct_answer": "A", "explanation": "E1"},
        {"id": 2, "question_text": "Q2", "question_type": "true_false", "options": ["True", "False"], "correct_answer": "True", "explanation": "E2"},
        {"id": 3, "question_text": "Q3", "question_type": "one_word", "options": None, "correct_answer": "Paging", "explanation": "E3"},
        {"id": 4, "question_text": "Q4", "question_type": "fill_blank", "options": None, "correct_answer": "Thread", "explanation": "E4"},
    ]
    # 3 correct, 1 incorrect
    submissions = {
        1: "A",
        2: "True",
        3: "paging",
        4: "Process"  # Incorrect
    }

    result = answer_evaluation_service.calculate_score(questions, submissions)
    assert result["score"] == 3
    assert result["total_questions"] == 4
    assert result["percentage"] == 75.0
    assert len(result["evaluations"]) == 4
    assert result["evaluations"][0]["is_correct"] is True
    assert result["evaluations"][3]["is_correct"] is False


def test_calculate_score_empty():
    result = answer_evaluation_service.calculate_score([], {})
    assert result["score"] == 0
    assert result["total_questions"] == 0
    assert result["percentage"] == 0.0

