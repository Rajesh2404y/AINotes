"""
Translation Export Service.
Generates exportable PDF and TXT files for multilingual translations with
full UTF-8, Unicode font embedding, and complex script support
(covering Tamil, Hindi, French, Spanish, German, etc.).
"""
from __future__ import annotations

import io
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Base directory for static fonts
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
FONTS_DIR = os.path.join(BACKEND_DIR, "static", "fonts")

# Font cache to track registered fonts in ReportLab
_REGISTERED_FONTS: set[str] = set()


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates total page count and draws running headers
    and footers with exact 'Page X of Y' numbering on every page.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int):
        self.saveState()
        font_to_use = "NotoSansTamil" if "NotoSansTamil" in _REGISTERED_FONTS else "Helvetica"
        self.setFont(font_to_use, 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header on pages > 1
        if self._pageNumber > 1:
            self.drawString(40, 810, "AI Notes Summarizer • Multilingual Study Notes")
            self.drawRightString(555, 810, f"Page {self._pageNumber} of {total_pages}")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.6)
            self.line(40, 804, 555, 804)

        # Running Footer on all pages
        footer_left = "AI Notes Summarizer with Multilingual Translator • Academic Study Aid"
        footer_right = f"Page {self._pageNumber} of {total_pages}"
        self.drawString(40, 25, footer_left)
        self.drawRightString(555, 25, footer_right)

        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.6)
        self.line(40, 36, 555, 36)

        self.restoreState()


