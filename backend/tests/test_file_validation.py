"""Automated Tests for File Validation Service.

Verifies:
1. Valid PDF validation.
2. Valid DOCX validation.
3. Valid TXT validation.
4. Valid PNG image validation.
5. Unsupported extension rejection.
6. File size limit enforcement.
7. Empty file rejection.
8. Corrupted document signature rejection.
9. Suspicious filename and path traversal prevention.
10. Filename sanitization.
"""

import io
import pytest
from werkzeug.datastructures import FileStorage
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from docx import Document as DocxDoc
from PIL import Image

from backend.app.services.file_validation_service import (
    FileValidationService,
    FileValidationError,
)


@pytest.fixture
def validator():
    return FileValidationService(max_size_mb=20)


def test_valid_pdf_validation(validator, tmp_path):
    """Test 1: Verifies a legitimate PDF passes validation with metadata."""
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Educational Notes for Class")
    doc.save(str(pdf_path))
    doc.close()

    with open(pdf_path, "rb") as f:
        fs = FileStorage(stream=f, filename="valid.pdf", content_type="application/pdf")
        is_valid, meta = validator.validate_file(fs)
        assert is_valid is True
        assert meta["file_type"] == "pdf"
        assert meta["file_size"] > 0
        assert meta["original_filename"] == "valid.pdf"
        assert meta["stored_filename"].endswith(".pdf")


def test_valid_docx_validation(validator, tmp_path):
    """Test 2: Verifies a legitimate DOCX document passes validation."""
    docx_path = tmp_path / "lecture.docx"
    doc = DocxDoc()
    doc.add_paragraph("Machine learning study notes")
    doc.save(str(docx_path))

    with open(docx_path, "rb") as f:
        fs = FileStorage(
            stream=f,
            filename="lecture.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        is_valid, meta = validator.validate_file(fs)
        assert is_valid is True
        assert meta["file_type"] == "docx"
        assert meta["stored_filename"].endswith(".docx")


def test_valid_txt_validation(validator):
    """Test 3: Verifies plain text file validation."""
    content = b"Lecture 1: Introduction to Data Structures and Algorithms."
    fs = FileStorage(stream=io.BytesIO(content), filename="notes.txt", content_type="text/plain")
    is_valid, meta = validator.validate_file(fs)
    assert is_valid is True
    assert meta["file_type"] == "txt"
    assert meta["file_size"] == len(content)


def test_valid_png_validation(validator, tmp_path):
    """Test 4: Verifies image file (PNG) validation."""
    png_path = tmp_path / "board_photo.png"
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img.save(str(png_path), "PNG")

    with open(png_path, "rb") as f:
        fs = FileStorage(stream=f, filename="board_photo.png", content_type="image/png")
        is_valid, meta = validator.validate_file(fs)
        assert is_valid is True
        assert meta["file_type"] == "png"


def test_unsupported_extension_rejected(validator):
    """Test 5: Verifies executable or unsupported files (.exe, .py) are rejected."""
    fs = FileStorage(stream=io.BytesIO(b"print('hello')"), filename="script.py")
    with pytest.raises(FileValidationError) as exc:
        validator.validate_file(fs)
    assert exc.value.code == "UNSUPPORTED_EXTENSION"


def test_oversized_file_rejected(tmp_path):
    """Test 6: Verifies files exceeding max configured size are rejected."""
    small_validator = FileValidationService(max_size_mb=1)  # 1 MB threshold
    oversized_data = b"A" * (2 * 1024 * 1024)  # 2 MB
    fs = FileStorage(stream=io.BytesIO(oversized_data), filename="huge.txt")
    with pytest.raises(FileValidationError) as exc:
        small_validator.validate_file(fs)
    assert exc.value.code == "FILE_TOO_LARGE"


def test_empty_file_rejected(validator):
    """Test 7: Verifies empty (0-byte) files are rejected."""
    fs = FileStorage(stream=io.BytesIO(b""), filename="empty.pdf")
    with pytest.raises(FileValidationError) as exc:
        validator.validate_file(fs)
    assert exc.value.code == "EMPTY_FILE"


def test_corrupted_signature_rejected(validator):
    """Test 8: Verifies renamed non-PDF file with .pdf extension is rejected."""
    fake_pdf = b"This is plain text, not a PDF magic header!"
    fs = FileStorage(stream=io.BytesIO(fake_pdf), filename="fake.pdf")
    with pytest.raises(FileValidationError) as exc:
        validator.validate_file(fs)
    assert exc.value.code == "CORRUPTED_SIGNATURE"


def test_path_traversal_sanitized(validator):
    """Test 9: Verifies directory traversal attempts in filename are neutralized."""
    content = b"Important safe study notes."
    traversal_name = "../../../etc/passwd.txt"
    fs = FileStorage(stream=io.BytesIO(content), filename=traversal_name)
    is_valid, meta = validator.validate_file(fs)
    assert is_valid is True
    assert ".." not in meta["original_filename"]
    assert "/" not in meta["original_filename"]
    assert "\\" not in meta["original_filename"]
    assert meta["stored_filename"].endswith(".txt")


def test_suspicious_filename_sanitized(validator):
    """Test 10: Verifies control characters and weird strings are sanitized safely."""
    content = b"Study content"
    dirty_name = "test\x00file\x1fwith\tctrl.txt"
    fs = FileStorage(stream=io.BytesIO(content), filename=dirty_name)
    is_valid, meta = validator.validate_file(fs)
    assert is_valid is True
    assert "\x00" not in meta["original_filename"]
    assert "\x1f" not in meta["original_filename"]

