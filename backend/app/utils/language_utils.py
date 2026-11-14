"""
Centralized Language Management and Code Mapping Utilities.
Provides standard ISO 639-1 to NLLB-200 FLORES codes and MarianMT mappings
for all 9 supported academic languages.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: List[Dict[str, str]] = [
    {
        "code": "en",
        "name": "English",
        "nllb_code": "eng_Latn",
        "native_name": "English",
        "script": "Latin"
    },
    {
        "code": "ta",
        "name": "Tamil",
        "nllb_code": "tam_Taml",
        "native_name": "தமிழ்",
        "script": "Tamil"
    },
    {
        "code": "hi",
        "name": "Hindi",
        "nllb_code": "hin_Deva",
        "native_name": "हिन्दी",
        "script": "Devanagari"
    },
    {
        "code": "te",
        "name": "Telugu",
        "nllb_code": "tel_Telu",
        "native_name": "తెలుగు",
        "script": "Telugu"
    },
    {
        "code": "ml",
        "name": "Malayalam",
        "nllb_code": "mal_Mlym",
        "native_name": "മലയാളം",
        "script": "Malayalam"
    },
    {
        "code": "kn",
        "name": "Kannada",
        "nllb_code": "kan_Knda",
        "native_name": "ಕನ್ನಡ",
        "script": "Kannada"
    },
    {
        "code": "fr",
        "name": "French",
        "nllb_code": "fra_Latn",
        "native_name": "Français",
        "script": "Latin"
    },
    {
        "code": "es",
        "name": "Spanish",
        "nllb_code": "spa_Latn",
        "native_name": "Español",
        "script": "Latin"
    },
    {
        "code": "de",
        "name": "German",
        "nllb_code": "deu_Latn",
        "native_name": "Deutsch",
        "script": "Latin"
    }
]

# Quick lookup indexes
CODE_TO_LANG: Dict[str, Dict[str, str]] = {l["code"]: l for l in SUPPORTED_LANGUAGES}
NLLB_TO_CODE: Dict[str, str] = {l["nllb_code"]: l["code"] for l in SUPPORTED_LANGUAGES}
NAME_TO_CODE: Dict[str, str] = {l["name"].lower(): l["code"] for l in SUPPORTED_LANGUAGES}


def get_supported_languages() -> List[Dict[str, str]]:
    """Returns the list of all configured languages and display metadata."""
    return [
        {
            "code": l["code"],
            "name": l["name"],
            "native_name": l["native_name"],
            "script": l["script"]
        }
        for l in SUPPORTED_LANGUAGES
    ]


def is_language_supported(lang_code: str) -> bool:
    """Verifies whether an ISO language code is supported."""
    if not lang_code:
        return False
    return lang_code.lower().strip() in CODE_TO_LANG


def get_nllb_code(lang_code: str) -> Optional[str]:
    """Resolves an ISO-639-1 code to its NLLB FLORES-200 identifier."""
    if not lang_code:
        return None
    lang = CODE_TO_LANG.get(lang_code.lower().strip())
    return lang["nllb_code"] if lang else None


def validate_language_pair(source_lang: str, target_lang: str) -> Tuple[bool, Optional[str]]:
    """
    Validates source and target language compatibility.
    """
    s = (source_lang or "").lower().strip()
    t = (target_lang or "").lower().strip()

    if not s:
        return False, "Source language code is required."
    if not t:
        return False, "Target language code is required."

    if s not in CODE_TO_LANG:
        return False, f"Unsupported source language '{source_lang}'."
    if t not in CODE_TO_LANG:
        return False, f"Unsupported target language '{target_lang}'."

    if s == t:
        return False, f"Source and target languages cannot be identical ('{s}')."

    return True, None

