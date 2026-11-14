"""
Unit tests for Language Detection Service.
"""
from backend.app.ai.language_detection_service import language_detection_service


def test_detect_tamil_script():
    tamil_text = "இயந்திர கற்றல் என்பது செயற்கை நுண்ணறிவின் ஒரு முக்கிய பிரிவு ஆகும்."
    res = language_detection_service.detect_language(tamil_text)
    assert res["language"] == "ta"
    assert res["reliable"] is True


def test_detect_hindi_script():
    hindi_text = "मशीन लर्निंग कृत्रिम बुद्धिमत्ता का एक महत्वपूर्ण उपक्षेत्र है।"
    res = language_detection_service.detect_language(hindi_text)
    assert res["language"] == "hi"
    assert res["reliable"] is True


def test_detect_english_text():
    en_text = "Artificial intelligence and deep learning allow autonomous agents to perceive environments."
    res = language_detection_service.detect_language(en_text)
    assert res["language"] == "en"
    assert res["reliable"] is True


def test_detect_french_diacritics():
    fr_text = "L'intelligence artificielle générale révolutionne l'éducation et la recherche."
    res = language_detection_service.detect_language(fr_text)
    assert res["language"] == "fr"
    assert res["reliable"] is True


def test_detect_empty_text():
    res = language_detection_service.detect_language("")
    assert res["language"] == "en"
    assert res["reliable"] is False

