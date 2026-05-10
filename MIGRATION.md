# دليل الترحيل من `src/` إلى `modules/`

## نظرة عامة

في الإصدار 5.0، قمنا بإعادة هيكلة المشروع لتوحيد الكود في `modules/` بدلاً من التكرار بين `modules/` و `src/`.

## التغييرات الرئيسية

### قبل (v4.x)
```
src/
├── gradio_ui.py          ← الواجهة الرئيسية
├── ocr/
│   ├── handwritten_ocr.py
│   └── image_preprocessor.py
├── nlp/
│   └── text_analyzer.py
└── ...
```

### بعد (v5.0)
```
modules/
├── ui/
│   └── gradio_app.py     ← الواجهة الجديدة (موحدة)
├── vision/
│   ├── ocr_engine.py     ← محرك OCR الموحد
│   ├── htr/              ← HTR المتخصص (جديد!)
│   │   ├── arabic_htr.py
│   │   ├── line_segmenter.py
│   │   └── ...
│   └── image_preprocessor.py
├── nlp/
│   └── text_analyzer.py
└── ...
```

## دليل الترحيل السريع

### للمطورين

```python
# القديم (v4.x)
from src.gradio_ui import OmniFileProcessor
from src.ocr.handwritten_ocr import HandwrittenOCR

# الجديد (v5.0)
from modules.ui.gradio_app import OmniFileProcessor
from modules.vision.htr import ArabicHandwrittenHTR
```

### للمستخدمين

```bash
# القديم
python src/gradio_ui.py

# الجديد
python -m modules.ui.gradio_app
# أو
make run
```

## الجدول الزمني

| الإصدار | الحالة | `src/` | `modules/` |
|---------|--------|--------|------------|
| v4.x | مستقر | ✅ نشط | ✅ نشط (نظري) |
| v5.0 | ترحيل | ⚠️ DEPRECATED | ✅ نشط (عملي) |
| v5.5 | انتقال | ⚠️ DEPRECATED | ✅ الوحيد |
| v6.0 | إزالة | ❌ محذوف | ✅ الوحيد |

## المساعدة

إذا واجهت مشاكل في الترحيل، افتح [Issue](https://github.com/DrAbdulmalek/OmniFile_Processor/issues) مع وسم `migration`.
