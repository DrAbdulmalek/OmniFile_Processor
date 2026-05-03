# Changelog — OmniFile AI Processor

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

---

## [4.1.1] — 2026-05-03

### Fixed
- **NLP optional imports**: جعل تحميل `AICorrector` و `python-dotenv` اختيارياً حتى لا يفشل التثبيت الخفيف أو اختبارات CI الأساسية.
- **Direction detection**: تحسين اكتشاف اتجاه النص المختلط في `modules/vision/text_reconstructor.py` ليعتمد على غلبة الحروف العربية مقابل اللاتينية بدلاً من عتبة منخفضة كانت تسبب تصنيفاً خاطئاً.
- **Arabic normalization tests**: تصحيح اختبار `_normalize_arabic(None)` ليعكس السلوك المقصود فعلياً.
- **Evaluation grading boundary**: تعديل حد CER بحيث تمثل نسبة `10%` بداية مستوى `C (Acceptable)`.

### Added
- **`requirements-colab.txt`**: ملف متطلبات مخصص لدفاتر Google Colab والدفاتر التفاعلية.

---

## [4.1.0] — 2025-05-03

### Added
- **Layout Preservation System**: تصدير DOCX مع الحفاظ على البنية البصرية (جداول، عناوين، تسميات، صور)
  - `modules/export/layout_preserving.py` — دالة `export_to_docx()` و `ocr_result_to_layout()`
- **Arabic NLP Utils**: أدوات المقارنة الدلالية للنصوص العربية المحسّنة لبيئات OCR
  - `modules/nlp/arabic_nlp_utils.py` — `normalize_for_comparison()`, `arabic_normalized_similarity()`, `similarity_report()`
- **Mobile Review Server**: خادم Flask لمراجعة نتائج OCR من الجوال
  - `mobile_review/server.py` — واجهة REST API مع دعم ngrok
  - `mobile_review/templates/review.html` — واجهة متجاوبة RTL للتصحيح اللمسي
- **GitHub Actions CI/CD**: سير عمل تلقائي لاختبارات pytest على كل commit و PR
- **Layered Requirements**: تقسيم `requirements.txt` إلى 4 طبقات:
  - `requirements-core.txt` — الحد الأدنى للتشغيل (~1.5 GB)
  - `requirements-ocr.txt` — محركات OCR (~3 GB إضافية)
  - `requirements-nlp.txt` — معالجة اللغة (~2 GB إضافية)
  - `requirements-full.txt` — كل المكونات (~6-8 GB)

### Changed
- تحديث `SUGGESTIONS.md` بتوثيق ميزات Layout Preservation و Mobile Review

### Architecture Notes
- `mobile/` يحتوي على PWA بسيط (HTML ثابت) للمراجعة المحلية
- `mobile_review/` يحتوي على خادم Flask كامل مع واجهة REST API
- لا يوجد تداخل وظيفي — كل منهما يخدم سيناريو استخدام مختلف

---

## [4.0.0] — 2025-05-02

### Major Changes — OmniFile AI Processor v4.0 Complete Overhaul

#### Added
- **دعم 6 مشاريع مدمجة** في نظام واحد متكامل:
  - OmniFile_Processor + HandwrittenOCR + handwriting-ocr + arabic-ocr-pro + advanced-ocr + OCR-Enhancer
- **محركات OCR متعددة**: TrOCR + EasyOCR + Tesseract + PaddleOCR
- **نظام Fusion Engine**: دمج ذكي لنتائج محركات OCR متعددة
- **معالجة RTL كاملة**: `modules/nlp/arabic_rtl.py` مع دعم التشكيل والعناوين
- **نظام الأمان**: كشف وحماية البيانات الحساسة باستخدام Presidio
  - `modules/security/sensitive_scanner.py`
- **أنماط مطابقة**: `modules/core/pattern_matcher.py` للكشف عن الأنماط النصية
- **واجهة Gradio**: `hf_app.py` للنشر على HuggingFace Spaces
- **Docker Support**: `Dockerfile` و `docker-compose.yml` للتشغيل في حاويات
- **Kubernetes**: ملفات النشر في `k8s/`
- **13 ملف اختبار** في `tests/` مع fixtures مشتركة

#### Architecture
- `modules/vision/` — رؤية حاسوبية ومعالجة صور
- `modules/nlp/` — معالجة اللغة الطبيعية والترجمة
- `modules/ai/` — تحسين بالذكاء الاصطناعي (GPT/Gemini)
- `modules/security/` — كشف البيانات الحساسة
- `modules/export/` — تصدير لتنسيقات متعددة
- `modules/evaluation/` — تقييم وقياس الأداء
- `modules/core/` — المكونات الأساسية المشتركة

---

## [3.0.0] — 2025-04-XX

### Added
- نظام Streamlit UI الأساسي
- دعم PDF و الصور
- تصدير النتائج (TXT, JSON, Excel, DOCX)
- معالجة مسبقة للصور

---

## [2.0.0] — 2025-03-XX

### Added
- دعم EasyOCR
- الترجمة الأساسية
- تصحيح إملائي

---

## [1.0.0] — 2025-02-XX

### Added
- الإصدار الأول من OmniFile Processor
- دعم Tesseract OCR
- واجهة سطر الأوامر
