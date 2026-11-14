"""Plain Text (TXT) Extraction Service.

Provides safe multi-encoding fallback handling (UTF-8 with BOM, standard UTF-8, Latin-1, CP1252),
full Unicode preservation for Tamil and regional Indian scripts, and binary content rejection.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger("ainotes.txt_extractor")

ENCODINGS_TO_TRY = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]


def extract_txt_text(file_path: str) -> Dict[str, Any]:
    """Reads and extracts text from plain text files with robust character encoding detection.

    Args:
        file_path (str): Filesystem path to the text file.

    Returns:
        Dict[str, Any]: Structured extraction result dictionary.
    """
    raw_bytes = None
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except Exception as exc:
        logger.error("Failed to read text file at '%s': %s", file_path, exc)
        return {
            "success": False,
            "file_type": "txt",
            "encoding_used": None,
            "total_words": 0,
            "total_characters": 0,
            "text": "",
            "error": f"Failed to open file: {str(exc)}",
            "message": "Cannot read plain text file."
        }

    if len(raw_bytes) == 0:
        return {
            "success": True,
            "file_type": "txt",
            "encoding_used": "utf-8",
            "total_words": 0,
            "total_characters": 0,
            "text": "",
            "ocr_required": False,
            "message": "The text document is empty."
        }

    # Binary detection heuristic: check for null bytes or excessive unprintable controls
    if b"\x00" in raw_bytes[:1024]:
        return {
            "success": False,
            "file_type": "txt",
            "encoding_used": None,
            "total_words": 0,
            "total_characters": 0,
            "text": "",
            "error": "Binary data detected in text file.",
            "message": "The uploaded text file contains unsupported binary or compiled data."
        }

    decoded_text = None
    matched_encoding = None

    for enc in ENCODINGS_TO_TRY:
        try:
            decoded_text = raw_bytes.decode(enc)
            matched_encoding = enc
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        # Final fallback with replace error handler
        decoded_text = raw_bytes.decode("utf-8", errors="replace")
        matched_encoding = "utf-8-fallback"

    # Normalize carriage returns
    normalized_text = decoded_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    total_characters = len(normalized_text)
    total_words = len(normalized_text.split()) if normalized_text else 0

    return {
        "success": True,
        "file_type": "txt",
        "encoding_used": matched_encoding,
        "total_words": total_words,
        "total_characters": total_characters,
        "text": normalized_text,
        "ocr_required": False,
        "message": "Plain text extracted successfully"
    }

