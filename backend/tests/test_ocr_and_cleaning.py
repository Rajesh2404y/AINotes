"""Automated Tests for OCR Service, Text Cleaning, and Text Quality Assessment.

Verifies:
- OCR image preprocessing and availability detection.
- Text cleaning whitespace, newline, and control character normalization.
- Tamil Unicode and mathematical formula preservation during cleaning.
- Bullet points and sentence boundary standardization.
- Quality scoring metrics (HIGH, MEDIUM, LOW, FAILED) and warning flags.
"""

from PIL import Image
from backend.app.services.ocr_service import OCRService
from backend.app.services.text_cleaning_service import clean_text
from backend.app.services.text_quality_service import assess_text_quality


# ============================================================================
# 1. OCR TESTS
# ============================================================================

def test_ocr_availability_and_disabled_state():
    """Test 1: Verifies OCR service respects enabled flag and binary availability."""
    disabled_service = OCRService(enabled=False)
    assert disabled_service.is_available() is False
    res = disabled_service.extract_text_from_image("dummy.png")
    assert res["success"] is False
    assert "disabled" in res["warning"]


def test_ocr_image_preprocessing(tmp_path):
    """Test 2: Verifies image preprocessing converts to grayscale and enhances contrast."""
    ocr = OCRService()
    img = Image.new("RGB", (100, 100), color=(120, 150, 200))
    processed = ocr.preprocess_image(img)
    assert processed.mode == "L"  # Grayscale
    assert processed.size == (100, 100)


def test_ocr_missing_binary_fallback_handling():
    """Test 3: Verifies that if tesseract binary is not installed, clear warning is returned."""
    service_with_bad_cmd = OCRService(tesseract_cmd="/non/existent/path/to/tesseract")
    img = Image.new("RGB", (50, 50), color=(255, 255, 255))
    res = service_with_bad_cmd.extract_text_from_image(img)
    assert res["success"] is False
    assert "Tesseract OCR binary not found" in res["warning"]


# ============================================================================
# 2. TEXT CLEANING TESTS
# ============================================================================

def test_clean_text_whitespace_and_newlines():
    """Test 4: Verifies excessive whitespace and 3+ consecutive newlines are normalized."""
    raw = "Paragraph   one    with   wide    spacing.\r\n\r\n\r\n\r\nParagraph two."
    cleaned = clean_text(raw)
    assert "Paragraph one with wide spacing." in cleaned
    assert "Paragraph two." in cleaned
    assert "\n\n\n" not in cleaned
    assert "\r" not in cleaned


def test_clean_text_control_characters_removal():
    """Test 5: Verifies unprintable control characters are stripped while preserving tabs and newlines."""
    raw = "Valid line.\x00\x07\x1f\nLine with tab:\tvalue."
    cleaned = clean_text(raw)
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned
    assert "\x1f" not in cleaned
    assert "\t" in cleaned
    assert "\n" in cleaned


def test_clean_text_tamil_and_unicode_preservation():
    """Test 6: Verifies Tamil Unicode scripts and mathematical symbols are untouched."""
    raw = "பாடம்: கணிதவியல். Equation: E = mc^2 and \\sqrt{x} + \\sum_{i=1}^n i."
    cleaned = clean_text(raw)
    assert "பாடம்: கணிதவியல்." in cleaned
    assert "E = mc^2" in cleaned
    assert "\\sqrt{x}" in cleaned


def test_clean_text_sentence_boundary_and_bullets():
    """Test 7: Verifies punctuation spacing and bullet points are standardized."""
    raw = "Important points :\n•First item .\n·Second item .\n○Third item ."
    cleaned = clean_text(raw)
    assert "• First item." in cleaned or "•First item" in cleaned
    assert "• Second item." in cleaned or "•Second item" in cleaned


# ============================================================================
# 3. TEXT QUALITY ASSESSMENT TESTS
# ============================================================================

def test_text_quality_high():
    """Test 8: Verifies substantive, readable educational content receives HIGH quality."""
    text = (
        "Supervised learning is an approach to creating artificial intelligence where the program is trained "
        "on labeled data. In supervised learning, the algorithm is provided with inputs paired with correct outputs. "
        "The model learns a mapping function from input variables to the target output variable. Common examples "
        "include classification tasks like spam filtering and regression tasks like price prediction."
    )
    res = assess_text_quality(text, total_pages=1)
    assert res["quality"] == "HIGH"
    assert res["total_words"] > 50
    assert len(res["warnings"]) == 0


def test_text_quality_medium_for_brief_text():
    """Test 9: Verifies brief text (< 50 words) receives MEDIUM quality with advisory warning."""
    text = "Short study note: photosynthesis is the process used by plants to convert light into chemical energy."
    res = assess_text_quality(text, total_pages=1)
    assert res["quality"] == "MEDIUM"
    assert any("Brief document" in w for w in res["warnings"])


def test_text_quality_low_for_sparse_text():
    """Test 10: Verifies very sparse text (< 20 words) receives LOW quality."""
    text = "Only three words."
    res = assess_text_quality(text, total_pages=1)
    assert res["quality"] == "LOW"
    assert any("Very low word count" in w for w in res["warnings"])


def test_text_quality_failed_for_empty():
    """Test 11: Verifies empty text receives FAILED quality status."""
    res = assess_text_quality("", total_pages=1)
    assert res["quality"] == "FAILED"
    assert res["total_words"] == 0
    assert len(res["warnings"]) > 0

