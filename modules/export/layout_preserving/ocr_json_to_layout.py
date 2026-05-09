"""
modules/export/layout_preserving/ocr_json_to_layout.py
تحويل مخرجات OCR JSON إلى HTML/PDF يحافظ على التخطيط — OmniFile v5.0
"""


def layout_to_html(layout_data: dict, output_html: str) -> str:
    """تحويل layout_data إلى HTML يحافظ على مواضع الكتل الأصلية."""
    pages = layout_data.get("pages", [])
    html_parts = [
        '<html><head><meta charset="UTF-8"><style>',
        'body { font-family: Arial, sans-serif; margin: 0; }',
        '.page { margin: 20px auto; border: 1px solid #ccc; position: relative; background: white; }',
        'table { border-collapse: collapse; width: auto; }',
        'td { border: 1px solid black; padding: 5px; }',
        'img { max-width: 100%; }',
        '</style></head><body>',
    ]

    for page in pages:
        pw = page.get("width", 800)
        ph = page.get("height", 1100)
        html_parts.append(
            f'<div class="page" style="width:{pw}px; height:{ph}px;">'
        )
        for block in page.get("blocks", []):
            b_type = block.get("type", "paragraph")
            bbox   = block.get("bbox", [0, 0, 1, 1])
            left   = bbox[0] * pw
            top    = bbox[1] * ph
            width  = (bbox[2] - bbox[0]) * pw
            height = (bbox[3] - bbox[1]) * ph
            style  = (
                f"position:absolute; left:{left:.1f}px; top:{top:.1f}px;"
                f" width:{width:.1f}px; height:{height:.1f}px; overflow:hidden;"
            )
            if b_type in ("paragraph", "header", "footer", "caption"):
                d = 'dir="rtl"' if block.get("direction") == "rtl" else 'dir="ltr"'
                html_parts.append(f'<div style="{style}" {d}>{block.get("text","")}</div>')
            elif b_type == "table":
                html_parts.append(f'<div style="{style}"><table>')
                rows: dict = {}
                for cell in block.get("structure", {}).get("cells", []):
                    r, c = cell.get("row", 0), cell.get("col", 0)
                    rows.setdefault(r, {})[c] = cell.get("text", "")
                for r in sorted(rows):
                    html_parts.append("<tr>")
                    for c in sorted(rows[r]):
                        html_parts.append(f"<td>{rows[r][c]}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</table></div>")
            elif b_type == "image":
                src = block.get("image_file", "")
                html_parts.append(
                    f'<div style="{style}">'
                    f'<img src="{src}" style="width:100%;height:100%;object-fit:contain;">'
                    f'</div>'
                )
        html_parts.append("</div>")

    html_parts.append("</body></html>")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))
    return output_html


def layout_to_pdf(layout_data: dict, output_pdf: str) -> str:
    """تحويل layout_data إلى PDF عبر WeasyPrint (pip install weasyprint)."""
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".html")
    try:
        layout_to_html(layout_data, tmp)
        from weasyprint import HTML
        HTML(tmp).write_pdf(output_pdf)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return output_pdf
