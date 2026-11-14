"""
Unit tests for Quiz Quality and Deduplication Service.
"""
from backend.app.ai.quiz_quality_service import quiz_quality_service


def test_assess_source_sufficiency():
    short_text = "This is a five word note."
    ok, err = quiz_quality_service.assess_source_sufficiency(short_text, 10)
    assert ok is False
    assert "insufficient" in err

    long_text = " ".join(["Computers analyze data and execute complex algorithmic procedures in parallel."] * 20)
    ok, err = quiz_quality_service.assess_source_sufficiency(long_text, 5)
    assert ok is True
    assert err is None


def test_question_similarity_and_deduplication():
    q1 = "What is the primary role of the CPU in modern computing?"
    q2 = "What is the primary role of the CPU in modern computing systems?"  # High similarity
    q3 = "How does virtual memory paging prevent memory fragmentation?"   # Low similarity

    sim_high = quiz_quality_service.calculate_question_similarity(q1, q2)
    sim_low = quiz_quality_service.calculate_question_similarity(q1, q3)

    assert sim_high > 0.70
    assert sim_low < 0.30

    questions = [
        {"question_text": q1, "question_type": "one_word"},
        {"question_text": q2, "question_type": "one_word"},
        {"question_text": q3, "question_type": "one_word"}
    ]
    deduped = quiz_quality_service.deduplicate_questions(questions, max_similarity=0.70)
    assert len(deduped) == 2
    assert deduped[0]["question_text"] == q1
    assert deduped[1]["question_text"] == q3

