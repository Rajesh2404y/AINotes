"""
Integration tests for Quiz REST API Routes.
"""
import pytest
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.quiz import Quiz
from backend.app.models.question import Question


SAMPLE_CHAPTER = """
Machine learning is defined as a branch of artificial intelligence focused on learning models from empirical data.
Supervised learning refers to the process of training algorithms on labeled datasets where ground truth outputs are provided.
Unsupervised learning is a type of algorithm that detects hidden structures in unlabeled data.
Deep learning denotes neural networks with multiple layers capable of hierarchical representation learning.
In supervised learning, models iteratively optimize weights by minimizing empirical loss through backpropagation.
Clustering and dimensionality reduction are two prominent examples of unsupervised techniques.
"""


@pytest.fixture
def quiz_user(app):
    with app.app_context():
        user = User.query.filter_by(email="quiz_tester@example.com").first()
        if not user:
            user = User(
                full_name="Quiz Tester",
                email="quiz_tester@example.com",
                is_active=True
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def other_quiz_user(app):
    with app.app_context():
        user = User.query.filter_by(email="other_quiz_user@example.com").first()
        if not user:
            user = User(
                full_name="Other Quiz User",
                email="other_quiz_user@example.com",
                is_active=True
            )
            user.set_password("StudentPassword123!")
            db.session.add(user)
            db.session.commit()
        return user.id


@pytest.fixture
def user_jwt(app, quiz_user):
    with app.app_context():
        return create_access_token(identity=str(quiz_user))


@pytest.fixture
def other_jwt(app, other_quiz_user):
    with app.app_context():
        return create_access_token(identity=str(other_quiz_user))


@pytest.fixture
def doc_fixture(app, quiz_user):
    with app.app_context():
        doc = Document(
            user_id=quiz_user,
            original_filename="ml_chapter.txt",
            stored_filename="ml_chapter.txt",
            file_type="txt",
            file_size=1024,
            processing_status="COMPLETED",
            extraction_quality="HIGH",
            extracted_text=SAMPLE_CHAPTER,
            total_words=75
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id


def test_generate_quiz_unauthorized(client):
    res = client.post("/api/quizzes/generate", json={"document_id": 1})
    assert res.status_code == 401


def test_generate_quiz_missing_source(client, user_jwt):
    res = client.post(
        "/api/quizzes/generate",
        json={"difficulty": "medium"},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert res.status_code == 400


def test_generate_quiz_cross_user_forbidden(client, other_jwt, doc_fixture):
    res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "difficulty": "medium"},
        headers={"Authorization": f"Bearer {other_jwt}"}
    )
    assert res.status_code == 403


def test_generate_quiz_success(client, user_jwt, doc_fixture):
    res = client.post(
        "/api/quizzes/generate",
        json={
            "document_id": doc_fixture,
            "question_types": ["mcq", "true_false"],
            "difficulty": "medium",
            "total_questions": 5
        },
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["id"] is not None
    assert data["total_questions"] >= 2
    assert "questions" in data
    # Security requirement: correct answers must NOT be exposed before submission!
    for q in data["questions"]:
        assert "correct_answer" not in q


def test_get_quiz_protects_answers(client, user_jwt, doc_fixture):
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 4},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    res = client.get(f"/api/quizzes/{quiz_id}", headers={"Authorization": f"Bearer {user_jwt}"})
    assert res.status_code == 200
    quiz_data = res.get_json()["data"]
    assert quiz_data["id"] == quiz_id
    for q in quiz_data["questions"]:
        assert "correct_answer" not in q
        assert "explanation" not in q


def test_get_quiz_cross_user_forbidden(client, other_jwt, doc_fixture, user_jwt):
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 3},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    res = client.get(f"/api/quizzes/{quiz_id}", headers={"Authorization": f"Bearer {other_jwt}"})
    assert res.status_code == 403


def test_list_quizzes(client, user_jwt, doc_fixture):
    # Ensure at least 1 quiz exists
    client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 3},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )

    res = client.get("/api/quizzes", headers={"Authorization": f"Bearer {user_jwt}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "quizzes" in data
    assert len(data["quizzes"]) >= 1
    assert "pagination" in data


def test_submit_quiz_and_get_results(client, user_jwt, doc_fixture, app):
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 4},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    with app.app_context():
        quiz = db.session.get(Quiz, quiz_id)
        questions = quiz.questions.all()
        q1_id = questions[0].id
        q1_answer = questions[0].correct_answer

    # Submit answer
    submit_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        json={
            "responses": [
                {"question_id": q1_id, "answer": q1_answer}
            ]
        },
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.get_json()["data"]
    assert sub_data["attempt_id"] is not None
    assert sub_data["score"] >= 1
    assert "results" in sub_data

    attempt_id = sub_data["attempt_id"]

    # Verify GET /api/quizzes/attempts/<id>
    att_res = client.get(f"/api/quizzes/attempts/{attempt_id}", headers={"Authorization": f"Bearer {user_jwt}"})
    assert att_res.status_code == 200
    att_data = att_res.get_json()["data"]
    assert att_data["id"] == attempt_id
    assert att_data["score"] == sub_data["score"]
    assert len(att_data["responses"]) >= 1


def test_quiz_history(client, user_jwt, doc_fixture, app):
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 3},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    client.post(
        f"/api/quizzes/{quiz_id}/submit",
        json={"responses": []},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )

    res = client.get("/api/quizzes/history", headers={"Authorization": f"Bearer {user_jwt}"})
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["attempts"]) >= 1


