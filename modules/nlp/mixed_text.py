"""
OmniFile AI Processor — Mixed Text Processing
==============================================
Source: advanced-ocr/postprocessing/mixed_text.py

Handles Arabic + English + Numbers mixed text commonly found in
medical and engineering documents.

Example: "التخدير العام: 0.05 mg/kg IV"

Capabilities:
- Language detection (Arabic / English / mixed)
- Arabic/English/Numbers extraction and separation
- Technical terms protection (units, medical abbreviations, etc.)
- Bidirectional text spacing fixes
- Number ordering correction in Arabic context
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Arabic character Unicode ranges
ARABIC_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)

# Pattern for mixed Arabic-English text with numbers
MIXED_PATTERN = re.compile(
    r"[A-Za-z0-9\u0600-\u06FF\u0750-\u077F\s.,;:()\-/]+"
)

# ---------------------------------------------------------------------------
# Technical-term dictionary (medical / engineering / IT)
# ---------------------------------------------------------------------------

TECHNICAL_TERMS = {
    # Units
    "mg", "kg", "ml", "mm", "cm", "g", "l", "m",
    # Administration routes
    "IV", "IM", "SC", "PO", "PR",
    # Medical imaging
    "ECG", "EEG", "MRI", "CT", "US", "X-ray",
    # Measurements
    "mmHg", "kPa", "pH",
    # Vitals
    "BMI", "BP", "HR", "RR", "SpO2", "Temp",
    # Lab
    "DNA", "RNA", "PCR", "ELISA", "HIV", "HBV", "HCV",
    # Tech
    "API", "URL", "HTTP", "HTTPS", "JSON", "XML",
    # Compound units
    "kg/m", "mg/kg", "ml/h", "µg/ml", "IU/L",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    """Detect the dominant language of a text string.

    Args:
        text: Input text.

    Returns:
        Language code: ``"ar"``, ``"en"``, ``"mixed"``, or ``"unknown"``.
    """
    if not text or not text.strip():
        return "unknown"

    text = text.strip()
    arabic_chars = len(ARABIC_PATTERN.findall(text))
    latin_chars = len(re.findall(r"[A-Za-z]", text))
    digit_chars = len(re.findall(r"[0-9]", text))

    total_text_chars = arabic_chars + latin_chars

    if total_text_chars == 0:
        return "unknown"

    arabic_ratio = arabic_chars / total_text_chars
    latin_ratio = latin_chars / total_text_chars

    # If digits are significant alongside text, it's mixed
    has_significant_digits = digit_chars > total_text_chars * 0.2

    if arabic_ratio > 0.7:
        return "ar"
    elif latin_ratio > 0.7:
        return "en"
    else:
        return "mixed"


def optimize_mixed_text(text: str) -> str:
    """Optimize text that contains mixed Arabic, English, and numbers.

    Handles:
    1. Correct ordering of Arabic-English transitions
    2. Preserve technical terms and abbreviations
    3. Fix spacing between Arabic and Latin characters
    4. Handle bidirectional text properly

    Args:
        text: Raw OCR text that may contain mixed content.

    Returns:
        Optimized text with correct ordering.
    """
    if not text or not text.strip():
        return text

    # Step 1: Fix spacing between Arabic and Latin characters
    text = _fix_mixed_spacing(text)

    # Step 2: Protect technical terms
    text = _protect_technical_terms(text)

    # Step 3: Fix number ordering in Arabic context
    text = _fix_number_ordering(text)

    return text


def extract_arabic_text(text: str) -> str:
    """Extract only Arabic text from mixed content."""
    return " ".join(ARABIC_PATTERN.findall(text))


def extract_latin_text(text: str) -> str:
    """Extract only Latin/English text from mixed content."""
    return " ".join(re.findall(r"[A-Za-z]+", text))


def extract_numbers(text: str) -> str:
    """Extract only numbers from mixed content."""
    return " ".join(re.findall(r"[\d.,]+", text))


def separate_text_components(text: str) -> dict:
    """Separate mixed text into its components.

    Args:
        text: Mixed Arabic/English/number text.

    Returns:
        Dict with ``'arabic'``, ``'english'``, ``'numbers'``, and
        ``'language'`` keys.
    """
    return {
        "arabic": extract_arabic_text(text),
        "english": extract_latin_text(text),
        "numbers": extract_numbers(text),
        "language": detect_language(text),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fix_mixed_spacing(text: str) -> str:
    """Fix spacing between Arabic and Latin characters/numbers.

    Ensures proper visual separation between RTL and LTR text runs.

    Example: ``"الوزن70kg"`` → ``"الوزن 70 kg"``
    """
    # Arabic→Latin: add space
    text = re.sub(
        r"([\u0600-\u06FF])([A-Za-z0-9])",
        r"\1 \2",
        text,
    )

    # Latin→Arabic: add space
    text = re.sub(
        r"([A-Za-z0-9])([\u0600-\u06FF])",
        r"\1 \2",
        text,
    )

    # Clean up multiple spaces
    text = re.sub(r"  +", " ", text)

    return text.strip()


def _protect_technical_terms(text: str) -> str:
    """Ensure technical terms and abbreviations are not broken apart.

    Example: ``"m g"`` → ``"mg"`` (if context suggests it's a unit).

    Uses a conservative approach — only fixes clearly broken terms
    when surrounded by digits or whitespace.
    """
    common_fixes = {
        "m g": "mg",
        "k g": "kg",
        "m l": "ml",
        "m m": "mm",
        "c m": "cm",
        "k P a": "kPa",
        "m m H g": "mmHg",
    }

    for broken, fixed in common_fixes.items():
        # Only replace if surrounded by appropriate context (numbers or Arabic)
        text = re.sub(
            rf"(?<=\d|\s){re.escape(broken)}(?=\d|\s|$)",
            fixed,
            text,
        )

    return text


def _fix_number_ordering(text: str) -> str:
    """Fix number ordering in Arabic text context.

    In Arabic, numbers should read left-to-right even in RTL text.
    OCR sometimes reverses digit order in Arabic context.

    Currently a no-op placeholder that preserves digit sequences as-is.
    Extend with heuristic reversal logic if needed.
    """
    def fix_digit_sequence(match):
        digits = match.group(0)
        # For simple numbers, no change needed
        return digits

    return re.sub(r"\d[\d.,]+\d", fix_digit_sequence, text)
