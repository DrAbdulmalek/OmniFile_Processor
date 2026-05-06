### دالة تصدير HTML محسّنة
```python
def layout_to_html(layout_data, output_html):
    pages = layout_data.get("pages", [])
    html_parts = ['<html><head><meta charset="UTF-8"><style>',
                  'body { font-family: "Arial", sans-serif; }',
                  '.page { margin-bottom: 20px; padding: 20px; border:1px solid #ccc; position:relative; }',
                  'table { border-collapse: collapse; width: auto; }',
                  'td { border: 1px solid black; padding: 5px; }',
                  'img { max-width: 100%; }',
                  '</style></head><body>']
    for page in pages:
        html_parts.append(f'<div class="page" style="width:{page["width"]}px;height:{page["height"]}px;">')
        for block in page["blocks"]:
            b_type = block["type"]
            # تحويل الإحداثيات النسبية إلى موضع مطلق
            left = block["bbox"][0] * page["width"]
            top = block["bbox"][1] * page["height"]
            width = (block["bbox"][2] - block["bbox"][0]) * page["width"]
            height = (block["bbox"][3] - block["bbox"][1]) * page["height"]
            style = f"position:absolute; left:{left}px; top:{top}px; width:{width}px; height:{height}px; overflow:hidden;"
            if b_type == "paragraph":
                dir_attr = 'dir="rtl"' if block.get("direction") == "rtl" else 'dir="ltr"'
                html_parts.append(f'<div style="{style}" {dir_attr}>{block["text"]}</div>')
            elif b_type == "table":
                # بناء جدول
                html_parts.append(f'<div style="{style}"><table>')
                # استخدم structure.cells
                rows = {}
                for cell in block.get("structure", {}).get("cells", []):
                    r, c = cell["row"], cell["col"]
                    rows.setdefault(r, {})[c] = cell["text"]
                for r in sorted(rows.keys()):
                    html_parts.append("<tr>")
                    for c in sorted(rows[r].keys()):
                        html_parts.append(f"<td>{rows[r][c]}</td>")
                    html_parts.append("</tr>")
                html_parts.append("</table></div>")
            elif b_type == "image":
                img_src = block.get("image_file", "")
                html_parts.append(f'<div style="{style}"><img src="{img_src}" style="width:100%;height:100%;object-fit:contain;"></div>')
                if "caption" in block:
                    cap = block["caption"]
                    cap_style = f"position:absolute; left:{cap['bbox'][0]*page['width']}px; top:{cap['bbox'][1]*page['height']}px; width:{(cap['bbox'][2]-cap['bbox'][0])*page['width']}px;"
                    html_parts.append(f'<div style="{cap_style}"><em>{cap["text"]}</em></div>')
        html_parts.append("</div>")
    html_parts.append("</body></html>")
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write("\n".join(html_parts))
```

هذا الإخراج سيضع النص والصور والجداول **في نفس مواقعها الأصلية** على الصفحة، وكأنها أعيدت كتابتها.

### تحويل HTML إلى PDF باستخدام WeasyPrint (داخل Colab)
```python
!pip install -q weasyprint
from weasyprint import HTML
HTML('output_layout.html').write_pdf('output_mimic.pdf')
```

---

