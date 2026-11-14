"""PDF Text Extraction Service using PyMuPDF (fitz).

Implements high-performance, page-by-page text extraction, paragraph structure preservation,
scanned/image page detection for OCR routing, and encrypted document detection.
"""

import logging
from typing import Dict, Any, List
try:
    import pymupdf as fitz  # Modern PyMuPDF API
except ImportError:
    import fitz  # Fallback for legacy environments

logger = logging.getLogger("ainotes.pdf_extractor")


class PDFExtractionError(Exception):
    """Exception raised when PDF parsing encounters unrecoverable errors."""
    pass


def extract_pdf_text(file_path: str) -> Dict[str, Any]:
    """Extracts textual content and structural layout from a PDF file.

    Args:
        file_path (str): Absolute or relative filesystem path to the PDF.

    Returns:
        Dict[str, Any]: Structured extraction result dictionary.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("Failed to open PDF at '%s': %s", file_path, exc)
        return {
            "success": False,
            "file_type": "pdf",
            "total_pages": 0,
            "extracted_pages": 0,
            "text": "",
            "ocr_required": False,
            "pages_needing_ocr": [],
            "page_details": [],
            "error": f"Failed to open PDF document: {str(exc)}",
            "message": "Corrupted or invalid PDF document."
        }

    # 1. Password / Encryption Guard
    if doc.is_encrypted:
        doc.close()
        return {
            "success": False,
            "file_type": "pdf",
            "total_pages": 0,
            "extracted_pages": 0,
            "text": "",
            "ocr_required": False,
            "pages_needing_ocr": [],
            "page_details": [],
            "error": "The PDF is encrypted or password-protected.",
            "message": "Password-protected PDFs are not supported for automated processing."
        }

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        return {
            "success": True,
            "file_type": "pdf",
            "total_pages": 0,
            "extracted_pages": 0,
            "text": "",
            "ocr_required": False,
            "pages_needing_ocr": [],
            "page_details": [],
            "message": "The PDF document contains 0 pages."
        }

    extracted_pages_count = 0
    pages_needing_ocr: List[int] = []
    page_details: List[Dict[str, Any]] = []
    accumulated_text_blocks: List[str] = []

    try:
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            # Extract text blocks preserving paragraph flow
            # "blocks" format returns tuples: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type 0 = text, 1 = image
            blocks = page.get_text("blocks")
            page_text_pieces = []

            for block in blocks:
                if len(block) >= 5 and block[6] == 0:  # Text block
                    block_text = block[4].strip()
                    if block_text:
                        page_text_pieces.append(block_text)

            page_text = "\n\n".join(page_text_pieces).strip()
            char_count = len(page_text)
            word_count = len(page_text.split()) if page_text else 0

            # Inspect images on page
            images = page.get_images(full=True)
            has_images = len(images) > 0

            # Determine if this specific page requires OCR:
            # Low character count (< 50 chars) but contains image content
            needs_ocr = (char_count < 50 and has_images) or (char_count == 0 and has_images)
            if needs_ocr:
                pages_needing_ocr.append(page_num)

            if char_count > 0:
                extracted_pages_count += 1
                accumulated_text_blocks.append(f"--- Page {page_num} ---\n{page_text}")

            page_details.append({
                "page_number": page_num,
                "character_count": char_count,
                "word_count": word_count,
                "has_images": has_images,
                "ocr_needed": needs_ocr,
                "snippet": page_text[:120] if page_text else ""
            })

    except Exception as exc:
        logger.error("Error reading pages from PDF '%s': %s", file_path, exc)
    finally:
        doc.close()

    full_text = "\n\n".join(accumulated_text_blocks).strip()
    ocr_required = len(pages_needing_ocr) > 0

    return {
        "success": True,
        "file_type": "pdf",
        "total_pages": total_pages,
        "extracted_pages": extracted_pages_count,
        "text": full_text,
        "ocr_required": ocr_required,
        "pages_needing_ocr": pages_needing_ocr,
        "page_details": page_details,
        "message": "PDF text extracted successfully"
    }

