"""
Unit tests for Content Extraction Service (Takeaways, Definitions, Keywords).
"""
import pytest
from backend.app.ai.content_extraction_service import content_extraction_service


SAMPLE_EDUCATIONAL_TEXT = """
Machine learning is defined as a branch of artificial intelligence focused on building applications that learn from data.
Supervised learning refers to the process of training algorithms on labeled datasets.
Unsupervised learning is a type of algorithm that detects hidden patterns in unlabeled data.
Deep learning denotes neural networks with multiple layers capable of representation learning.
In supervised learning, algorithms iteratively make predictions on data and are corrected based on ground truth labels.
Clustering and dimensionality reduction are two prominent examples of unsupervised techniques.
Overall, these paradigms empower modern data science applications and intelligent automation across diverse domains.
"""


def test_extract_key_takeaways():
    takeaways = content_extraction_service.extract_key_takeaways(SAMPLE_EDUCATIONAL_TEXT, max_items=4)
    assert isinstance(takeaways, list)
    assert 1 <= len(takeaways) <= 4
    for item in takeaways:
        assert isinstance(item, str)
        assert len(item.strip()) > 10


def test_extract_definitions():
    definitions = content_extraction_service.extract_definitions(SAMPLE_EDUCATIONAL_TEXT)
    assert isinstance(definitions, list)
    assert len(definitions) >= 2

    terms = [d["term"].lower() for d in definitions]
    assert any("machine learning" in t for t in terms)
    assert any("supervised learning" in t for t in terms)


def test_extract_keywords():
    keywords = content_extraction_service.extract_keywords(SAMPLE_EDUCATIONAL_TEXT, max_keywords=5)
    assert isinstance(keywords, list)
    assert 1 <= len(keywords) <= 5
    for kw in keywords:
        assert isinstance(kw, str)
        assert len(kw) > 2


def test_extract_all_empty():
    res = content_extraction_service.extract_all("")
    assert res["key_takeaways"] == []
    assert res["definitions"] == []
    assert res["keywords"] == []
