"""
OmniFile AI Processor — Arabic RTL (Right-to-Left) Text Processing
===================================================================
Merged from arabic-ocr-pro and advanced-ocr.

Provides comprehensive utilities for:
- RTL text detection and direction analysis (arabic-ocr-pro)
- Arabic presentation form normalization — 40+ character mappings (advanced-ocr)
- Arabic reshaping + BiDi algorithm integration via arabic_reshaper/python-bidi (arabic-ocr-pro)
- Mixed Arabic/English bidirectional text with LRM markers (arabic-ocr-pro)
- Block-level RTL sorting for correct reading order (arabic-ocr-pro + advanced-ocr)
- Bounding-box reordering for raw dict/bbox data (advanced-ocr)
- Line-level reading order fixes for OCR output (advanced-ocr)

CRITICAL PROBLEM SOLVED:
OCR engines return blocks sorted by coordinates: top→bottom, left→right.
This is CORRECT for LTR languages but WRONG for Arabic, where reading
order is: top→bottom, RIGHT→LEFT within each line.

Without this fix, a sentence like "مرحبا بالعالم" would be read as
"بالعالم مرحبا" — the words are reversed within each line.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Arabic / Hebrew Unicode ranges
# ---------------------------------------------------------------------------
ARABIC_RANGES = [
    (0x0600, 0x06FF),   # Arabic block
    (0x0750, 0x077F),   # Arabic Supplement
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
]

HEBREW_RANGE = (0x0590, 0x05FF)

# Tolerance for considering blocks on the same visual line (pixels)
LINE_HEIGHT_TOLERANCE = 20

# ---------------------------------------------------------------------------
# Arabic Presentation-Form Normalization Table (40+ mappings)
# ---------------------------------------------------------------------------
# Maps isolated/initial/medial/final presentation forms back to their
# canonical Unicode code-points so OCR output is consistent.
ARABIC_NORMALIZATION_MAP = {
    # Alef variants
    "\uFE81": "\u0622", "\uFE82": "\u0622",  # Alef with Madda
    "\uFE83": "\u0623", "\uFE84": "\u0623",  # Alef with Hamza above
    "\uFE85": "\u0624", "\uFE86": "\u0624",  # Waw with Hamza
    "\uFE87": "\u0625", "\uFE88": "\u0625",  # Alef with Hamza below
    "\uFE89": "\u0626", "\uFE8A": "\u0626",  # Yeh with Hamza
    "\uFE8B": "\u0626", "\uFE8C": "\u0626",
    # Alef
    "\uFE8D": "\u0627", "\uFE8E": "\u0627",
    # Ba
    "\uFE8F": "\u0628", "\uFE90": "\u0628", "\uFE91": "\u0628", "\uFE92": "\u0628",
    # Ta
    "\uFE93": "\u062A", "\uFE94": "\u062A", "\uFE95": "\u062A", "\uFE96": "\u062A",
    # Tha
    "\uFE97": "\u062B", "\uFE98": "\u062B", "\uFE99": "\u062B", "\uFE9A": "\u062B",
    # Jim
    "\uFE9B": "\u062C", "\uFE9C": "\u062C", "\uFE9D": "\u062C", "\uFE9E": "\u062C",
    # Haa (breathy)
    "\uFE9F": "\u062D", "\uFEA0": "\u062D", "\uFEA1": "\u062D", "\uFEA2": "\u062D",
    # Khaa
    "\uFEA3": "\u062E", "\uFEA4": "\u062E", "\uFEA5": "\u062E", "\uFEA6": "\u062E",
    # Dal
    "\uFEA7": "\u062F", "\uFEA8": "\u062F",
    # Dhal
    "\uFEA9": "\u0630", "\uFEAA": "\u0630",
    # Raa
    "\uFEAB": "\u0631", "\uFEAC": "\u0631",
    # Zay
    "\uFEAD": "\u0632", "\uFEAE": "\u0632",
    # Seen
    "\uFEAF": "\u0633", "\uFEB0": "\u0633", "\uFEB1": "\u0633", "\uFEB2": "\u0633",
    # Sheen
    "\uFEB3": "\u0634", "\uFEB4": "\u0634", "\uFEB5": "\u0634", "\uFEB6": "\u0634",
    # Sad
    "\uFEB7": "\u0635", "\uFEB8": "\u0635", "\uFEB9": "\u0635", "\uFEBA": "\u0635",
    # Dad
    "\uFEBB": "\u0636", "\uFEBC": "\u0636", "\uFEBD": "\u0636", "\uFEBE": "\u0636",
    # Tah
    "\uFEBF": "\u0637", "\uFEC0": "\u0637", "\uFEC1": "\u0637", "\uFEC2": "\u0637",
    # Zah
    "\uFEC3": "\u0638", "\uFEC4": "\u0638", "\uFEC5": "\u0638", "\uFEC6": "\u0638",
    # Ain
    "\uFEC7": "\u0639", "\uFEC8": "\u0639", "\uFEC9": "\u0639", "\uFECA": "\u0639",
    # Ghain
    "\uFECB": "\u063A", "\uFECC": "\u063A", "\uFECD": "\u063A", "\uFECE": "\u063A",
    # Fa
    "\uFED3": "\u0641", "\uFED4": "\u0641", "\uFED5": "\u0641", "\uFED6": "\u0641",  # removed duplicate \uFECF/FED0
    # Qaf
    "\uFED7": "\u0642", "\uFED8": "\u0642", "\uFED9": "\u0642", "\uFEDA": "\u0642",
    # Kaf
    "\uFEDB": "\u0643", "\uFEDC": "\u0643", "\uFEDD": "\u0643", "\uFEDE": "\u0643",
    # Lam
    "\uFEDF": "\u0644", "\uFEE0": "\u0644", "\uFEE1": "\u0644", "\uFEE2": "\u0644",
    # Meem
    "\uFEE3": "\u0645", "\uFEE4": "\u0645", "\uFEE5": "\u0645", "\uFEE6": "\u0645",
    # Noon
    "\uFEE7": "\u0646", "\uFEE8": "\u0646", "\uFEE9": "\u0646", "\uFEEA": "\u0646",
    # Ha
    "\uFEEB": "\u0647", "\uFEEC": "\u0647", "\uFEED": "\u0647", "\uFEEE": "\u0647",
    # Waw
    "\uFEEF": "\u0648", "\uFEF0": "\u0648",
    # Ya
    "\uFEF1": "\u064A", "\uFEF2": "\u064A", "\uFEF3": "\u064A", "\uFEF4": "\u064A",
    # Lam-Alef ligatures
    "\uFEF5": "\u0644\u0627", "\uFEF6": "\u0644\u0627",
    "\uFEF7": "\u0644\u0622", "\uFEF8": "\u0644\u0622",
    "\uFEF9": "\u0644\u0625", "\uFEFA": "\u0644\u0625",
    "\uFEFB": "\u0644\u0623", "\uFEFC": "\u0644\u0623",
}

# Extra OCR-specific normalisation (additional forms sometimes emitted by OCR)
EXTRA_OCR_NORMALIZATION = {
    # Normalize Alef variants
    "\uFE81": "\u0622", "\uFE8D": "\u0627", "\uFE8E": "\u0627", "\u0627": "\u0627",
    # Normalize Waw
    "\uFEF0": "\u0648", "\uFEEF": "\u0648", "\u0648": "\u0648",
    # Normalize Ya
    "\uFEF1": "\u064A", "\uFEF2": "\u064A", "\uFEF3": "\u064A", "\uFEF4": "\u064A",
    # Normalize Lam-Alef
    "\uFEF5": "\u0644\u0627", "\uFEF6": "\u0644\u0627",
    "\uFEF7": "\u0644\u0622", "\uFEF8": "\u0644\u0622",
    "\uFEF9": "\u0644\u0625", "\uFEFA": "\u0644\u0625",
    "\uFEFB": "\u0644\u0623", "\uFEFC": "\u0644\u0623",
    # Ta-Marbuta
    "\uFE93": "\u062A", "\uFE94": "\u0629", "\uFE95": "\u062A", "\uFE96": "\u0629",
    # Kaf
    "\uFEDB": "\u0643", "\uFEDC": "\u0643", "\uFEDD": "\u0643", "\uFEDE": "\u0643",
    # Ba
    "\uFE8F": "\u0628", "\uFE90": "\u0628", "\uFE91": "\u0628", "\uFE92": "\u0628",
    # Mim
    "\uFEE3": "\u0645", "\uFEE4": "\u0645", "\uFEE5": "\u0645", "\uFEE6": "\u0645",
    # Nun
    "\uFEE7": "\u0646", "\uFEE8": "\u0646", "\uFEE9": "\u0646", "\uFEEA": "\u0646",
    # Ha
    "\uFEEB": "\u0647", "\uFEEC": "\u0647", "\uFEED": "\u0647", "\uFEEE": "\u0647",
    # Taa
    "\uFED3": "\u062A", "\uFED4": "\u062A", "\uFED5": "\u062A", "\uFED6": "\u062A",
    # Ain
    "\uFEC7": "\u0639", "\uFEC8": "\u0639", "\uFEC9": "\u0639", "\uFECA": "\u0639",
    # Ghain
    "\uFECB": "\u063A", "\uFECC": "\u063A", "\uFECD": "\u063A", "\uFECE": "\u063A",
    # Sad
    "\uFEB7": "\u0635", "\uFEB8": "\u0635", "\uFEB9": "\u0635", "\uFEBA": "\u0635",
    # Dad
    "\uFEBB": "\u0636", "\uFEBC": "\u0636", "\uFEBD": "\u0636", "\uFEBE": "\u0636",
    # Sin
    "\uFEAF": "\u0633", "\uFEB0": "\u0633", "\uFEB1": "\u0633", "\uFEB2": "\u0633",
    # Shin
    "\uFEB3": "\u0634", "\uFEB4": "\u0634", "\uFEB5": "\u0634", "\uFEB6": "\u0634",
    # Fa
    "\uFED3": "\u0641", "\uFED4": "\u0641", "\uFED5": "\u0641", "\uFED6": "\u0641",
    # Qaf
    "\uFED7": "\u0642", "\uFED8": "\u0642", "\uFED9": "\u0642", "\uFEDA": "\u0642",
    # Khaa
    "\uFEA3": "\u062E", "\uFEA4": "\u062E", "\uFEA5": "\u062E", "\uFEA6": "\u062E",
    # Dal
    "\uFEA7": "\u062F", "\uFEA8": "\u062F",
    # Dhal
    "\uFEA9": "\u0630", "\uFEAA": "\u0630",
    # Zaa
    "\uFEAD": "\u0632", "\uFEAE": "\u0632",
    # Raa
    "\uFEAB": "\u0631", "\uFEAC": "\u0631",
    # Lam
    "\uFEDF": "\u0644", "\uFEE0": "\u0644", "\uFEE1": "\u0644", "\uFEE2": "\u0644",
    # Thaa
    "\uFE97": "\u062B", "\uFE98": "\u062B", "\uFE99": "\u062B", "\uFE9A": "\u062B",
    # Jim
    "\uFE9B": "\u062C", "\uFE9C": "\u062C", "\uFE9D": "\u062C", "\uFE9E": "\u062C",
    # Haa (throat)
    "\uFE9F": "\u062D", "\uFEA0": "\u062D", "\uFEA1": "\u062D", "\uFEA2": "\u062D",
}

# ---------------------------------------------------------------------------
# Character classification helpers
# ---------------------------------------------------------------------------

def is_arabic_char(char: str) -> bool:
    """Check if a character is an Arabic letter.

    Covers Arabic block, Arabic Supplement, Arabic Extended-A,
    Arabic Presentation Forms-A, and Arabic Presentation Forms-B.

    Args:
        char: Single character to check.

    Returns:
        True if the character is in an Arabic Unicode range.
    """
    code = ord(char)
    return any(start <= code <= end for start, end in ARABIC_RANGES)


def is_hebrew_char(char: str) -> bool:
    """Check if a character is a Hebrew letter.

    Args:
        char: Single character to check.

    Returns:
        True if the character is in the Hebrew Unicode range.
    """
    code = ord(char)
    return HEBREW_RANGE[0] <= code <= HEBREW_RANGE[1]


def is_rtl_char(char: str) -> bool:
    """Check if a character has RTL directionality.

    Args:
        char: Single character to check.

    Returns:
        True if the character is Arabic or Hebrew.
    """
    return is_arabic_char(char) or is_hebrew_char(char)


# ---------------------------------------------------------------------------
# Text direction analysis
# ---------------------------------------------------------------------------

def is_rtl_text(text: str) -> bool:
    """Determine if a text string is primarily RTL.

    Counts RTL vs LTR characters and returns True if RTL characters
    are more than 30% of the total alphabetic characters.

    Args:
        text: Text string to analyze.

    Returns:
        True if the text is primarily right-to-left.
    """
    if not text:
        return False

    rtl_count = 0
    ltr_count = 0

    for char in text:
        if is_rtl_char(char):
            rtl_count += 1
        elif char.isalpha():
            ltr_count += 1

    total = rtl_count + ltr_count
    if total == 0:
        return False

    return (rtl_count / total) > 0.3


def get_text_direction(text: str) -> str:
    """Determine the dominant text direction.

    Args:
        text: Text string to analyze.

    Returns:
        'rtl' for right-to-left, 'ltr' for left-to-right,
        or 'mixed' for bidirectional text.
    """
    if not text:
        return "ltr"

    rtl_count = 0
    ltr_count = 0

    for char in text:
        if is_rtl_char(char):
            rtl_count += 1
        elif char.isalpha():
            ltr_count += 1

    total = rtl_count + ltr_count
    if total == 0:
        return "ltr"

    rtl_ratio = rtl_count / total
    ltr_ratio = ltr_count / total

    if rtl_ratio > 0.7:
        return "rtl"
    elif ltr_ratio > 0.7:
        return "ltr"
    else:
        return "mixed"


# ---------------------------------------------------------------------------
# Arabic presentation-form normalization
# ---------------------------------------------------------------------------

def normalize_arabic_presentation_forms(text: str) -> str:
    """Normalize Arabic presentation forms to canonical characters.

    Converts isolated/initial/medial/final presentation forms back to
    their base Unicode code-points using the 40+ mapping table.

    Args:
        text: Text potentially containing Arabic presentation forms.

    Returns:
        Text with all presentation forms normalized.
    """
    if not text:
        return text
    for old, new in ARABIC_NORMALIZATION_MAP.items():
        text = text.replace(old, new)
    return text


def normalize_arabic_ocr(text: str) -> str:
    """Apply OCR-specific Arabic normalization.

    Includes presentation-form normalization plus common OCR-specific
    character fixes (duplicate/redundant mappings are handled by the
    replacement order).

    Args:
        text: Raw OCR text output.

    Returns:
        Normalized text.
    """
    if not text:
        return text
    # First pass: presentation forms
    text = normalize_arabic_presentation_forms(text)
    # Second pass: extra OCR-specific fixes
    for old, new in EXTRA_OCR_NORMALIZATION.items():
        text = text.replace(old, new)
    # Normalize Arabic diacritics (tashkeel) — keep them but standardize
    return text.strip()


# ---------------------------------------------------------------------------
# Text segmentation and direction-based splitting
# ---------------------------------------------------------------------------

def _segment_by_direction(text: str) -> list[dict]:
    """Segment text into Arabic and non-Arabic runs.

    Arabic Unicode ranges checked:
    - 0x0600-0x06FF: Arabic
    - 0x0750-0x077F: Arabic Supplement
    - 0x08A0-0x08FF: Arabic Extended-A
    - 0xFB50-0xFDFF: Arabic Presentation Forms-A
    - 0xFE70-0xFEFF: Arabic Presentation Forms-B

    Args:
        text: Input text.

    Returns:
        List of dicts with 'text' and 'is_arabic' keys.
    """
    segments = []
    current = ""
    is_current_arabic = None

    for char in text:
        is_arabic = is_arabic_char(char)
        is_punctuation = char in ".,;:!?()-\u2014\u2013'\u201c\u201d\" "

        if is_current_arabic is None:
            is_current_arabic = is_arabic
            current = char
        elif is_arabic == is_current_arabic or is_punctuation:
            current += char
        else:
            if current.strip():
                segments.append({
                    "text": current,
                    "is_arabic": is_current_arabic,
                })
            current = char
            is_current_arabic = is_arabic

    if current.strip():
        segments.append({
            "text": current,
            "is_arabic": is_current_arabic,
        })

    return segments


def _split_directional_runs(text: str) -> list[tuple[str, str]]:
    """Split text into runs of consistent text direction.

    Args:
        text: Input text.

    Returns:
        List of (text_segment, direction) tuples.
    """
    if not text:
        return []

    runs: list[tuple[str, str]] = []
    current_run = ""
    current_dir = None

    for char in text:
        char_dir = "rtl" if is_rtl_char(char) else ("ltr" if char.isalpha() else "neutral")

        if current_dir is None:
            current_dir = char_dir
            current_run = char
        elif char_dir == current_dir or char_dir == "neutral":
            current_run += char
        else:
            if current_run:
                runs.append((current_run, current_dir))
            current_run = char
            current_dir = char_dir

    if current_run:
        runs.append((current_run, current_dir))

    return runs


# ---------------------------------------------------------------------------
# RTL display fixing
# ---------------------------------------------------------------------------

def fix_rtl_display(text: str) -> str:
    """Fix RTL text display issues in OCR output.

    Handles common OCR problems with Arabic:
    1. Reversed word order within lines
    2. Disconnected Arabic characters
    3. Mixed Arabic/Latin character ordering

    Args:
        text: Raw OCR text output.

    Returns:
        Text with corrected RTL display.
    """
    if not text or not text.strip():
        return text

    # Normalize presentation forms first
    text = normalize_arabic_presentation_forms(text)

    # Split into segments: Arabic runs and non-Arabic runs
    segments = _segment_by_direction(text)

    if not segments:
        return text

    # Process each segment
    fixed_segments = []
    for segment in segments:
        if segment["is_arabic"]:
            fixed_segments.append(normalize_arabic_ocr(segment["text"]))
        else:
            fixed_segments.append(segment["text"])

    return "".join(fixed_segments)


# ---------------------------------------------------------------------------
# Line / block reordering for RTL reading order
# ---------------------------------------------------------------------------

def fix_arabic_reading_order(
    lines: list,
    tolerance: int = LINE_HEIGHT_TOLERANCE,
) -> list:
    """Reorder lines/blocks for correct Arabic reading order.

    Works with any object that has a ``bbox`` attribute with ``x`` and ``y``
    properties (e.g., ``LineResult``, ``DocumentBlock``, or a simple
    ``types.SimpleNamespace``).

    Sorts blocks:
    1. Top to bottom (by Y coordinate)
    2. Within each line: Right to Left (by X coordinate, REVERSED)

    Args:
        lines: List of objects with ``bbox.x`` and ``bbox.y`` attributes.
        tolerance: Pixel tolerance for grouping lines into visual rows.

    Returns:
        Reordered list of line objects.
    """
    if not lines:
        return []

    # Step 1: Sort all lines by Y coordinate (top to bottom)
    sorted_lines = sorted(lines, key=lambda l: l.bbox.y)

    # Step 2: Group lines into visual rows (same Y ± tolerance)
    row_groups: list[list] = []
    current_row = [sorted_lines[0]]

    for line in sorted_lines[1:]:
        ref_y = current_row[0].bbox.y
        if abs(line.bbox.y - ref_y) < tolerance:
            current_row.append(line)
        else:
            row_groups.append(current_row)
            current_row = [line]

    if current_row:
        row_groups.append(current_row)

    # Step 3: Within each row, sort RIGHT to LEFT for Arabic
    reordered = []
    for row in row_groups:
        row_sorted = sorted(row, key=lambda l: -l.bbox.x)

        # Set reading order metadata if supported
        for idx, line in enumerate(row_sorted):
            if hasattr(line, "metadata"):
                line.metadata = getattr(line, "metadata", {})
                line.metadata["reading_order"] = idx

        reordered.extend(row_sorted)

    logger.debug(f"Reordered {len(lines)} lines into {len(row_groups)} rows (RTL)")
    return reordered


def reorder_bboxes_for_rtl(
    blocks: list[dict],
    tolerance: int = LINE_HEIGHT_TOLERANCE,
) -> list[dict]:
    """Reorder bounding boxes for correct Arabic reading order.

    Same logic as ``fix_arabic_reading_order`` but works with raw
    ``dict``/bbox data.  Useful when you have bbox data from a
    different source (e.g., raw JSON).

    Args:
        blocks: List of dicts with ``"bbox"`` ``(x1, y1, x2, y2)`` and
                ``"text"`` keys.
        tolerance: Pixel tolerance for line grouping.

    Returns:
        Reordered list of blocks.
    """
    if not blocks:
        return []

    # Sort by Y
    sorted_blocks = sorted(blocks, key=lambda b: b["bbox"][1])

    # Group into rows
    rows = []
    current_row = [sorted_blocks[0]]

    for block in sorted_blocks[1:]:
        ref_y = current_row[0]["bbox"][1]
        if abs(block["bbox"][1] - ref_y) < tolerance:
            current_row.append(block)
        else:
            rows.append(current_row)
            current_row = [block]

    if current_row:
        rows.append(current_row)

    # Reverse X within each row
    reordered = []
    for row in rows:
        row_sorted = sorted(row, key=lambda b: -b["bbox"][0])
        reordered.extend(row_sorted)

    return reordered


# ---------------------------------------------------------------------------
# RTLFixer — high-level class (arabic-ocr-pro)
# ---------------------------------------------------------------------------

class RTLFixer:
    """Fixes Arabic RTL text ordering issues in OCR output.

    Handles common RTL-related problems:
    - Reversed word order within lines
    - Incorrect mixing of Arabic and English text
    - Broken Arabic letter connections
    - Incorrect paragraph direction

    Integrates **arabic_reshaper** and **python-bidi** when available
    for proper letter-connection and visual-order rendering.
    """

    def __init__(self) -> None:
        """Initialize the RTL fixer."""
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display  # noqa: F401
            self._has_reshaper = True
            self._has_bidi = True
        except ImportError:
            self._has_reshaper = False
            self._has_bidi = False
            logger.warning(
                "arabic_reshaper or python-bidi not installed. "
                "Install for better RTL support: pip install arabic_reshaper python-bidi"
            )

    # ---- public API ----

    def fix_text(self, text: str) -> str:
        """Fix RTL text ordering.

        Applies presentation-form normalization, Arabic reshaping,
        and BiDi algorithm (if available).

        Args:
            text: Input text that may have RTL ordering issues.

        Returns:
            Text with correct visual ordering.
        """
        if not text.strip():
            return text

        direction = get_text_direction(text)
        if direction == "ltr":
            return text

        # Normalize presentation forms
        text = normalize_arabic_presentation_forms(text)

        # Apply Arabic reshaping to fix letter connections
        if self._has_reshaper:
            try:
                import arabic_reshaper
                reshaped = arabic_reshaper.reshape(text)
            except Exception:
                reshaped = text
        else:
            reshaped = text

        # Apply BiDi algorithm for correct visual ordering
        if self._has_bidi:
            try:
                from bidi.algorithm import get_display
                return get_display(reshaped)
            except Exception:
                return reshaped

        return reshaped

    def fix_line_order(self, lines: list[str]) -> list[str]:
        """Fix the reading order of text lines for RTL documents.

        For fully RTL documents, applies text-level fixes to each line
        while preserving top-to-bottom visual order.

        Args:
            lines: List of text lines in document order.

        Returns:
            Lines with correct RTL text within each line.
        """
        if not lines:
            return lines

        full_text = " ".join(lines)
        if not is_rtl_text(full_text):
            return lines

        return [self.fix_text(line) for line in lines]

    def sort_blocks_rtl(self, blocks: list, y_tolerance: int = 20) -> list:
        """Sort document blocks in RTL reading order.

        RTL documents are read right-to-left, so blocks on the same
        line should be sorted by decreasing x-coordinate.

        Works with any object that exposes ``bbox.x``, ``bbox.y``,
        and ``get_text()``.

        Args:
            blocks: List of document blocks with bounding boxes.
            y_tolerance: Maximum vertical distance to consider same row.

        Returns:
            Blocks sorted in RTL reading order.
        """
        if not blocks:
            return blocks

        rows = self._group_blocks_by_row(blocks, y_tolerance)

        sorted_blocks: list = []
        for row_blocks in sorted(
            rows,
            key=lambda r: r[0].bbox.y if hasattr(r[0], "bbox") and r[0].bbox else 0,
        ):
            row_text = " ".join(
                b.get_text() if hasattr(b, "get_text") else str(b)
                for b in row_blocks
            )
            if is_rtl_text(row_text):
                row_blocks.sort(
                    key=lambda b: b.bbox.x if hasattr(b, "bbox") and b.bbox else 0,
                    reverse=True,
                )
            else:
                row_blocks.sort(
                    key=lambda b: b.bbox.x if hasattr(b, "bbox") and b.bbox else 0,
                )
            sorted_blocks.extend(row_blocks)

        return sorted_blocks

    def fix_mixed_text(self, text: str) -> str:
        """Handle mixed Arabic/English (bidirectional) text.

        Separates Arabic and English segments and applies proper
        ordering based on the base direction.  Wraps English runs
        with LRM (Left-to-Right Mark) markers inside RTL context.

        Args:
            text: Mixed Arabic/English text.

        Returns:
            Text with proper bidirectional ordering.
        """
        direction = get_text_direction(text)
        if direction == "ltr":
            return text

        runs = _split_directional_runs(text)
        if len(runs) <= 1:
            return text

        if direction == "rtl":
            fixed_runs: list[str] = []
            for run_text, run_dir in runs:
                if run_dir == "ltr" and len(run_text.strip()) > 1:
                    # Keep English words in original order but mark them
                    fixed_runs.append(f"\u200e{run_text}\u200e")  # LRM markers
                else:
                    fixed_runs.append(run_text)
            return "".join(fixed_runs)

        return text

    # ---- helpers ----

    @staticmethod
    def _group_blocks_by_row(
        blocks: list,
        y_tolerance: int = 20,
    ) -> list[list]:
        """Group blocks into rows based on vertical position.

        Args:
            blocks: Objects with ``bbox`` having ``y`` attribute.
            y_tolerance: Maximum vertical distance to consider same row.

        Returns:
            List of rows, each containing blocks in that row.
        """
        if not blocks:
            return []

        sortable = [
            b for b in blocks
            if hasattr(b, "bbox") and b.bbox is not None
        ]
        if not sortable:
            return [blocks]

        sorted_blocks = sorted(sortable, key=lambda b: b.bbox.y)

        rows: list[list] = [[sorted_blocks[0]]]

        for block in sorted_blocks[1:]:
            if not (hasattr(block, "bbox") and block.bbox is not None):
                continue

            row_y = sum(b.bbox.y for b in rows[-1]) / len(rows[-1])

            if abs(block.bbox.y - row_y) <= y_tolerance:
                rows[-1].append(block)
            else:
                rows.append([block])

        return rows
