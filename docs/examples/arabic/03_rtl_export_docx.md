# تصدير مع الحفاظ على اتجاه النص (RTL)

## نظرة عامة

يوضح هذا المثال كيفية تصدير النصوص العربية مع الحفاظ على اتجاه الكتابة من اليمين لليسار (RTL) في صيغ مختلفة مثل DOCX و PDF و Markdown. يدعم OmniFile الحفاظ على التخطيط الأصلي للمستند بما في ذلك الجداول والعناوين والفقرات.

## المتطلبات

```bash
pip install -r requirements-core.txt -r requirements-ocr.txt
```

## المثال 1: تصدير إلى DOCX مع دعم RTL

```python
from modules.export.layout_preserving import LayoutPreservingExporter

exporter = LayoutPreservingExporter()

# تصدير نتيجة OCR إلى DOCX
exporter.export_to_docx(
    text="بسم الله الرحمن الرحيم\nالحمد لله رب العالمين",
    output_path="output_rtl.docx",
    rtl_support=True,
    font_name="Noto Naskh Arabic",
    font_size=14
)
```

## المثال 2: تصدير مع الحفاظ على التخطيط

```python
from modules.export.layout_preserving import LayoutPreservingExporter
import json

exporter = LayoutPreservingExporter()

# تحميل تخطيط OCR (يُنتج من عملية التعرف)
with open("ocr_layout_result.json") as f:
    layout = json.load(f)

# تصدير مع الحفاظ على الموضع والحجم
exporter.export_preserved_layout(
    layout=layout,
    output_path="output_layout.docx",
    page_width=595,   # A4 عرض بالبكسل عند 72 DPI
    page_height=842,  # A4 ارتفاع
    rtl_default=True
)
```

## المثال 3: تصدير Markdown مع اتجاه عربي

```python
from modules.export.markdown_exporter import MarkdownExporter

exporter = MarkdownExporter()

markdown = exporter.export(
    text="عنوان المستند\nبسم الله الرحمن الرحيم",
    output_path="output.md",
    rtl=True,
    heading_levels=True
)

# الناتج يحتوي على <div dir="rtl"> للعرض الصحيح
```

## المثال 4: تصدير دليل دراسي عربي

```python
from modules.export.study_guide import StudyGuideExporter

exporter = StudyGuideExporter()

exporter.export(
    title="مقدمة في علوم الحاسب",
    content="الوحدة الأولى: أساسيات البرمجة...",
    output_path="study_guide.docx",
    include_flashcards=True,
    rtl=True,
    template="academic"
)
```

## ملاحظات

- الخط الافتراضي هو Noto Naskh Arabic (يُثبَّت تلقائياً)
- دعم كامل لـ A4 و Letter و A3
- الجداول تُصدَّر مع محاذاة خلايا صحيحة
- يمكن تخصيص نوع الخط والحجم لكل عنصر