class TranslationExportService:
    """Exports translated notes to plain text and styled PDF formats with Unicode font embedding."""

    @classmethod
    def _register_fonts(cls) -> None:
        """
        Registers Unicode fonts packaged with the application (Noto Sans Tamil,
        Noto Sans Devanagari) and system fonts (Nirmala UI).
        """
        # 1. Register Tamil Font (Contains English Latin + Tamil Unicode)
        tamil_reg = os.path.join(FONTS_DIR, "NotoSansTamil.ttf")
        tamil_bold = os.path.join(FONTS_DIR, "NotoSansTamil-Bold.ttf")
        if os.path.exists(tamil_reg) and "NotoSansTamil" not in _REGISTERED_FONTS:
            try:
                pdfmetrics.registerFont(TTFont("NotoSansTamil", tamil_reg))
                _REGISTERED_FONTS.add("NotoSansTamil")
                if os.path.exists(tamil_bold):
                    pdfmetrics.registerFont(TTFont("NotoSansTamil-Bold", tamil_bold))
                    _REGISTERED_FONTS.add("NotoSansTamil-Bold")
                    pdfmetrics.registerFontFamily(
                        "NotoSansTamil",
                        normal="NotoSansTamil",
                        bold="NotoSansTamil-Bold"
                    )
                logger.info("Successfully registered NotoSansTamil fonts.")
            except Exception as e:
                logger.warning("Could not register NotoSansTamil: %s", e)

        # 2. Register Devanagari Font (Contains English Latin + Devanagari Unicode)
        deva_reg = os.path.join(FONTS_DIR, "NotoSansDevanagari.ttf")
        deva_bold = os.path.join(FONTS_DIR, "NotoSansDevanagari-Bold.ttf")
        if os.path.exists(deva_reg) and "NotoSansDevanagari" not in _REGISTERED_FONTS:
            try:
                pdfmetrics.registerFont(TTFont("NotoSansDevanagari", deva_reg))
                _REGISTERED_FONTS.add("NotoSansDevanagari")
                if os.path.exists(deva_bold):
                    pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", deva_bold))
                    _REGISTERED_FONTS.add("NotoSansDevanagari-Bold")
                    pdfmetrics.registerFontFamily(
                        "NotoSansDevanagari",
                        normal="NotoSansDevanagari",
                        bold="NotoSansDevanagari-Bold"
                    )
                logger.info("Successfully registered NotoSansDevanagari fonts.")
            except Exception as e:
                logger.warning("Could not register NotoSansDevanagari: %s", e)

        # 3. Register System Indic Font (Nirmala UI) on Windows if available
        win_nirmala = "C:/Windows/Fonts/Nirmala.ttc"
        if os.path.exists(win_nirmala) and "Nirmala" not in _REGISTERED_FONTS:
            try:
                pdfmetrics.registerFont(TTFont("Nirmala", win_nirmala, subfontIndex=0))
                pdfmetrics.registerFont(TTFont("Nirmala-Bold", win_nirmala, subfontIndex=1))
                pdfmetrics.registerFontFamily("Nirmala", normal="Nirmala", bold="Nirmala-Bold")
                _REGISTERED_FONTS.add("Nirmala")
                _REGISTERED_FONTS.add("Nirmala-Bold")
                logger.info("Successfully registered Windows Nirmala fonts.")
            except Exception as e:
                logger.debug("Could not register Nirmala font: %s", e)

    @classmethod
    def get_font_for_target_language(cls, target_lang: str) -> Tuple[str, str]:
        """
        Resolves the appropriate font and bold font names for the target script.
        Never falls back to Helvetica for Tamil or Indic scripts.
        """
        cls._register_fonts()
        lang = (target_lang or "").lower().strip()

        if lang == "ta":
            if "NotoSansTamil" in _REGISTERED_FONTS:
                bold_name = "NotoSansTamil-Bold" if "NotoSansTamil-Bold" in _REGISTERED_FONTS else "NotoSansTamil"
                return "NotoSansTamil", bold_name
            if "Nirmala" in _REGISTERED_FONTS:
                bold_name = "Nirmala-Bold" if "Nirmala-Bold" in _REGISTERED_FONTS else "Nirmala"
                return "Nirmala", bold_name
            raise RuntimeError(
                "Tamil Unicode font (NotoSansTamil.ttf or Nirmala UI) is not available. "
                "Cannot export Tamil PDF without Unicode font support."
            )

        if lang == "hi":
            if "NotoSansDevanagari" in _REGISTERED_FONTS:
                bold_name = "NotoSansDevanagari-Bold" if "NotoSansDevanagari-Bold" in _REGISTERED_FONTS else "NotoSansDevanagari"
                return "NotoSansDevanagari", bold_name
            if "Nirmala" in _REGISTERED_FONTS:
                bold_name = "Nirmala-Bold" if "Nirmala-Bold" in _REGISTERED_FONTS else "Nirmala"
                return "Nirmala", bold_name

        if lang in ["te", "kn", "ml"] and "Nirmala" in _REGISTERED_FONTS:
            bold_name = "Nirmala-Bold" if "Nirmala-Bold" in _REGISTERED_FONTS else "Nirmala"
            return "Nirmala", bold_name

        # For Latin-based scripts or default
        if "NotoSansTamil" in _REGISTERED_FONTS:
            bold_name = "NotoSansTamil-Bold" if "NotoSansTamil-Bold" in _REGISTERED_FONTS else "NotoSansTamil"
            return "NotoSansTamil", bold_name

        return "Helvetica", "Helvetica-Bold"

    @staticmethod
    def _format_markdown_for_reportlab(text: str) -> str:
        """
        Converts basic markdown (bold, italic) and escapes XML special entities
        for safe rendering in ReportLab Paragraphs.
        """
        if not text:
            return ""

        # Escape XML entities first
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        # Convert markdown bold **word** -> <b>word</b>
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)

        # Convert markdown italic *word* or _word_ -> <i>word</i>
        escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)

        return escaped

    @classmethod
    def export_txt(cls, translation_data: Dict[str, Any], doc_title: str = "Translated Notes") -> str:
        """
        Formats a translated summary into a clean UTF-8 text document, preserving
        Tamil Unicode, English terminology, and structural formatting.
        """
        source_lang = (translation_data.get("source_language") or "en").upper()
        target_lang = (translation_data.get("target_language") or "ta").upper()
        model_name = translation_data.get("model_name") or "NLLB-200 / Multilingual Engine"
        export_time = datetime.utcnow().strftime("%d %b %Y, %I:%M:%S UTC")

        lines = [
            "=" * 72,
            f"TRANSLATED STUDY NOTES: {doc_title.upper()}",
            "=" * 72,
            f"Translation       : {source_lang} -> {target_lang}",
            f"Source Language   : {source_lang}",
            f"Target Language   : {target_lang}",
            f"Translation Engine: {model_name}",
            f"Exported At       : {export_time}",
            "=" * 72,
            "",
            "-" * 50,
            f"TRANSLATED CONTENT ({target_lang})",
            "-" * 50,
            (translation_data.get("translated_text") or "").strip(),
            "",
        ]

        orig_text = (translation_data.get("original_text") or "").strip()
        if orig_text:
            lines.extend([
                "-" * 50,
                f"ORIGINAL REFERENCE CONTENT ({source_lang})",
                "-" * 50,
                orig_text,
                "",
            ])

        lines.extend([
            "=" * 72,
            "Generated by AI Notes Summarizer & Multilingual Translator Engine",
            "=" * 72,
        ])

        return "\n".join(lines)

    @classmethod
    def export_pdf(cls, translation_data: Dict[str, Any], doc_title: str = "Translated Notes") -> io.BytesIO:
        """
        Builds a high-fidelity, publication-grade academic study notes PDF
        with embedded Tamil and multilingual Unicode fonts, complex script support,
        A4 page setup, and two-pass 'Page X of Y' numbering.
        """
        target_lang = (translation_data.get("target_language") or "ta").lower().strip()
        source_lang = (translation_data.get("source_language") or "en").lower().strip()
        font_regular, font_bold = cls.get_font_for_target_language(target_lang)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=45,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()

        # Custom Typography Styles using Unicode Fonts
        title_style = ParagraphStyle(
            "TransDocTitle",
            parent=styles["Heading1"],
            fontName=font_bold,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4
        )

        section_heading = ParagraphStyle(
            "TransSectionHeading",
            parent=styles["Heading2"],
            fontName=font_bold,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            "TransBodyText",
            parent=styles["BodyText"],
            fontName=font_regular,
            fontSize=9.5,
            leading=14.5,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            "TransBulletText",
            parent=body_style,
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=4
        )

        meta_label_style = ParagraphStyle(
            "TransMetaLabel",
            parent=styles["Normal"],
            fontName=font_bold,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569")
        )

        meta_val_style = ParagraphStyle(
            "TransMetaVal",
            parent=styles["Normal"],
            fontName=font_regular,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a")
        )

        story: List[Any] = []

        # 1. Header Title
        clean_title = cls._format_markdown_for_reportlab(doc_title)
        story.append(Paragraph(clean_title, title_style))
        story.append(Spacer(1, 4))

        # 2. Metadata Information Card Table
        export_date = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")
        meta_table_data = [
            [
                Paragraph("<b>Language Pair:</b>", meta_label_style),
                Paragraph(f"{source_lang.upper()} -&gt; {target_lang.upper()}", meta_val_style),
                Paragraph("<b>Export Date:</b>", meta_label_style),
                Paragraph(export_date, meta_val_style),
            ],
            [
                Paragraph("<b>Translation Model:</b>", meta_label_style),
                Paragraph(translation_data.get("model_name") or "NLLB-200 / deep-translator", meta_val_style),
                Paragraph("<b>Total Chunks:</b>", meta_label_style),
                Paragraph(str(translation_data.get("total_chunks") or 1), meta_val_style),
            ]
        ]

        meta_table = Table(meta_table_data, colWidths=[100, 155, 90, 170])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

        # 3. Section: Translated Content
        lang_display_names = {
            "ta": "தமிழ் (Tamil)",
            "hi": "हिन्दी (Hindi)",
            "fr": "Français (French)",
            "es": "Español (Spanish)",
            "de": "Deutsch (German)",
            "te": "తెలుగు (Telugu)",
            "kn": "ಕನ್ನಡ (Kannada)",
            "ml": "മലയാളം (Malayalam)",
            "en": "English"
        }
        target_display = lang_display_names.get(target_lang, target_lang.upper())
        story.append(Paragraph(f"Translated Content — {target_display}", section_heading))

        translated_text = (translation_data.get("translated_text") or "").strip()
        if not translated_text:
            story.append(Paragraph("<i>[No translated text available]</i>", body_style))
        else:
            paragraphs = translated_text.split("\n\n")
            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue

                lines = para_clean.split("\n")
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue

                    # Check for bullet point
                    if line_clean.startswith(("•", "-", "* ")) and len(line_clean) > 2:
                        bullet_body = re.sub(r"^([•\-\*]\s*)", "", line_clean)
                        fmt_bullet = f"• {cls._format_markdown_for_reportlab(bullet_body)}"
                        story.append(Paragraph(fmt_bullet, bullet_style))
                    elif re.match(r"^\d+\.\s+", line_clean):
                        # Numbered list item
                        fmt_num = cls._format_markdown_for_reportlab(line_clean)
                        story.append(Paragraph(fmt_num, bullet_style))
                    elif line_clean.startswith("---") and line_clean.endswith("---"):
                        # Document page marker / subtitle
                        story.append(Spacer(1, 4))
                        story.append(Paragraph(f"<b>{cls._format_markdown_for_reportlab(line_clean)}</b>", meta_label_style))
                        story.append(Spacer(1, 2))
                    else:
                        fmt_para = cls._format_markdown_for_reportlab(line_clean)
                        story.append(Paragraph(fmt_para, body_style))

        # 4. Section: Original Reference Content
        orig_text = (translation_data.get("original_text") or "").strip()
        if orig_text:
            story.append(Spacer(1, 8))
            story.append(KeepTogether([
                HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8),
                Paragraph(f"Original Reference Content ({source_lang.upper()})", section_heading)
            ]))

            orig_paragraphs = orig_text.split("\n\n")
            for para in orig_paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue
                lines = para_clean.split("\n")
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    if line_clean.startswith(("•", "-", "* ")) and len(line_clean) > 2:
                        bullet_body = re.sub(r"^([•\-\*]\s*)", "", line_clean)
                        fmt_bullet = f"• {cls._format_markdown_for_reportlab(bullet_body)}"
                        story.append(Paragraph(fmt_bullet, bullet_style))
                    else:
                        fmt_para = cls._format_markdown_for_reportlab(line_clean)
                        story.append(Paragraph(fmt_para, body_style))

        # Build PDF using NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer


# Global export service instance
translation_export_service = TranslationExportService()
