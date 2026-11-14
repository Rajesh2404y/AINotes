"""
Unit tests for Multilingual Translation Service.
"""
import pytest
from backend.app.ai.translation_service import translation_service, TranslationServiceError


SAMPLE_NOTE = "Machine learning and artificial intelligence empower educational software."


def test_translate_to_tamil():
    res = translation_service.translate_text(
        text=SAMPLE_NOTE,
        source_lang="en",
        target_lang="ta"
    )
    assert res["source_language"] == "en"
    assert res["target_language"] == "ta"
    assert len(res["translated_text"]) > 0
    assert "metadata" in res


def test_translate_to_hindi():
    res = translation_service.translate_text(
        text=SAMPLE_NOTE,
        source_lang="en",
        target_lang="hi"
    )
    assert res["target_language"] == "hi"
    assert len(res["translated_text"]) > 0


def test_translate_to_french():
    res = translation_service.translate_text(
        text=SAMPLE_NOTE,
        source_lang="en",
        target_lang="fr"
    )
    assert res["target_language"] == "fr"
    assert len(res["translated_text"]) > 0


def test_translate_identical_languages_raises_error():
    with pytest.raises(TranslationServiceError, match="cannot be identical"):
        translation_service.translate_text(
            text=SAMPLE_NOTE,
            source_lang="en",
            target_lang="en"
        )


def test_translate_empty_text_raises_error():
    with pytest.raises(TranslationServiceError, match="cannot be empty"):
        translation_service.translate_text(
            text="   ",
            source_lang="en",
            target_lang="ta"
        )

