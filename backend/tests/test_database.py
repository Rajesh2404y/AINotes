"""Automated Tests for Database Schema Integrity, Relationships, and Cascades.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from backend.app.extensions import db
from backend.app.models import (
    User,
    Document,
    Summary,
    Quiz,
    Question,
    QuizAttempt,
    QuizResponse,
    Translation,
)


def test_user_persistence_and_unique_constraint(app):
    """Test user record persists and duplicate email violates unique constraint."""
    with app.app_context():
        u1 = User(full_name="Persist One", email="unique_test@example.com")
        u1.set_password("SecurePassword123!")
        db.session.add(u1)
        db.session.commit()

        assert u1.id is not None

        # Attempt to insert identical email directly via ORM
        u2 = User(full_name="Persist Two", email="unique_test@example.com")
        u2.set_password("SecurePassword123!")
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_full_relationship_chain_and_cascade(app):
    """Test full relational hierarchy across all 8 tables and verify cascade deletion."""
    with app.app_context():
        # 1. Create User
        user = User(full_name="Student Test", email="student_rel@example.com")
        user.set_password("Secure123!")
        db.session.add(user)
        db.session.commit()

        # 2. Create Document
        doc = Document(
            user_id=user.id,
            original_filename="chapter1.pdf",
            file_type="pdf",
            file_size=1024,
            extracted_text="Artificial intelligence is the simulation of human intelligence by machines.",
            processing_status="completed"
        )
        db.session.add(doc)
        db.session.commit()

        # 3. Create Summary
        summary = Summary(
            user_id=user.id,
            document_id=doc.id,
            summary_type="medium",
            summary_text="AI simulates human intelligence via computation.",
            keywords=["AI", "intelligence", "machines"],
            key_takeaways=["Simulates human cognitive functions", "Executed by machines"]
        )
        db.session.add(summary)
        db.session.commit()

        # 4. Create Translation
        trans = Translation(
            user_id=user.id,
            summary_id=summary.id,
            source_language="en",
            target_language="es",
            original_text=summary.summary_text,
            translated_text="La IA simula la inteligencia humana mediante computación."
        )
        db.session.add(trans)
        db.session.commit()

        # 5. Create Quiz
        quiz = Quiz(
            user_id=user.id,
            document_id=doc.id,
            summary_id=summary.id,
            quiz_type="mcq",
            difficulty="medium",
            total_questions=1
        )
        db.session.add(quiz)
        db.session.commit()

        # 6. Create Question
        question = Question(
            quiz_id=quiz.id,
            question_text="What does AI simulate?",
            question_type="mcq",
            options=["Human intelligence", "Atmospheric pressure", "Tectonic shift", "Photosynthesis"],
            correct_answer="Human intelligence",
            explanation="AI simulates human cognitive capabilities."
        )
        db.session.add(question)
        db.session.commit()

        # 7. Create Quiz Attempt
        attempt = QuizAttempt(
            user_id=user.id,
            quiz_id=quiz.id,
            score=1,
            total_questions=1,
            percentage=100.0
        )
        db.session.add(attempt)
        db.session.commit()

        # 8. Create Quiz Response
        response = QuizResponse(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer="Human intelligence",
            is_correct=True
        )
        db.session.add(response)
        db.session.commit()

        # Verify all entities are persisted
        assert doc.id is not None
        assert summary.id is not None
        assert trans.id is not None
        assert quiz.id is not None
        assert question.id is not None
        assert attempt.id is not None
        assert response.id is not None

        # Verify navigation across relationships
        assert summary.document.original_filename == "chapter1.pdf"
        assert quiz.summary.id == summary.id
        assert question.quiz.id == quiz.id
        assert attempt.responses.count() == 1

        # Delete user -> verify cascading deletes clean up child entities
        user_id = user.id
        db.session.delete(user)
        db.session.commit()

        assert Document.query.filter_by(user_id=user_id).first() is None
        assert Summary.query.filter_by(user_id=user_id).first() is None
        assert Quiz.query.filter_by(user_id=user_id).first() is None
        assert Translation.query.filter_by(user_id=user_id).first() is None
        assert QuizAttempt.query.filter_by(user_id=user_id).first() is None

