# 🎯 OmniFile Interactive Learning System

نظام تعليمي تفاعلي للتعرف الضوئي المتقدم مع الحفاظ على التخطيط.

## المميزات الرئيسية

- **تقسيم ذكي**: فصل الصفحة إلى كلمات مع الحفاظ على الترتيب المكاني
- **وضع التعليم**: واجهة تفاعلية للتصحيح الكلمة بكلمة
- **تعلم تكيفي**: تحسين النموذج من كل تصحيح فوراً
- **حفظ التخطيط**: إعادة إنتاج الصفحة بالتنسيق الأصلي
- **رسم ذكي**: تحويل الجداول والرسومات إلى عناصر منسقة

## البنية

```

interactive_learning/
├── core/               # المحرك الأساسي
│   ├── segmenter.py    # تقسيم الصفحة
│   ├── word_extractor.py  # استخراج الكلمات
│   └── layout_preserver.py  # الحفاظ على التخطيط
├── ui/                 # واجهة المستخدم
│   ├── word_editor.py  # محرر الكلمات
│   └── layout_viewer.py  # عارض التخطيط
├── learning/           # التعلم التكيفي
│   ├── online_learner.py  # التعلم الفوري
│   └── feedback_loop.py   # حلقة التغذية الراجعة
├── rendering/          # إعادة الإنتاج
│   ├── html_renderer.py   # HTML
│   ├── docx_renderer.py   # Word
│   └── pdf_renderer.py    # PDF
└── graphics/           # الرسومات
├── table_drawer.py    # رسم الجداول
├── chart_detector.py  # اكتشاف المخططات
└── diagram_renderer.py # رسم الصناديق

```

## الاستخدام

```python
from interactive_learning import InteractiveLearningSystem

system = InteractiveLearningSystem(
    model_path="models/trocr-arabic-v2",
    learning_mode=True
)

# معالجة صفحة
result = system.process_page("document.jpg")

# وضع التعليم - يتفاعل مع المستخدم
corrections = system.teaching_mode(result)

# التعلم من التصحيحات
system.learn_from_corrections(corrections)

# إنتاج المستند النهائي
output = system.render_with_layout(
    corrections,
    format="html",  # أو "docx", "pdf"
    preserve_graphics=True
)
```
