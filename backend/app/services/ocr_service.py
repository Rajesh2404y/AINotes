"""OCR (Optical Character Recognition) Processing Engine.

Supports scanned PDF pages and standalone image files (PNG, JPG, JPEG).
Integrates pytesseract with Pillow/OpenCV image preprocessing, multi-language support (English, Tamil),
confidence analysis, and graceful fallback when Tesseract is not installed on the host system.
"""

import os
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import pymupdf as fitz

logger = logging.getLogger("ainotes.ocr_service")


class OCRService:
    """Enterprise OCR pipeline coordinating image preprocessing and character recognition."""

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        languages: str = "eng+tam",
        enabled: bool = True
    ):
        self.enabled = enabled
        self.languages = languages
        self.tesseract_cmd = self._resolve_tesseract_cmd(tesseract_cmd)
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    def _resolve_tesseract_cmd(self, explicit_cmd: Optional[str] = None) -> Optional[str]:
        """Discovers tesseract binary across PATH and standard OS installation directories."""
        if explicit_cmd and os.path.exists(explicit_cmd):
            return explicit_cmd

        env_cmd = os.getenv("TESSERACT_CMD")
        if env_cmd and os.path.exists(env_cmd):
            return env_cmd

        # Check system PATH
        path_binary = shutil.which("tesseract")
        if path_binary:
            return path_binary

        # Common Windows installation locations
        windows_defaults = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in windows_defaults:
            if os.path.exists(p):
                return p

        # Common Linux / Unix locations
        unix_defaults = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]
        for p in unix_defaults:
            if os.path.exists(p):
                return p

        return None

    def is_available(self) -> bool:
        """Checks if Tesseract binary is operational on the host system."""
        if not self.enabled:
            return False
        if not self.tesseract_cmd:
            return False
        try:
            # Check version
            ver = pytesseract.get_tesseract_version()
            return ver is not None
        except Exception:
            return False

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocesses image to enhance OCR text legibility.

        Performs:
        1. Grayscale conversion.
        2. Contrast enhancement.
        3. Mild sharpening.
        """
        try:
            # 1. Convert to Grayscale
            gray = image.convert("L")

            # 2. Enhance contrast
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.8)

            # 3. Apply mild sharpening
            sharpened = enhanced.filter(ImageFilter.SHARPEN)
            return sharpened
        except Exception as exc:
            logger.warning("Image preprocessing failed, falling back to original: %s", exc)
            return image

    def extract_text_from_image(self, file_path_or_image) -> Dict[str, Any]:
        """Executes OCR on an image file or PIL Image instance.

        Args:
            file_path_or_image: Path string or PIL.Image.Image object.

        Returns:
            Dict[str, Any]: Extraction results with confidence metrics and warnings.
        """
        if not self.enabled:
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "ocr_used": False,
                "warning": "OCR engine is disabled in configuration (OCR_ENABLED=false)."
            }

        if not self.is_available():
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "ocr_used": False,
                "warning": (
                    "Tesseract OCR binary not found. Please install Tesseract-OCR and ensure "
                    "it is on the system PATH or configure TESSERACT_CMD in .env."
                )
            }

        try:
            if isinstance(file_path_or_image, (str, bytes)):
                image = Image.open(file_path_or_image)
            else:
                image = file_path_or_image

            processed_img = self.preprocess_image(image)

            # Attempt multi-language OCR, falling back to English if target language data missing
            ocr_text = ""
            conf_score = 0.0
            used_lang = self.languages

            try:
                data = pytesseract.image_to_data(
                    processed_img,
                    lang=self.languages,
                    output_type=pytesseract.Output.DICT
                )
                conf_values = [int(c) for c in data["conf"] if int(c) != -1]
                conf_score = (sum(conf_values) / len(conf_values)) if conf_values else 0.0
                ocr_text = pytesseract.image_to_string(processed_img, lang=self.languages).strip()
            except pytesseract.TesseractError as terr:
                logger.warning("OCR with lang '%s' failed, attempting fallback to 'eng': %s", self.languages, terr)
                used_lang = "eng"
                data = pytesseract.image_to_data(
                    processed_img,
                    lang="eng",
                    output_type=pytesseract.Output.DICT
                )
                conf_values = [int(c) for c in data["conf"] if int(c) != -1]
                conf_score = (sum(conf_values) / len(conf_values)) if conf_values else 0.0
                ocr_text = pytesseract.image_to_string(processed_img, lang="eng").strip()

            word_count = len(ocr_text.split()) if ocr_text else 0
            warnings = []
            if conf_score < 40 and word_count > 0:
                warnings.append("Low OCR confidence score (< 40%). Image quality may be poor.")
            if word_count == 0:
                warnings.append("No recognizable textual characters detected in image.")

            return {
                "success": True,
                "text": ocr_text,
                "confidence": round(conf_score, 2),
                "ocr_used": True,
                "language_used": used_lang,
                "word_count": word_count,
                "character_count": len(ocr_text),
                "warnings": warnings
            }

        except Exception as exc:
            logger.error("OCR execution error: %s", exc)
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "ocr_used": True,
                "error": str(exc),
                "warning": f"OCR extraction failed: {str(exc)}"
            }

    def ocr_pdf_pages(
        self, pdf_path: str, pages_to_ocr: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Renders specific scanned pages from a PDF into images and runs OCR on them.

        Args:
            pdf_path (str): Filesystem path to the PDF.
            pages_to_ocr (List[int]): 1-indexed page numbers requiring OCR.

        Returns:
            Dict[int, Dict[str, Any]]: Map of page_number -> OCR result dictionary.
        """
        page_results: Dict[int, Dict[str, Any]] = {}
        if not pages_to_ocr:
            return page_results

        if not self.is_available():
            logger.info("Skipping PDF page OCR because Tesseract is not available on host system.")
            for p_num in pages_to_ocr:
                page_results[p_num] = {
                    "success": False,
                    "text": "",
                    "warning": "Tesseract OCR binary not found on host system."
                }
            return page_results

        try:
            doc = fitz.open(pdf_path)
            for page_num in pages_to_ocr:
                if 1 <= page_num <= len(doc):
                    page = doc[page_num - 1]
                    # Render page at 200 DPI for high-accuracy OCR
                    pix = page.get_pixmap(dpi=200)
                    import io
                    img_bytes = io.BytesIO(pix.tobytes("png"))
                    img = Image.open(img_bytes)

                    ocr_res = self.extract_text_from_image(img)
                    page_results[page_num] = ocr_res
            doc.close()
        except Exception as exc:
            logger.error("Error rendering PDF pages for OCR at '%s': %s", pdf_path, exc)

        return page_results


# Global default OCR service instance
ocr_engine = OCRService(
    tesseract_cmd=os.getenv("TESSERACT_CMD", ""),
    languages=os.getenv("TESSERACT_LANGUAGES", "eng+tam"),
    enabled=os.getenv("OCR_ENABLED", "true").lower() in ("true", "1", "yes")
)

