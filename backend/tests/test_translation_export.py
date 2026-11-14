"""
Unit tests for Translation Export Service (PDF & TXT).
"""
import io
from backend.app.services.translation_export_service import translation_export_service


SAMPLE_TRANSLATION = {
    "source_language": "en",
    "target_language": "ta",
    "original_text": "Machine learning enables computers to learn from empirical observations.",
    "translated_text": "இயந்திர கற்றல் கணினிகள் அனுபவ அவதானிப்புகளிலிருந்து கற்றுக்கொள்ள உதவுகிறது.",
    "model_name": "facebook/nllb-200-distilled-600M"
}


def test_export_translation_txt():
    txt_out = translation_export_service.export_txt(SAMPLE_TRANSLATION, doc_title="AI Chapter Notes")
    assert "TRANSLATED STUDY NOTES: AI CHAPTER NOTES" in txt_out
    assert "EN -> TA" in txt_out
    assert "இயந்திர கற்றல்" in txt_out


def test_export_translation_pdf():
    pdf_buffer = translation_export_service.export_pdf(SAMPLE_TRANSLATION, doc_title="AI Chapter Notes")
    assert isinstance(pdf_buffer, io.BytesIO)
    content = pdf_buffer.getvalue()
    assert len(content) > 500
    assert content.startswith(b"%PDF")

