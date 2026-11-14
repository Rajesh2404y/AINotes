"""
Unit tests for Question Validation Service.
"""
from backend.app.ai.question_validator import question_validator


def test_validate_valid_mcq():
    q = {
        "question_text": "What is the primary role of an operating system kernel?",
        "question_type": "mcq",
        "options": ["Manage hardware resources", "Compile source code", "Render 3D graphics", "Format hard drives"],
        "correct_answer": "Manage hardware resources",
        "explanation": "The kernel coordinates low-level hardware resource allocation and execution.",
        "difficulty": "medium"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is True
    assert reason is None


def test_validate_mcq_invalid_options_count():
    q = {
        "question_text": "Which layer handles memory paging in modern architectures?",
        "question_type": "mcq",
        "options": ["Kernel", "User Space", "Hypervisor"],  # Only 3 options
        "correct_answer": "Kernel",
        "explanation": "The memory management unit and kernel handle paging.",
        "difficulty": "medium"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is False
    assert "MCQ requires exactly 4 options" in reason


def test_validate_mcq_duplicate_options():
    q = {
        "question_text": "Which algorithm is used for CPU process scheduling?",
        "question_type": "mcq",
        "options": ["Round Robin", "Round Robin", "Priority Scheduling", "Shortest Job First"],
        "correct_answer": "Round Robin",
        "explanation": "Round robin is a pre-emptive scheduling algorithm.",
        "difficulty": "easy"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is False
    assert "distinct" in reason


def test_validate_valid_true_false():
    q = {
        "question_text": "True or False: Virtual memory allows execution of processes exceeding physical RAM.",
        "question_type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "True",
        "explanation": "Virtual memory employs demand paging to simulate contiguous address spaces.",
        "difficulty": "easy"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is True


def test_validate_true_false_invalid_answer():
    q = {
        "question_text": "True or False: Deadlocks can be resolved automatically without intervention.",
        "question_type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "Maybe",
        "explanation": "Deadlock recovery usually requires process preemption.",
        "difficulty": "medium"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is False
    assert "must have correct answer 'True' or 'False'" in reason


def test_validate_fill_blank_missing_placeholder():
    q = {
        "question_text": "The central processing unit executes machine instructions.",
        "question_type": "fill_blank",
        "correct_answer": "CPU",
        "explanation": "The CPU is the central computational component.",
        "difficulty": "easy"
    }
    is_valid, reason = question_validator.validate_question(q)
    assert is_valid is False
    assert "must contain a blank placeholder" in reason


def test_validate_batch_deduplication():
    batch = [
        {
            "question_text": "What is the primary role of an operating system kernel?",
            "question_type": "mcq",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Valid explanation.",
            "difficulty": "easy"
        },
        {
            "question_text": "What is the primary role of an operating system kernel?",  # Duplicate
            "question_type": "mcq",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Valid explanation.",
            "difficulty": "easy"
        }
    ]
    valid = question_validator.validate_batch(batch)
    assert len(valid) == 1

