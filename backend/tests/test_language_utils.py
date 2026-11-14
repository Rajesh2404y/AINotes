"""
Unit tests for Language Utilities and Mapping Services.
"""
from backend.app.utils.language_utils import (
    get_supported_languages,
    is_language_supported,
    get_nllb_code,
    validate_language_pair,
)


def test_supported_languages_list():
    languages = get_supported_languages()
    assert len(languages) == 9
    codes = {l["code"] for l in languages}
    expected_codes = {"en", "ta", "hi", "te", "ml", "kn", "fr", "es", "de"}
    assert codes == expected_codes


def test_is_language_supported():
    assert is_language_supported("en") is True
    assert is_language_supported("ta") is True
    assert is_language_supported("hi") is True
    assert is_language_supported("fr") is True
    assert is_language_supported("xyz") is False
    assert is_language_supported("") is False


def test_get_nllb_code():
    assert get_nllb_code("en") == "eng_Latn"
    assert get_nllb_code("ta") == "tam_Taml"
    assert get_nllb_code("hi") == "hin_Deva"
    assert get_nllb_code("fr") == "fra_Latn"
    assert get_nllb_code("de") == "deu_Latn"
    assert get_nllb_code("xyz") is None


def test_validate_language_pair():
    # Valid pairs
    ok, err = validate_language_pair("en", "ta")
    assert ok is True
    assert err is None

    ok, err = validate_language_pair("en", "hi")
    assert ok is True

    # Identical languages
    ok, err = validate_language_pair("en", "en")
    assert ok is False
    assert "cannot be identical" in err

    # Unsupported language
    ok, err = validate_language_pair("en", "klingon")
    assert ok is False
    assert "Unsupported" in err

