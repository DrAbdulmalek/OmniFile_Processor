# omnifile-core

النواة القابلة لإعادة الاستخدام من مشروع OmniFile — حزمة pip داخلية تصدّر الواجهات البرمجية المشتركة من شجرة `modules/` الحالية **دون نقل أو نسخ أي ملف**.

## الهدف (لماذا هذه الحزمة؟)

حتى الآن كانت المصححات والأنابيب المتوازية تنسخ الملفات يدوياً — مثال واقعي: `medical-ocr-benchmarks/benchmarks/postprocessor/correction.py` نسخة مستقلة من منطق التصحيح، وكل نسخة تنحرف بمرور الوقت. الهدف من `omnifile-core` أن يكون **المصدر الواحد** لـ:

- قاموس التصحيح `correction_dict.json` (التحميل والتطبيق والبناء من ملاحظات المراجعين)
- تطبيع النص العربي واتجاه RTL من `arabic_rtl.py`
- نقاط التصحيح الإملائي/النحوي (`LanguageCorrector`, `AICorrector`)
- مقاييس التقييم CER/WER من `evaluation/metrics.py`
- تصدير Markdown/DOCX الحافظ للتنسيق

بحيث تستهلك IntelliFile، وأنابيب الـ marathon (medical-ocr-benchmarks)، وmedical-rag-ar حزمة واحدة مثبّتة بدل نسخ الملفات بين المستودعات.

## لماذا طبقة إعادة تصدير رقيقة (thin re-export) وليس ربط `package-dir`؟

اخترنا طبقة إعادة تصدير رقيقة مع تحميل كسول (PEP 562) بدل `[tool.setuptools.package-dir]` الذي يربط `omnifile_core` مباشرة على شجرة `../../modules`، لثة أسباب: أولاً، ربط مسارات خارج جذر الحزمة (`../../modules`) هشّ مع أدوات البناء المعزولة وsdist وقد ينتج عجلة فارغة أو مكسورة حسب الـ frontend. ثانياً، `modules/nlp/__init__.py` **مكسور حالياً** (يستورد `spell_corrector.py` غير الموجود) ويستورد بأسلوب `from modules.nlp...` المطلق الذي لا يُحل بعد التثبيت، أي أن أي `omnifile_core.nlp` مُربوط بالمسار سيفشل عند الاستيراد. ثالثاً، التحميل الكسول يجعل استيراد `omnifile_core` بلا أي تبعية ثقيلة (pandas/python-docx/openai تُستورد فقط عند الوصول لاسم يعتمد عليها). هذا سقالة مؤقتة تحافظ على الواجهة العامة مستقرة، وعلى المشرف حسم النقل الفعلي للملفات لاحقاً.

## التثبيت والاستخدام

```bash
# من جذر المستودع (بدون تثبيت — للتجربة والاختبار):
pip install -e ./packages/omnifile-core

# أو تثبيت عادي:
pip install ./packages/omnifile-core
```

```python
import omnifile_core as oc

oc.is_rtl_text("المريض يعاني من ألم في الركبة")   # True
oc.get_text_direction("مرحبا")                     # 'rtl'
normalized = oc.normalize_arabic_ocr(raw_text)

corrections = oc.load_correction_dict(str(oc.CORRECTION_DICT_PATH))
fixed = oc.apply_correction_dict(text, corrections)

cer, errors, total = oc.calculate_cer(reference, hypothesis)
result = oc.evaluate(reference, hypothesis)        # EvaluationResult(cer, wer, ...)

md = oc.export_to_markdown(layout_data, output_path="out.md")
```

إذا لم تكن تعمل من جذر المستودع، حدّد موقع شجرة `modules/` صراحةً:

```bash
export OMNIFILE_CORE_MODULES_DIR=/path/to/OmniFile_Processor/modules
```

## الواجهة العامة (أسماء حقيقية من المصدر — لا اختراع)

| الاسم | المصدر |
| --- | --- |
| `is_rtl_text`, `get_text_direction`, `normalize_arabic_presentation_forms`, `normalize_arabic_ocr`, `fix_rtl_display`, `fix_arabic_reading_order`, `reorder_bboxes_for_rtl`, `is_arabic_char`, `is_hebrew_char`, `is_rtl_char`, `RTLFixer` | `modules/nlp/arabic_rtl.py` |
| `normalize_for_comparison`, `arabic_normalized_similarity`, `similarity_report` | `modules/nlp/arabic_nlp_utils.py` |
| `load_correction_dict`, `apply_correction_dict`, `track_correction_usage`, `build_correction_dict`, `build_correction_dict_v2` | `modules/nlp/feedback.py` |
| `LanguageCorrector` | `modules/nlp/language_corrector.py` |
| `AICorrector` | `modules/nlp/ai_corrector.py` |
| `EvaluationResult`, `calculate_cer`, `calculate_wer`, `evaluate`, `evaluate_file` | `modules/evaluation/metrics.py` |
| `DocumentExporter` | `modules/export/exporter.py` |
| `export_to_docx`, `layout_to_docx`, `ocr_result_to_layout` | `modules/export/layout_preserving.py` |
| `blocks_to_markdown`, `detect_list_items`, `export_to_markdown` | `modules/export/markdown_exporter.py` |
| `CORRECTION_DICT_PATH` (ثابت: مسار `correction_dict.json` الأصلي) | `modules/nlp/correction_dict.json` |

جميع الأسماء تُحل بشكل كسول عند أول وصول، وتُخزَّن بعدها في الوحدة.

## الاختبارات

```bash
python -m pytest packages/omnifile-core/tests/test_public_api.py -x -q
```

الاختبارات تعمل من جذر المستودع دون تثبيت: `tests/conftest.py` يضيف جذر المستودع ومجلد الحزمة إلى `sys.path`.

## قيود معروفة ومهام معلّقة للمشرف (follow-ups)

1. **`SpellCorrector` غير موجود أصلاً**: `modules/nlp/__init__.py` يستورد `modules.nlp.spell_corrector` لكن الملف غير موجود في المستودع — لذلك `import modules.nlp` يفشل كلياً، ولا يمكن إعادة تصدير `SpellCorrector` قبل استرجاع الملف من التاريخ أو إعادة كتابته. هذه الحزمة تتجاوز `__init__.py` المكسور بتحميل الملفات مباشرة، لكن إصلاح المصدر ضروري.
2. **حسم ربط المسارات**: عندما يُحسم الاستخراج، انقل الشجرة (أو اربط `package-dir`) وأزل آلية `spec_from_file_location` الاحتياطية في `omnifile_core/__init__.py`، واجعل `correction_dict.json` ملف `package-data` داخل الحزمة.
3. **عدد مدخلات القاموس**: يفترض خارطة الطريق أكثر من 100 مدخل، بينما `modules/nlp/correction_dict.json` يحوي حالياً **97 مدخلاً** (بعضها ببنية متداخلة `{الخطأ: {الصحيح: العدد}}`)؛ الاختبار يثبت الحد الحقيقي (>90) حتى لا يفشل زوراً، والقاموس يحتاج تغذية راجعة من مصادر IntelliFile/الأنابيب ليصل لمستواه المستهدف.
4. **نسختان من الوحدة في نفس العملية**: إذا استورد التطبيق `modules.nlp.x` بنجاح (بعد إصلاح `__init__`) وحزمتنا تحمل الملف مباشرة، فستكون كائنين منفصلين — آلية التحميل تفضّل الاستيراد القانوني أولاً لتقليل ذلك، ويُحسم نهائياً عند اكتمال الاستخراج.
