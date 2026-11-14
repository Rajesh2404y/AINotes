"""Unit and integration tests for Learning Performance Analysis and Topic Mapping.
"""

from backend.app.ai.learning_analysis_service import learning_analysis_service
from backend.app.extensions import db
from backend.app.models.document import Document
from backend.app.models.question import Question
from backend.app.models.quiz import Quiz
from backend.app.models.quiz_attempt import QuizAttempt
from backend.app.models.quiz_response import QuizResponse
from backend.app.models.summary import Summary
from backend.app.models.user import User


def test_empty_learning_analysis(app):
    """Verifies that a user with no quiz attempts receives a clean, non-null analysis structure."""
    with app.app_context():
        user = User(full_name="New Student", email="student_new@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        analysis = learning_analysis_service.analyze_user_learning(user.id)
        assert analysis["total_quizzes_attempted"] == 0
        assert analysis["average_quiz_score"] == 0.0
        assert analysis["topic_performance"] == {}
        assert analysis["weak_topics"] == []
        assert analysis["strong_topics"] == []


def test_topic_mapping_keyword_and_definitions(app):
    """Verifies mapping a question to a topic via Summary definitions and keywords."""
    with app.app_context():
        user = User(full_name="Topic Student", email="topic_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        doc = Document(user_id=user.id, original_filename="Computer_Science.pdf", file_type="pdf")
        db.session.add(doc)
        db.session.commit()

        summary = Summary(
            user_id=user.id,
            document_id=doc.id,
            summary_type="medium",
            summary_text="Summary text",
            definitions=[{"term": "Neural Networks", "definition": "Brain-inspired computing units"}],
            keywords=["Backpropagation", "Gradient Descent"],
        )
        db.session.add(summary)
        db.session.commit()

        quiz = Quiz(
            user_id=user.id,
            document_id=doc.id,
            summary_id=summary.id,
            quiz_type="mcq",
            difficulty="medium",
            total_questions=2,
        )
        db.session.add(quiz)
        db.session.commit()

        q1 = Question(
            quiz_id=quiz.id,
            question_text="How do Neural Networks process distributed activations?",
            question_type="mcq",
            correct_answer="Through weights",
        )
        q2 = Question(
            quiz_id=quiz.id,
            question_text="What role does Backpropagation play in optimizing loss?",
            question_type="mcq",
            correct_answer="Calculates gradients",
        )
        q3 = Question(
            quiz_id=quiz.id,
            question_text="Describe general computational theory without matched terms.",
            question_type="mcq",
            correct_answer="Theory",
        )
        db.session.add_all([q1, q2, q3])
        db.session.commit()

        # Check topic mapping
        assert learning_analysis_service.map_question_to_topic(q1, quiz=quiz) == "Neural Networks"
        assert learning_analysis_service.map_question_to_topic(q2, quiz=quiz) == "Backpropagation"
        assert learning_analysis_service.map_question_to_topic(q3, quiz=quiz) == "Computer Science"


def test_multi_attempt_topic_accuracy_and_metrics(app):
    """Verifies topic aggregation, accuracy, and difficulty breakdown across quiz attempts."""
    with app.app_context():
        user = User(full_name="Assessment Student", email="assessment_stu@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

        doc = Document(user_id=user.id, original_filename="Algorithms.pdf", file_type="pdf")
        db.session.add(doc)
        db.session.commit()

        quiz = Quiz(
            user_id=user.id,
            document_id=doc.id,
            quiz_type="mixed",
            difficulty="medium",
            total_questions=4,
        )
        db.session.add(quiz)
        db.session.commit()

        q1 = Question(
            quiz_id=quiz.id,
            question_text="Explain Sorting Algorithms complexity.",
            question_type="mcq",
            correct_answer="O(n log n)",
            source_reference="Document: Sorting",
        )
        q2 = Question(
            quiz_id=quiz.id,
            question_text="What is Quick Sort pivot strategy?",
            question_type="one_word",
            correct_answer="Median",
            source_reference="Document: Sorting",
        )
        q3 = Question(
            quiz_id=quiz.id,
            question_text="Is Bubble Sort stable?",
            question_type="true_false",
            correct_answer="True",
            source_reference="Document: Sorting",
        )
        q4 = Question(
            quiz_id=quiz.id,
            question_text="Fill in the blank: Merge sort uses ______ and conquer.",
            question_type="fill_blank",
            correct_answer="divide",
            source_reference="Document: Sorting",
        )
        db.session.add_all([q1, q2, q3, q4])
        db.session.commit()

        # Create Attempt 1: 3 out of 4 correct (75%)
        att1 = QuizAttempt(user_id=user.id, quiz_id=quiz.id, score=3, total_questions=4, percentage=75.0)
        db.session.add(att1)
        db.session.commit()

        r1 = QuizResponse(attempt_id=att1.id, question_id=q1.id, selected_answer="O(n log n)", is_correct=True)
        r2 = QuizResponse(attempt_id=att1.id, question_id=q2.id, selected_answer="Median", is_correct=True)
        r3 = QuizResponse(attempt_id=att1.id, question_id=q3.id, selected_answer="True", is_correct=True)
        r4 = QuizResponse(attempt_id=att1.id, question_id=q4.id, selected_answer="multiply", is_correct=False)
        db.session.add_all([r1, r2, r3, r4])
        db.session.commit()

        analysis = learning_analysis_service.analyze_user_learning(user.id)
        assert analysis["total_quizzes_attempted"] == 1
        assert analysis["average_quiz_score"] == 75.0
        assert "Algorithms" in analysis["topic_performance"]
        topic_info = analysis["topic_performance"]["Algorithms"]
        assert topic_info["attempted_questions"] == 4
        assert topic_info["correct_answers"] == 3
        assert topic_info["accuracy"] == 75.0
        assert topic_info["performance_status"] == "Good"