def test_delete_quiz(client, user_jwt, doc_fixture):
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 3},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    del_res = client.delete(f"/api/quizzes/{quiz_id}", headers={"Authorization": f"Bearer {user_jwt}"})
    assert del_res.status_code == 200

    # Ensure it's deleted
    get_res = client.get(f"/api/quizzes/{quiz_id}", headers={"Authorization": f"Bearer {user_jwt}"})
    assert get_res.status_code == 404


LARGE_CHAPTER = """
Artificial Intelligence is the simulation of human intelligence by machines.
Machine Learning is a subset of artificial intelligence focused on learning from data.
Deep Learning is a subset of machine learning based on artificial neural networks.
Supervised Learning algorithms train on labeled datasets to predict outcomes.
Unsupervised Learning algorithms discover hidden patterns in unlabeled data.
Reinforcement Learning trains agents to make sequences of decisions by rewarding desired behaviors.
Neural Networks are computing systems inspired by the biological neural networks in animal brains.
Convolutional Neural Networks excel at processing grid-like data such as digital images.
Recurrent Neural Networks are designed to recognize patterns in sequences of data such as text.
Transformers are deep learning models that utilize self-attention mechanisms for language processing.
Natural Language Processing enables computers to understand, interpret, and generate human language.
Computer Vision trains computers to interpret and understand visual information from the world.
Overfitting occurs when a machine learning model learns the training data too closely, harming generalization.
Regularization techniques reduce overfitting by penalizing model complexity.
Gradient Descent is an optimization algorithm used to minimize the loss function in neural networks.
Activation Functions introduce non-linear properties into neural network nodes.
Cross Validation evaluates how the results of a statistical analysis will generalize to an independent dataset.
Backpropagation computes the gradient of the loss function with respect to the network weights.
Hyperparameters are configuration variables external to the model whose values cannot be estimated from data.
Transfer Learning leverages knowledge gained while solving one problem to solve a different related problem.
Feature Engineering transforms raw data into features that better represent the underlying problem.
Classification algorithms assign test data into specific categories or target classes.
Regression analysis estimates the relationships among variables to predict continuous numerical values.
Clustering groups a set of objects such that objects in the same group are more similar to each other.
Dimensionality Reduction reduces the number of random variables under consideration via feature extraction.
"""


@pytest.fixture
def large_doc_fixture(app, quiz_user):
    with app.app_context():
        doc = Document(
            user_id=quiz_user,
            original_filename="ai_textbook.txt",
            stored_filename="ai_textbook.txt",
            file_type="txt",
            file_size=2048,
            processing_status="COMPLETED",
            extraction_quality="HIGH",
            extracted_text=LARGE_CHAPTER,
            total_words=325
        )
        db.session.add(doc)
        db.session.commit()
        return doc.id


@pytest.mark.parametrize("requested_count", [5, 10, 15, 20])
def test_generate_quiz_exact_counts(client, user_jwt, large_doc_fixture, requested_count):
    """Verifies that selecting 5, 10, 15, and 20 questions produces the exact requested count."""
    res = client.post(
        "/api/quizzes/generate",
        json={"document_id": large_doc_fixture, "total_questions": requested_count},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert res.status_code == 201
    payload = res.get_json()
    assert payload["status"] == "success"
    quiz_data = payload["data"]
    assert quiz_data["total_questions"] == requested_count
    assert len(quiz_data["questions"]) == requested_count


def test_generate_quiz_invalid_counts_rejected(client, user_jwt, doc_fixture):
    """Verifies that invalid counts (<1, >50, non-integer) are rejected with 400 Bad Request."""
    for bad_count in [-1, 0, 55, "twenty"]:
        res = client.post(
            "/api/quizzes/generate",
            json={"document_id": doc_fixture, "total_questions": bad_count},
            headers={"Authorization": f"Bearer {user_jwt}"}
        )
        assert res.status_code == 400
        assert res.get_json()["status"] == "error"


def test_delete_quiz_attempt(client, user_jwt, other_jwt, doc_fixture):
    """Verifies deleting individual quiz attempt and cross-user authorization enforcement."""
    # 1. Generate quiz and submit attempt
    gen_res = client.post(
        "/api/quizzes/generate",
        json={"document_id": doc_fixture, "total_questions": 3},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    quiz_id = gen_res.get_json()["data"]["id"]

    sub_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        json={"responses": []},
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    attempt_id = sub_res.get_json()["data"]["attempt_id"]

    # 2. Other user cannot delete this attempt
    unauth_del = client.delete(
        f"/api/quizzes/attempts/{attempt_id}",
        headers={"Authorization": f"Bearer {other_jwt}"}
    )
    assert unauth_del.status_code == 403

    # 3. Owner successfully deletes attempt
    del_res = client.delete(
        f"/api/quizzes/attempts/{attempt_id}",
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert del_res.status_code == 200
    assert del_res.get_json()["status"] == "success"

    # 4. Attempt is no longer retrievable
    get_res = client.get(
        f"/api/quizzes/attempts/{attempt_id}",
        headers={"Authorization": f"Bearer {user_jwt}"}
    )
    assert get_res.status_code == 404


