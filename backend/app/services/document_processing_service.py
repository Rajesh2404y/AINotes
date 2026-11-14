"""Unified Document Processing Orchestration Service.

Acts as the single point of entry for the complete document processing pipeline:
Format routing -> Text extraction (PDF/DOCX/TXT/Images) -> Targeted OCR for scanned content ->
Text cleaning -> Quality assessment & statistics.
"""

import os
import logging
from typing import Dict, Any, List

from backend.app.services.pdf_extractor import extract_pdf_text
from backend.app.services.docx_extractor import extract_docx_text
from backend.app.services.txt_extractor import extract_txt_text
from backend.app.services.ocr_service import ocr_engine
from backend.app.services.text_cleaning_service import clean_text
from backend.app.services.text_quality_service import assess_text_quality

logger = logging.getLogger("ainotes.document_processor")


class DocumentProcessingService:
    """Coordinates parsing, OCR fallback, cleaning, and quality scoring."""

    def process_document(
        self, file_path: str, file_type: str, original_filename: str = ""
    ) -> Dict[str, Any]:
        """Executes the full extraction and analysis pipeline on a document.

        Args:
            file_path (str): Path to the stored document file.
            file_type (str): Extension/format (pdf, docx, txt, png, jpg, jpeg).
            original_filename (str): Original client file name for reporting.

        Returns:
            Dict[str, Any]: Complete extraction, cleaning, quality, and status payload.
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "file_type": file_type,
                "error": f"File does not exist at path: {file_path}",
                "processing_status": "failed",
                "extraction_quality": "FAILED",
                "raw_text": "",
                "cleaned_text": "",
                "total_pages": 0,
                "total_words": 0,
                "total_characters": 0,
                "ocr_used": False,
                "warnings": ["Source file missing from storage."]
            }

        norm_type = file_type.lower().strip().replace(".", "")
        extraction_result: Dict[str, Any] = {}
        ocr_used = False
        ocr_confidence = 0.0
        ocr_pages_count = 0
        total_pages = 1
        collected_warnings: List[str] = []

        # 1. Route by File Type
        try:
            if norm_type == "pdf":
                pdf_res = extract_pdf_text(file_path)
                if not pdf_res.get("success"):
                    return {
                        "success": False,
                        "file_type": "pdf",
                        "error": pdf_res.get("error", "PDF extraction failed"),
                        "processing_status": "failed",
                        "extraction_quality": "FAILED",
                        "raw_text": "",
                        "cleaned_text": "",
                        "total_pages": pdf_res.get("total_pages", 0),
                        "total_words": 0,
                        "total_characters": 0,
                        "ocr_used": False,
                        "warnings": [pdf_res.get("message", "PDF parsing error")]
                    }

                total_pages = pdf_res.get("total_pages", 1)
                raw_text = pdf_res.get("text", "")

                # Check if scanned pages require OCR
                pages_needing_ocr = pdf_res.get("pages_needing_ocr", [])
                if pages_needing_ocr and ocr_engine.is_available():
                    logger.info("PDF has %d pages requiring OCR. Invoking Tesseract engine.", len(pages_needing_ocr))
                    ocr_results = ocr_engine.ocr_pdf_pages(file_path, pages_needing_ocr)
                    ocr_used = True
                    ocr_pages_count = len(ocr_results)

                    # Merge OCR text into overall document text
                    ocr_text_pieces = []
                    total_conf = 0.0
                    for p_num, res in sorted(ocr_results.items()):
                        p_text = res.get("text", "").strip()
                        if p_text:
                            ocr_text_pieces.append(f"--- Page {p_num} (OCR) ---\n{p_text}")
                            total_conf += res.get("confidence", 0.0)
                        if res.get("warning"):
                            collected_warnings.append(f"Page {p_num}: {res['warning']}")

                    if ocr_text_pieces:
                        if raw_text:
                            raw_text = f"{raw_text}\n\n" + "\n\n".join(ocr_text_pieces)
                        else:
                            raw_text = "\n\n".join(ocr_text_pieces)
                        ocr_confidence = (total_conf / len(ocr_text_pieces)) if ocr_text_pieces else 0.0
                elif pages_needing_ocr:
                    collected_warnings.append(
                        f"PDF contains {len(pages_needing_ocr)} scanned pages requiring OCR, but OCR is currently not available."
                    )

                extraction_result["raw_text"] = raw_text

            elif norm_type == "docx":
                docx_res = extract_docx_text(file_path)
                if not docx_res.get("success"):
                    return {
                        "success": False,
                        "file_type": "docx",
                        "error": docx_res.get("error", "DOCX parsing failed"),
                        "processing_status": "failed",
                        "extraction_quality": "FAILED",
                        "raw_text": "",
                        "cleaned_text": "",
                        "total_pages": 1,
                        "total_words": 0,
                        "total_characters": 0,
                        "ocr_used": False,
                        "warnings": [docx_res.get("message", "DOCX parsing error")]
                    }
                total_pages = 1
                extraction_result["raw_text"] = docx_res.get("text", "")

            elif norm_type == "txt":
                txt_res = extract_txt_text(file_path)
                if not txt_res.get("success"):
                    return {
                        "success": False,
                        "file_type": "txt",
                        "error": txt_res.get("error", "Text extraction failed"),
                        "processing_status": "failed",
                        "extraction_quality": "FAILED",
                        "raw_text": "",
                        "cleaned_text": "",
                        "total_pages": 1,
                        "total_words": 0,
                        "total_characters": 0,
                        "ocr_used": False,
                        "warnings": [txt_res.get("message", "Text reading error")]
                    }
                total_pages = 1
                extraction_result["raw_text"] = txt_res.get("text", "")

            elif norm_type in ("png", "jpg", "jpeg"):
                total_pages = 1
                ocr_res = ocr_engine.extract_text_from_image(file_path)
                ocr_used = ocr_res.get("ocr_used", True)
                ocr_confidence = ocr_res.get("confidence", 0.0)
                ocr_pages_count = 1 if ocr_used else 0
                raw_text = ocr_res.get("text", "")
                if ocr_res.get("warnings"):
                    collected_warnings.extend(ocr_res["warnings"])
                if ocr_res.get("warning"):
                    collected_warnings.append(ocr_res["warning"])

                extraction_result["raw_text"] = raw_text

            else:
                return {
                    "success": False,
                    "file_type": norm_type,
                    "error": f"Unsupported format: {norm_type}",
                    "processing_status": "failed",
                    "extraction_quality": "FAILED",
                    "raw_text": "",
                    "cleaned_text": "",
                    "total_pages": 0,
                    "total_words": 0,
                    "total_characters": 0,
                    "ocr_used": False,
                    "warnings": [f"Unsupported document format '.{norm_type}'"]
                }

        except Exception as exc:
            logger.error("Unexpected error during extraction of '%s': %s", file_path, exc, exc_info=True)
            return {
                "success": False,
                "file_type": norm_type,
                "error": f"Document extraction encountered an internal error: {str(exc)}",
                "processing_status": "failed",
                "extraction_quality": "FAILED",
                "raw_text": "",
                "cleaned_text": "",
                "total_pages": total_pages,
                "total_words": 0,
                "total_characters": 0,
                "ocr_used": ocr_used,
                "warnings": ["Internal extractor exception occurred."]
            }

        # 2. Clean Extracted Text
        raw_text = extraction_result.get("raw_text", "")
        cleaned = clean_text(raw_text)

        # 3. Assess Text Quality
        quality_assessment = assess_text_quality(
            cleaned,
            total_pages=total_pages,
            ocr_pages_count=ocr_pages_count,
            ocr_confidence=ocr_confidence,
            extraction_warnings=collected_warnings
        )

        quality = quality_assessment["quality"]
        total_words = quality_assessment["total_words"]
        total_characters = quality_assessment["total_characters"]
        final_warnings = quality_assessment["warnings"]

        # 4. Determine Processing Status
        if quality == "FAILED":
            status = "failed"
        elif final_warnings:
            status = "completed_with_warnings"
        else:
            status = "completed"

        return {
            "success": quality != "FAILED",
            "file_type": norm_type,
            "raw_text": raw_text,
            "cleaned_text": cleaned,
            "total_pages": total_pages,
            "total_words": total_words,
            "total_characters": total_characters,
            "ocr_used": ocr_used,
            "ocr_confidence": ocr_confidence,
            "extraction_quality": quality,
            "processing_status": status,
            "warnings": final_warnings,
            "metadata": {
                "original_filename": original_filename,
                "total_sentences": quality_assessment["total_sentences"],
                "total_paragraphs": quality_assessment["total_paragraphs"],
                "ocr_pages_count": ocr_pages_count,
            }
        }


# Global default document processor instance
document_processor = DocumentProcessingService()

