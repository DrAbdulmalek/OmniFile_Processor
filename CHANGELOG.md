# Changelog — OmniFile AI Processor

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

---

## [6.0.0] — 2026-05-07

### Major Changes — Merge from OmniFile-Previous-Versions

دمج كامل مع مستودع `OmniFile-Previous-Versions` لاستعادة جميع الميزات المفقودة من الإصدارات السابقة.

### Added
- **نظام تصحيح ترجمات عربية ثنائية اللغة** (modules/nlp/translation_corrector/): 23+ قاعدة تصحيح
- **نظام المزامنة بين الأجهزة** (modules/security/sync/): FileLock + SyncManager + Syncthing
- **مرجع دراسي شامل** (modules/export/study_guide/): Markdown + HTML + Mermaid + Anki Flashcards
- **نظام ترحيل البيانات** (modules/core/migration/): DataMigrator للترحيل من الإصدارات القديمة
- **تصدير مع الحفاظ على التنسيق** (modules/export/layout_preserving/): DOCX/HTML مع RTL
- **أداة تقسيم الكلمات** (tools/streamlit_segmentation_app.py)
- **أدوات مراجعة متقدمة**: double_blind_reviewer, review_dashboard, voting_tracker, quota_manager
- **أدوات تدريب**: data_mixing, decay_tracker, unsloth_pipeline
- **فهرس المشاريع المرجعية** (docs/REFERENCE_PROJECTS.md): 40+ مشروع مرجعي
- **دفاتر Colab محسنة** (notebooks/)
- **نسخ أرشيفية** (legacy/) محفوظة من OmniFile-Previous-Versions

### Changed
- **backend/main.py**: ترقية من v3.0 إلى v6.0 مع إضافة 20+ endpoint جديد
- **__init__.py**: ترقية رقم الإصدار إلى 6.0.0

---

## [4.2.0] — 2026-05-03

### Added — src/ → modules/ Migration
- **modules/core/handwriting_db.py**: ترحيل `HandwritingDB` من `src/database.py` مع توثيق كامل.
- **modules/nlp/reconstruction.py**: ترحيل `reconstruct_sentences` و `reconstruct_sentences_direct` و `extract_bilingual_vocab` و `derive_word_corrections` من `src/reconstruction.py`.
- **modules/nlp/feedback.py**: ترحيل `append_feedback` + نظام قاموس التصحيح المتقدم (`CorrectionRule`, `build_correction_dict_v2`, `calculate_rule_indicator`, إلخ) من `src/correction.py`.
- **OCREngine.from_legacy_config()**: classmethod جديد في `modules/vision/ocr_engine.py` يسمح بإنشاء المحرك من كائن Config القديم بمعامل واحد.
- **notebooks/README.md**: دليل استخدام يصف كل دفتر (حديث/أرشيف) مع نصائح البدء السريع.
- **requirements-dev.txt**: ملف متطلبات التطوير المنفصل (pytest, ruff) — تم فصله عن requirements-core.txt.
- **tests/test_arabic_nlp_utils.py**: 16 اختباراً لوحدة arabic_nlp_utils (تطبيع، تشابه، تقرير).

### Changed
- **src/gradio_ui.py**: تحديث 5 استيرادات لتفضل modules/ مع fallback إلى src/ (HandwritingDB, OCREngine, append_feedback, reconstruct_sentences, logger).
- **src/__init__.py**: إعادة كتابته كطبقة backward-compatibility — يستورد من modules/ أولاً ويعود لـ src/ عند الفشل.
- **Version unification**: توحيد رقم الإصدار إلى v4.1.1 في main.py, app.py, config.py, __init__.py, database.py, README.md.
- **requirements-core.txt**: إزالة مكتبات الاختبار (pytest, flake8, black, isort) ونقلها إلى requirements-dev.txt.
- **README.md**: إضافة ملاحظة معمارية توثق قرار src/ (كود عملي) مقابل modules/ (بنية نظرية) والخطة التدريجية للتحويل.
- **CHANGELOG**: تصحيح تاريخ v4.1.0 من 2025-05-03 إلى 2026-04-28.

### Architecture Notes
- `src/` أصبحت طبقة توافق عكسي (backward-compatibility layer).
- جميع المكونات المُرحَّلة تستخدم نمط try/except: `from modules.X import Y` ثم fallback `from src.X import Y`.
- `src/` ستُحذف بالكامل في v5.0 بعد ترحيل المكونات المتبقية (recognition, preprocessing, study_guide, finetuning, pdf_processor, export).

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

## [4.1.0] — 2026-04-28

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
