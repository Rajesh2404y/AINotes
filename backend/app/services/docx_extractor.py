"""Microsoft Word DOCX Text Extraction Service using python-docx.

Extracts structured paragraphs, headings, and tabular records while maintaining
logical document reading flow and handling corrupted files gracefully.
"""

import logging
from typing import Dict, Any, List
from docx import Document as DocxDocument

logger = logging.getLogger("ainotes.docx_extractor")


def extract_docx_text(file_path: str) -> Dict[str, Any]:
    """Extracts text from paragraphs, headings, and tables within a .docx document.

    Args:
        file_path (str): Filesystem path to the DOCX file.

    Returns:
        Dict[str, Any]: Structured extraction result dictionary.
    """
    try:
        doc = DocxDocument(file_path)
    except Exception as exc:
        logger.error("Failed to parse DOCX document at '%s': %s", file_path, exc)
        return {
            "success": False,
            "file_type": "docx",
            "paragraphs_count": 0,
            "tables_count": 0,
            "total_words": 0,
            "total_characters": 0,
            "text": "",
            "error": f"Failed to parse DOCX document: {str(exc)}",
            "message": "Corrupted or invalid Word DOCX file."
        }

    extracted_elements: List[str] = []
    paragraph_count = 0
    table_count = 0

    # 1. Extract Paragraphs & Headings
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraph_count += 1
            # Check if heading style is applied
            style_name = p.style.name.lower() if p.style and p.style.name else ""
            if "heading" in style_name:
                extracted_elements.append(f"### {text}")
            else:
                extracted_elements.append(text)

    # 2. Extract Tables (Preserving row-column structure for educational notes)
    for table in doc.tables:
        table_rows = []
        for row in table.rows:
            # Extract distinct cell values (avoiding duplicated text from merged cells)
            seen_cells = set()
            row_cells = []
            for cell in row.cells:
                if cell._tc not in seen_cells:
                    seen_cells.add(cell._tc)
                    clean_cell = " ".join(cell.text.split()).strip()
                    row_cells.append(clean_cell if clean_cell else "-")
            if any(c != "-" for c in row_cells):
                table_rows.append(" | ".join(row_cells))

        if table_rows:
            table_count += 1
            table_representation = "\n".join(table_rows)
            extracted_elements.append(f"[Table Data]\n{table_representation}")

    full_text = "\n\n".join(extracted_elements).strip()
    total_characters = len(full_text)
    total_words = len(full_text.split()) if full_text else 0

    return {
        "success": True,
        "file_type": "docx",
        "paragraphs_count": paragraph_count,
        "tables_count": table_count,
        "total_words": total_words,
        "total_characters": total_characters,
        "text": full_text,
        "ocr_required": False,
        "message": "DOCX text extracted successfully"
    }

