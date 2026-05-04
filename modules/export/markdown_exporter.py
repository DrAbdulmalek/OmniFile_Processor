"""
modules/export/markdown_exporter.py
════════════════════════════════════
تصدير نتائج OCR إلى Markdown مع الحفاظ على البنية.
مستوحى من: Docling (IBM) — docling.txt في مجلد الاقتراحات.

يدعم:
  - العناوين (H1, H2, H3) بناءً على حجم النص النسبي
  - الجداول بتنسيق Markdown مع محاذاة RTL
  - تسميات الصور  (caption)
  - القوائم النقطية والرقمية
  - الفقرات مع الحفاظ على الفراغات
"""

import re
from typing import Optional


def blocks_to_markdown(layout_data: dict, rtl: bool = True) -> str:
    """
    تحويل layout_data إلى نص Markdown.

    Args:
        layout_data: dict يحتوي على 'blocks' (نفس تنسيق layout_preserving.py)
        rtl: True = إضافة ماركر RTL للنصوص العربية

    Returns:
        نص Markdown منسّق
    """
    lines = []
    rtl_marker = "\u202b" if rtl else ""  # RIGHT-TO-LEFT EMBEDDING

    for block in layout_data.get("blocks", []):
        btype = block.get("type", "paragraph")
        text  = block.get("text", "").strip()

        if btype == "header":
            lines.append(f"## {rtl_marker}{text}\n")

        elif btype == "paragraph":
            if text:
                lines.append(f"{rtl_marker}{text}\n")

        elif btype == "caption":
            if text:
                lines.append(f"*{rtl_marker}{text}*\n")

        elif btype == "table":
            md_table = _table_to_markdown(block.get("cells", []), rtl_marker)
            if md_table:
                lines.append(md_table + "\n")

        elif btype == "image":
            img = block.get("image_file", "")
            caption = block.get("caption", "")
            if img:
                lines.append(f"\n![{caption}]({img})\n\n")

        elif btype == "list_item":
            prefix = block.get("list_prefix", "-")
            lines.append(f"{prefix} {rtl_marker}{text}\n")

        # فراغ بين الكتل
        lines.append("")

    return "\n".join(lines).strip()


def _table_to_markdown(cells: list[list], rtl_marker: str = "") -> str:
    """تحويل خلايا جدول إلى Markdown table."""
    if not cells:
        return ""

    rows = []
    col_count = max(len(row) for row in cells)

    # صف العنوان
    header = cells[0]
    header_cells = [f"{rtl_marker}{str(c).strip()}" for c in header]
    # تعبئة الخلايا الناقصة
    while len(header_cells) < col_count:
        header_cells.append("")
    rows.append("| " + " | ".join(header_cells) + " |")

    # صف الفاصل (RTL alignment)
    rows.append("| " + " | ".join(["---:"] * col_count) + " |")

    # بقية الصفوف
    for row in cells[1:]:
        cells_fmt = [f"{rtl_marker}{str(c).strip()}" for c in row]
        while len(cells_fmt) < col_count:
            cells_fmt.append("")
        rows.append("| " + " | ".join(cells_fmt) + " |")

    return "\n".join(rows)


def detect_list_items(text: str) -> list[dict]:
    """
    كشف عناصر القوائم العربية والإنجليزية.
    الأنماط المدعومة: •, -, *, 1., أ), a)
    """
    patterns = [
        (r"^[•\-\*○▪▸►]\s+(.+)",   "-"),
        (r"^\d+[\.\)]\s+(.+)",       "1."),
        (r"^[أ-ي][\.\)]\s+(.+)",    "أ)"),
        (r"^[a-z][\.\)]\s+(.+)",     "a)"),
    ]
    items = []
    for line in text.split("\n"):
        line = line.strip()
        for pattern, prefix in patterns:
            m = re.match(pattern, line)
            if m:
                items.append({"type": "list_item", "text": m.group(1), "list_prefix": prefix})
                break
        else:
            if line:
                items.append({"type": "paragraph", "text": line})
    return items


def export_to_markdown(layout_data: dict, output_path: Optional[str] = None,
                       rtl: bool = True) -> str:
    """
    واجهة رئيسية: تصدير layout_data إلى ملف Markdown.

    Args:
        layout_data: dict بنفس تنسيق export_to_docx
        output_path: مسار الملف (اختياري — إذا None يُرجع النص فقط)
        rtl: True للنصوص العربية

    Returns:
        نص Markdown
    """
    md = blocks_to_markdown(layout_data, rtl=rtl)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
    return md
