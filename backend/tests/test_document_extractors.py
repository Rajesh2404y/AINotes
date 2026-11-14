"""Automated Tests for PDF, DOCX, and TXT Text Extractors.

Verifies:
- PDF digital single-page and multi-page extraction.
- PDF scanned page OCR routing detection.
- PDF encrypted file detection.
- PDF corrupted file handling.
- DOCX paragraph and table extraction.
- DOCX corrupted document handling.
- TXT UTF-8, Unicode, Tamil, and UTF-8 with BOM handling.
- TXT binary content rejection.
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from docx import Document as DocxDoc
from PIL import Image

from backend.app.services.pdf_extractor import extract_pdf_text
from backend.app.services.docx_extractor import extract_docx_text
from backend.app.services.txt_extractor import extract_txt_text


# ============================================================================
# 1. PDF EXTRACTION TESTS
# ============================================================================

def test_pdf_digital_extraction(tmp_path):
    """Test 1: Verifies digital PDF text extraction preserves content."""
    pdf_path = tmp_path / "lecture1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Deep Learning and Neural Networks. Chapter 1.")
    doc.save(str(pdf_path))
    doc.close()

    res = extract_pdf_text(str(pdf_path))
    assert res["success"] is True
    assert res["total_pages"] == 1
    assert "Deep Learning and Neural Networks" in res["text"]
    assert res["ocr_required"] is False


def test_pdf_multipage_extraction(tmp_path):
    """Test 2: Verifies multi-page PDF extracts each page in sequential order."""
    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()
    for i in range(1, 4):
        p = doc.new_page()
        p.insert_text((50, 72), f"This is page {i} content for syllabus.")
    doc.save(str(pdf_path))
    doc.close()

    res = extract_pdf_text(str(pdf_path))
    assert res["success"] is True
    assert res["total_pages"] == 3
    assert res["extracted_pages"] == 3
    assert "Page 1" in res["text"]
    assert "Page 2" in res["text"]
    assert "Page 3" in res["text"]


def test_pdf_scanned_page_detection(tmp_path):
    """Test 3: Verifies that a page with an image and no text is flagged for OCR."""
    pdf_path = tmp_path / "scanned.pdf"
    doc = fitz.open()
    page = doc.new_page()

    # Insert an image into the page without insert_text
    img_path = tmp_path / "sample_img.png"
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    img.save(str(img_path))

    page.insert_image(fitz.Rect(50, 50, 200, 200), filename=str(img_path))
    doc.save(str(pdf_path))
    doc.close()

    res = extract_pdf_text(str(pdf_path))
    assert res["success"] is True
    assert res["ocr_required"] is True
    assert 1 in res["pages_needing_ocr"]


def test_pdf_corrupted_handling(tmp_path):
    """Test 4: Verifies corrupted or invalid PDF file paths return error safely."""
    corrupted_path = tmp_path / "corrupted.pdf"
    corrupted_path.write_bytes(b"%PDF-1.4 garbage truncated data")

    res = extract_pdf_text(str(corrupted_path))
    assert res["success"] is False
    assert "error" in res


# ============================================================================
# 2. DOCX EXTRACTION TESTS
# ============================================================================

def test_docx_paragraphs_and_headings(tmp_path):
    """Test 5: Verifies DOCX extraction captures paragraphs and heading hierarchy."""
    docx_path = tmp_path / "sample.docx"
    doc = DocxDoc()
    doc.add_heading("Artificial Intelligence Notes", level=1)
    doc.add_paragraph("Supervised learning uses labeled training sets.")
    doc.add_paragraph("Unsupervised learning finds hidden patterns in unlabeled data.")
    doc.save(str(docx_path))

    res = extract_docx_text(str(docx_path))
    assert res["success"] is True
    assert res["paragraphs_count"] >= 3
    assert "Artificial Intelligence Notes" in res["text"]
    assert "Supervised learning" in res["text"]
    assert res["total_words"] > 10


def test_docx_table_extraction(tmp_path):
    """Test 6: Verifies tabular data in DOCX is preserved in text output with separators."""
    docx_path = tmp_path / "tables.docx"
    doc = DocxDoc()
    doc.add_paragraph("Course schedule:")
    table = doc.add_table(rows=2, cols=3)
    table.cell(0, 0).text = "Module"
    table.cell(0, 1).text = "Topic"
    table.cell(0, 2).text = "Credits"
    table.cell(1, 0).text = "CS101"
    table.cell(1, 1).text = "Python Programming"
    table.cell(1, 2).text = "4"
    doc.save(str(docx_path))

    res = extract_docx_text(str(docx_path))
    assert res["success"] is True
    assert res["tables_count"] == 1
    assert "CS101" in res["text"]
    assert "Python Programming" in res["text"]
    assert "|" in res["text"]


def test_docx_corrupted_handling(tmp_path):
    """Test 7: Verifies corrupted DOCX file returns a clean error payload."""
    corrupted_path = tmp_path / "corrupted.docx"
    corrupted_path.write_bytes(b"PK\x03\x04 fake docx bytes")

    res = extract_docx_text(str(corrupted_path))
    assert res["success"] is False
    assert "error" in res


# ============================================================================
# 3. TXT EXTRACTION TESTS
# ============================================================================

def test_txt_utf8_extraction(tmp_path):
    """Test 8: Verifies standard UTF-8 text extraction."""
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("Linear Algebra: Vectors, matrices, and eigenvalues.", encoding="utf-8")

    res = extract_txt_text(str(txt_path))
    assert res["success"] is True
    assert "Linear Algebra" in res["text"]
    assert res["encoding_used"] in ("utf-8", "utf-8-sig")


def test_txt_tamil_unicode_preservation(tmp_path):
    """Test 9: Verifies Tamil script is accurately preserved without corruption."""
    tamil_content = "இயற்கை மொழி செயலாக்கம் (NLP) கணினி அறிவியலின் ஒரு முக்கிய பிரிவு ஆகும்."
    txt_path = tmp_path / "tamil_notes.txt"
    txt_path.write_text(tamil_content, encoding="utf-8")

    res = extract_txt_text(str(txt_path))
    assert res["success"] is True
    assert tamil_content in res["text"]
    assert "இயற்கை" in res["text"]


def test_txt_utf8_bom_handling(tmp_path):
    """Test 10: Verifies UTF-8 files with Byte Order Mark (BOM) are read cleanly."""
    txt_path = tmp_path / "bom_notes.txt"
    bom_bytes = b"\xef\xbb\xbfQuantum Computing Principles."
    txt_path.write_bytes(bom_bytes)

    res = extract_txt_text(str(txt_path))
    assert res["success"] is True
    assert "Quantum Computing Principles" in res["text"]
    assert res["encoding_used"] == "utf-8-sig"


def test_txt_binary_rejection(tmp_path):
    """Test 11: Verifies binary file with null bytes is rejected."""
    bin_path = tmp_path / "binary.txt"
    bin_path.write_bytes(b"\x00\x01\x02\x03\x04 binary compiled data")

    res = extract_txt_text(str(bin_path))
    assert res["success"] is False
    assert "Binary data detected" in res["error"]

