# دليل التعامل مع النصوص من اليمين لليسار (RTL)

## نظرة عامة

دليل تقني مفصل للتعامل مع النصوص العربية RTL في جميع مراحل المعالجة.

## 1. اكتشاف اتجاه النص

```python
import arabic_reshaper
from bidi.algorithm import get_display

def is_rtl(text):
    """Check if text is primarily RTL."""
    rtl_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    ltr_chars = sum(1 for c in text if 'A' <= c <= 'Z' or 'a' <= c <= 'z')
    return rtl_chars > ltr_chars
```

## 2. إعادة تشكيل النص العربي

```python
# إعادة التشكيل للعرض الصحيح (RTL visual ordering)
reshaped = arabic_reshaper.reshape("بسم الله الرحمن الرحيم")
bidi_text = get_display(reshaped)
```

## 3. التصدير مع الحفاظ على RTL

```python
# DOCX مع RTL
from docx import Document
from docx.shared import Pt

doc = Document()
para = doc.add_paragraph()
para.alignment = 2  # RIGHT (RTL)
run = para.add_run("بسم الله الرحمن الرحيم")
run.font.size = Pt(14)
```

## 4. HTML مع RTL

```html
<div dir="rtl" lang="ar" style="text-align: right; font-family: 'Noto Naskh Arabic', sans-serif;">
    بسم الله الرحمن الرحيم
</div>
```
