"""
Dedicated Tests for Tamil Unicode Font Embedding, Complex Script Formatting,
and Multilingual PDF/TXT Export Pipelines.
"""
from __future__ import annotations

import io
import uuid
import pymupdf as fitz
import pytest
from flask_jwt_extended import create_access_token

from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.services.translation_export_service import translation_export_service


SAMPLE_TAMIL_TRANSLATION_RECORD = {
    "source_language": "en",
    "target_language": "ta",
    "model_name": "facebook/nllb-200-distilled-600M",
    "original_text": (
        "--- Page 1 ---\n"
        "Introduction to Machine Learning\n\n"
        "Sample academic notes for testing document upload, text extraction, summarization and quiz generation.\n\n"
        "• Machine Learning (ML) is a branch of Artificial Intelligence (AI).\n"
        "• Supervised learning uses labelled data for classification and regression.\n"
        "• Overfitting harms generalization to unseen data.\n"
        "• Dataset accuracy reached 98.5% across 1200 test samples."
    ),
    "translated_text": (
        "--- பக்கம் 1 ---\n"
        "இயந்திர கற்றல் அறிமுகம்\n\n"
        "ஆவணப் பதிவேற்றம், உரை பிரித்தெடுத்தல் மற்றும் சுருக்கம் தயாரிப்பதற்கான மாதிரி கல்வி குறிப்புகள்.\n\n"
        "• இயந்திர கற்றல் (Machine Learning - ML) என்பது செயற்கை நுண்ணறிவின் (AI) ஒரு முக்கிய கிளையாகும்.\n"
        "• மேற்பார்வை செய்யப்பட்ட கற்றல் (Supervised Learning) வகைப்படுத்தல் மற்றும் பின்னடைவுக்கு லேபிளிடப்பட்ட தரவைப் பயன்படுத்துகிறது.\n"
        "• அதிகப்படியான பொருத்தம் (Overfitting) காணப்படாத புதிய தரவுகளின் பொதுமைப்படுத்தலைப் பாதிக்கிறது.\n"
        "• 1200 சோதனை மாதிரிகளில் தரவுத்தொகுப்பு துல்லியம் (Accuracy) 98.5% ஐ எட்டியுள்ளது.\n"
        "• சிறப்பு உயிர்மெய் எழுத்துக்கள்: கி, கீ, கெ, கே, கொ, கோ, கௌ மற்றும் மெய்யெழுத்து க்."
    )
}


@pytest.fixture
def export_user(app):
    with app.app_context():
        email = f"tamil_export_{uuid.uuid4().hex[:6]}@example.com"
        user = User(
            full_name="Tamil Export Tester",
            email=email,
            is_active=True
        )
        user.set_password("StudentPassword123!")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def export_token(app, export_user):
    with app.app_context():
        return create_access_token(identity=str(export_user))


@pytest.fixture
def export_summary(app, export_user):
    with app.app_context():
        doc = Document(
            user_id=export_user,
            original_filename="sample_tamil_study_notes.pdf",
            stored_filename="sample_tamil_study_notes.pdf",
            file_type="pdf",
            file_size=4096,
            extracted_text="Machine Learning enables computers to learn patterns from academic data."
        )
        db.session.add(doc)
        db.session.commit()

        summary = Summary(
            document_id=doc.id,
            user_id=export_user,
            summary_type="detailed",
            summary_text="Machine Learning enables computers to learn patterns from academic data.",
            key_takeaways=["Supervised learning uses labelled data."],
            definitions={"ML": "Machine Learning"},
            keywords=["Machine Learning", "AI"]
        )
        db.session.add(summary)
        db.session.commit()
        return summary.id


def test_tamil_font_registration_and_selection():
    """Verifies that the export service selects NotoSansTamil and never falls back to Helvetica."""
    regular_font, bold_font = translation_export_service.get_font_for_target_language("ta")
    assert "Tamil" in regular_font or "Nirmala" in regular_font
    assert regular_font != "Helvetica"
    assert bold_font != "Helvetica-Bold"


def test_tamil_pdf_export_font_embedding_and_text_extraction():
    """
    Builds a real Tamil PDF and verifies:
    1. Output is valid PDF bytes.
    2. NotoSansTamil font is embedded in the PDF document.
    3. Extracted text contains Tamil Unicode glyphs without square boxes or missing characters.
    4. Mixed English terms in parentheses are preserved.
    """
    pdf_buffer = translation_export_service.export_pdf(
        SAMPLE_TAMIL_TRANSLATION_RECORD,
        doc_title="Introduction to Machine Learning"
    )
    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2000

    # Inspect the generated PDF structure using PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 1

    page1 = doc[0]
    extracted_text = page1.get_text()

    # Verify Tamil Unicode phrases in extracted PDF content
    assert "இயந்திர கற்றல் அறிமுகம்" in extracted_text
    assert "செயற்கை நுண்ணறிவின்" in extracted_text
    assert "மேற்பார்வை செய்யப்பட்ட கற்றல்" in extracted_text
    assert "துல்லியம்" in extracted_text
    assert "98.5%" in extracted_text

    # Verify English technical terms in parentheses are preserved alongside Tamil
    assert "Machine Learning - ML" in extracted_text
    assert "Supervised Learning" in extracted_text
    assert "Overfitting" in extracted_text

    # Verify font embedding: NotoSansTamil or Nirmala must be listed in page fonts
    embedded_fonts = page1.get_fonts()
    font_names = [f[3] for f in embedded_fonts]
    has_indic_font = any("Tamil" in fn or "Nirmala" in fn for fn in font_names)
    assert has_indic_font, f"Expected embedded Tamil font, found: {font_names}"


