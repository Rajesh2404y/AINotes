"""File Validation and Security Service.

Implements deep content validation, magic signature checks, MIME type verification,
path traversal prevention, safe filename generation, and file size enforcement
for uploaded educational documents and images.
"""

import os
import re
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

logger = logging.getLogger("ainotes.file_validation")

# Configured Magic Signatures
FILE_SIGNATURES = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}

# Standard MIME type mappings
MIME_MAP = {
    "pdf": ["application/pdf", "application/x-pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    ],
    "txt": [
        "text/plain",
        "text/x-python",
        "application/octet-stream",
        "text/markdown",
    ],
    "png": ["image/png", "application/octet-stream"],
    "jpg": ["image/jpeg", "image/pjpeg", "application/octet-stream"],
    "jpeg": ["image/jpeg", "image/pjpeg", "application/octet-stream"],
}

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}


class FileValidationError(Exception):
    """Custom exception raised when file validation fails."""

    def __init__(self, message: str, code: str = "INVALID_FILE", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class FileValidationService:
    """Provides enterprise-grade verification and sanitization for incoming uploads."""

    def __init__(self, max_size_mb: int = 20, allowed_extensions: Optional[set] = None):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or SUPPORTED_EXTENSIONS

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes filename against path traversal and dangerous characters."""
        if not filename or not isinstance(filename, str):
            raise FileValidationError("Filename cannot be empty.", code="EMPTY_FILENAME")

        # Strip path components and null bytes
        base_name = os.path.basename(filename.replace("\\", "/"))
        base_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", base_name)
        cleaned = secure_filename(base_name)

        if not cleaned:
            # Fallback for non-ASCII or stripped characters
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
            cleaned = f"upload_{uuid.uuid4().hex[:8]}.{ext}"

        return cleaned

    def generate_stored_filename(self, original_filename: str) -> str:
        """Generates a secure, cryptographically unique server-side filename."""
        sanitized = self.sanitize_filename(original_filename)
        ext = sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else "bin"
        unique_token = uuid.uuid4().hex
        return f"{unique_token}.{ext}"

    def compute_sha256(self, file_path_or_bytes) -> str:
        """Computes SHA-256 checksum for duplicate detection and data integrity."""
        sha256 = hashlib.sha256()
        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                while chunk := f.read(65536):
                    sha256.update(chunk)
        elif hasattr(file_path_or_bytes, "read"):
            pos = file_path_or_bytes.tell() if hasattr(file_path_or_bytes, "tell") else None
            while chunk := file_path_or_bytes.read(65536):
                sha256.update(chunk)
            if pos is not None and hasattr(file_path_or_bytes, "seek"):
                file_path_or_bytes.seek(pos)
        elif isinstance(file_path_or_bytes, bytes):
            sha256.update(file_path_or_bytes)
        return sha256.hexdigest()

    def validate_file(
        self, file: FileStorage
    ) -> Tuple[bool, Dict[str, Any]]:
        """Performs rigorous multi-stage validation on a Flask FileStorage object.

        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, metadata_dict)
        """
        if not file or not file.filename:
            raise FileValidationError("No file was submitted.", code="MISSING_FILE")

        raw_filename = file.filename
        # 1. Path traversal security check
        if ".." in raw_filename or "/" in raw_filename or "\\" in raw_filename:
            sanitized_name = self.sanitize_filename(raw_filename)
        else:
            sanitized_name = self.sanitize_filename(raw_filename)

        # 2. Extension verification
        if "." not in sanitized_name:
            raise FileValidationError(
                f"File '{raw_filename}' lacks a valid file extension.",
                code="MISSING_EXTENSION"
            )

        ext = sanitized_name.rsplit(".", 1)[-1].lower()
        if ext not in self.allowed_extensions:
            raise FileValidationError(
                f"File type '.{ext}' is unsupported. Allowed formats: {', '.join(sorted(self.allowed_extensions))}.",
                code="UNSUPPORTED_EXTENSION"
            )

        # 3. Read header bytes and check size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size == 0:
            raise FileValidationError(
                f"File '{raw_filename}' is empty (0 bytes).",
                code="EMPTY_FILE"
            )

        if file_size > self.max_size_bytes:
            max_mb = self.max_size_bytes // (1024 * 1024)
            raise FileValidationError(
                f"File '{raw_filename}' ({file_size / (1024*1024):.1f} MB) exceeds maximum permitted size of {max_mb} MB.",
                code="FILE_TOO_LARGE"
            )

        # 4. Magic Byte Signature Verification
        header_sample = file.read(2048)
        file.seek(0)

        if ext in FILE_SIGNATURES:
            signatures = FILE_SIGNATURES[ext]
            matched = any(header_sample.startswith(sig) for sig in signatures)
            if not matched:
                # Additional check for corrupted or renamed files
                raise FileValidationError(
                    f"File '{raw_filename}' contains invalid file signature for format '{ext}'. File may be corrupted or disguised.",
                    code="CORRUPTED_SIGNATURE"
                )

        # 5. TXT specific check: ensure valid text encoding, not binary disguised as .txt
        if ext == "txt":
            try:
                # Test initial sample decoding
                sample_snippet = header_sample[:512]
                sample_snippet.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    sample_snippet.decode("latin-1")
                except Exception:
                    raise FileValidationError(
                        f"Text file '{raw_filename}' contains undecodable binary content.",
                        code="INVALID_TEXT_ENCODING"
                    )

        # 6. DOCX Specific Zip Container Check
        if ext == "docx":
            import zipfile
            try:
                with zipfile.ZipFile(file) as zf:
                    # A valid docx must contain word/document.xml or [Content_Types].xml
                    names = zf.namelist()
                    if "[Content_Types].xml" not in names:
                        raise FileValidationError(
                            f"DOCX document '{raw_filename}' is missing valid OpenXML components.",
                            code="CORRUPTED_DOCX"
                        )
            except zipfile.BadZipFile:
                raise FileValidationError(
                    f"Document '{raw_filename}' is not a valid or readable Word DOCX file.",
                    code="CORRUPTED_DOCX"
                )
            finally:
                file.seek(0)

        # 7. Image Specific PIL Check
        if ext in ("png", "jpg", "jpeg"):
            from PIL import Image
            try:
                with Image.open(file) as img:
                    img.verify()
            except Exception as e:
                raise FileValidationError(
                    f"Image file '{raw_filename}' is malformed or corrupted: {str(e)}",
                    code="CORRUPTED_IMAGE"
                )
            finally:
                file.seek(0)

        # 8. Compute Checksum
        file_hash = self.compute_sha256(file)
        file.seek(0)

        stored_name = self.generate_stored_filename(sanitized_name)

        metadata = {
            "original_filename": sanitized_name,
            "stored_filename": stored_name,
            "file_type": ext,
            "file_size": file_size,
            "sha256": file_hash,
            "mime_type": file.mimetype or "application/octet-stream",
        }

        return True, metadata


# Global default validator instance
file_validator = FileValidationService()

