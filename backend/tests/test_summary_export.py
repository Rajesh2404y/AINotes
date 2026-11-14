"""
Unit tests for Summary Export Service (PDF & TXT).
"""
import io
from backend.app.services.summary_export_service import summary_export_service


SAMPLE_SUMMARY_DATA = {
    "summary_type": "medium",
    "summary_text": "Photosynthesis is the biological process by which green plants convert light into chemical energy.",
    "key_takeaways": [
        "Light energy is captured by chlorophyll molecules.",
        "Water and carbon dioxide are transformed into glucose and oxygen."
    ],
    "definitions": [
        {"term": "Photosynthesis", "definition": "Process transforming light into glucose."}
    ],
    "keywords": ["Chlorophyll", "Glucose", "Oxygen"],
    "model_name": "distilbart-cnn-12-6"
}


def test_export_txt():
    txt_out = summary_export_service.export_txt(SAMPLE_SUMMARY_DATA, doc_title="Biology 101")
    assert "STUDY NOTES: BIOLOGY 101" in txt_out
    assert "Photosynthesis is the biological process" in txt_out
    assert "Light energy is captured by chlorophyll molecules." in txt_out
    assert "Chlorophyll, Glucose, Oxygen" in txt_out


def test_export_pdf():
    pdf_buffer = summary_export_service.export_pdf(SAMPLE_SUMMARY_DATA, doc_title="Biology 101")
    assert isinstance(pdf_buffer, io.BytesIO)
    content = pdf_buffer.getvalue()
    assert len(content) > 500
    assert content.startswith(b"%PDF")
