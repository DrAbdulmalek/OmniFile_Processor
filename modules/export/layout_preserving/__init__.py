"""
تصدير مع الحفاظ على التنسيق (RTL + Layout)
Layout-Preserving Export for RTL Documents

واجهة توافق موحدة تجمع بين:
- دوال التصدير المباشر من layout_data
- دوال التحويل من OCR JSON إلى layout_data
- كلاس بسيط للاستخدام من الـ API الخلفي
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .layout_preserving_v2 import export_to_docx as _raw_export_to_docx


def export_to_docx(layout_data: dict[str, Any], output_path: str) -> str:
    """تصدير layout_data إلى DOCX مع الحفاظ على RTL والتخطيط الأساسي."""
    _raw_export_to_docx(layout_data, output_path)
    return output_path


def ocr_result_to_layout(ocr_json: dict[str, Any], image_path: str = "") -> dict[str, Any]:
    """تحويل مخرجات OCR البسيطة إلى تنسيق layout_data موحّد."""
    layout = {"image_path": image_path, "blocks": []}
    for block in ocr_json.get("blocks", []):
        normalized = {
            "type": block.get("type", "paragraph"),
            "bbox": block.get("bbox", [0, 0, 1, 1]),
            "text": block.get("text", ""),
        }
        if normalized["type"] == "table":
            normalized["cells"] = block.get("cells", [])
        elif normalized["type"] == "image":
            normalized["image_file"] = block.get("image_file", "")
        layout["blocks"].append(normalized)
    return layout


def _read_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def layout_to_docx(layout_json_path: str, output_docx: str) -> str:
    """قراءة JSON ثم تصديره إلى DOCX عبر واجهة layout_data الموحدة."""
    data = _read_json(layout_json_path)
    if "pages" in data and not data.get("blocks"):
        merged_blocks: list[dict[str, Any]] = []
        for page in data.get("pages", []):
            merged_blocks.extend(page.get("blocks", []))
        data = {"image_path": data.get("image_path", ""), "blocks": merged_blocks}
    return export_to_docx(data, output_docx)


def _write_html(layout_data: dict[str, Any], output_path: str) -> str:
    blocks_html: list[str] = []
    for block in layout_data.get("blocks", []):
        btype = block.get("type", "paragraph")
        if btype == "table":
            rows = []
            for row in block.get("cells", []):
                cells = "".join(f"<td>{str(cell)}</td>" for cell in row)
                rows.append(f"<tr>{cells}</tr>")
            blocks_html.append(f"<table dir='rtl'>{''.join(rows)}</table>")
        elif btype == "header":
            blocks_html.append(f"<h2 dir='rtl'>{block.get('text', '')}</h2>")
        elif btype == "caption":
            blocks_html.append(f"<p dir='rtl'><em>{block.get('text', '')}</em></p>")
        elif btype == "image" and block.get("image_file"):
            blocks_html.append(f"<img src='{block['image_file']}' style='max-width:100%;' />")
        else:
            blocks_html.append(f"<p dir='rtl'>{block.get('text', '')}</p>")

    html = """<html><head><meta charset='UTF-8'>
<style>
body { font-family: Arial, sans-serif; margin: 2rem; }
table { border-collapse: collapse; margin: 1rem 0; }
td, th { border: 1px solid #888; padding: 6px 10px; }
</style></head><body>{}</body></html>""".format("\n".join(blocks_html))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


class LayoutPreservingExporter:
    """واجهة مبسطة تُستخدم من FastAPI للتصدير من ملفات OCR JSON."""

    def export_to_docx(self, layout_json_path: str, output_path: str | None = None) -> str:
        output = output_path or str(Path(layout_json_path).with_suffix(".docx"))
        return layout_to_docx(layout_json_path, output)

    def export_to_html(self, layout_json_path: str, output_path: str | None = None) -> str:
        data = _read_json(layout_json_path)
        output = output_path or str(Path(layout_json_path).with_suffix(".html"))
        if "pages" in data and not data.get("blocks"):
            merged_blocks: list[dict[str, Any]] = []
            for page in data.get("pages", []):
                merged_blocks.extend(page.get("blocks", []))
            data = {"image_path": data.get("image_path", ""), "blocks": merged_blocks}
        return _write_html(data, output)


__all__ = [
    "LayoutPreservingExporter",
    "export_to_docx",
    "layout_to_docx",
    "ocr_result_to_layout",
]