def test_tamil_combining_characters_and_vowel_signs():
    """Verifies complex Tamil vowel signs and combining marks render without truncation."""
    complex_record = {
        "source_language": "en",
        "target_language": "ta",
        "translated_text": (
            "கொடுக்கப்பட்டுள்ள எடுத்துக்காட்டு: "
            "தொழில்நுட்பம், கல்வி, ஆராய்ச்சி, பல்கலைக்கழகம், நுண்ணறிவு."
        ),
        "original_text": "Sample text for testing complex Tamil ligature shaping."
    }
    pdf_buffer = translation_export_service.export_pdf(complex_record, doc_title="Complex Script Test")
    pdf_bytes = pdf_buffer.getvalue()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_text = doc[0].get_text()
    assert "கொடுக்கப்பட்டுள்ள" in page_text
    assert "தொழில்நுட்பம்" in page_text
    assert "நுண்ணறிவு" in page_text


def test_multipage_tamil_pdf_and_running_headers():
    """Verifies that multi-page translated notes include running headers and Page X of Y footers."""
    long_paras = []
    for i in range(1, 20):
        long_paras.append(
            f"• பகுதி {i}: இயந்திர கற்றல் மாதிரி பயிற்சி செயல்முறை மற்றும் மதிப்பீட்டு அளவீடுகள். "
            f"அளவீடு எண் {i * 10} - துல்லியம் மற்றும் பின்னடைவு பகுப்பாய்வு முடிவு."
        )

    multi_page_record = {
        "source_language": "en",
        "target_language": "ta",
        "translated_text": "\n\n".join(long_paras),
        "original_text": "Long original study text for multi-page verification.\n\n" * 10
    }

    pdf_buffer = translation_export_service.export_pdf(multi_page_record, doc_title="Multi-page Tamil Study Notes")
    pdf_bytes = pdf_buffer.getvalue()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc) >= 2, f"Expected at least 2 pages, got {len(doc)}"

    p1_text = doc[0].get_text()
    assert f"Page 1 of {len(doc)}" in p1_text

    p2_text = doc[1].get_text()
    assert "Multilingual Study Notes" in p2_text
    assert f"Page 2 of {len(doc)}" in p2_text


def test_tamil_txt_export_utf8_integrity():
    """Verifies UTF-8 plain text export preserves exact Tamil characters and structure."""
    txt_output = translation_export_service.export_txt(
        SAMPLE_TAMIL_TRANSLATION_RECORD,
        doc_title="Machine Learning Notes"
    )
    encoded_bytes = txt_output.encode("utf-8")
    decoded_str = encoded_bytes.decode("utf-8")
    assert decoded_str == txt_output

    assert "TRANSLATED STUDY NOTES: MACHINE LEARNING NOTES" in txt_output
    assert "Translation       : EN -> TA" in txt_output
    assert "இயந்திர கற்றல் அறிமுகம்" in txt_output
    assert "1200 சோதனை மாதிரிகளில்" in txt_output
    assert "ORIGINAL REFERENCE CONTENT (EN)" in txt_output


def test_api_export_tamil_pdf(client, export_token, export_summary):
    """Verifies GET /api/translations/<id>/export?format=pdf returns valid application/pdf with Tamil font."""
    gen_res = client.post(
        "/api/translations/generate",
        json={"summary_id": export_summary, "target_language": "ta"},
        headers={"Authorization": f"Bearer {export_token}"}
    )
    assert gen_res.status_code == 201
    trans_id = gen_res.get_json()["data"]["id"]

    export_res = client.get(
        f"/api/translations/{trans_id}/export?format=pdf",
        headers={"Authorization": f"Bearer {export_token}"}
    )
    assert export_res.status_code == 200
    assert "application/pdf" in export_res.content_type
    assert export_res.data.startswith(b"%PDF")

    doc = fitz.open(stream=export_res.data, filetype="pdf")
    assert len(doc) >= 1
    p1_fonts = [f[3] for f in doc[0].get_fonts()]
    assert any("Tamil" in fn or "Nirmala" in fn for fn in p1_fonts)
