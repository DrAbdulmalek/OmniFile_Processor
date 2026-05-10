#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
examples/interactive_learning_demo.py
=====================================

عرض تفاعلي لنظام التعلم.
"""

from pathlib import Path
import sys

# إضافة المسار
sys.path.insert(0, str(Path(__file__).parent.parent))

from interactive_learning import InteractiveLearningSystem, process_and_learn


def demo_basic():
    """عرض أساسي."""
    print("=" * 60)
    print("🎯 OmniFile Interactive Learning - Demo")
    print("=" * 60)

    # إنشاء النظام
    system = InteractiveLearningSystem(
        model_path="microsoft/trocr-large-handwritten",
        learning_mode=True,
        auto_train=True
    )

    # معالجة صفحة
    image_path = Path("./samples/handwritten_page.jpg")

    if not image_path.exists():
        print(f"❌ لم يتم العثور على: {image_path}")
        print("يرجى وضع صورة نموذجية في المسار")
        return

    print(f"\n📄 تحليل: {image_path}")
    layout = system.process_page(image_path)

    # إحصائيات
    stats = system.get_stats()
    print(f"\n📊 إحصائيات الصفحة:")
    print(f"   الكلمات: {stats['current_page']['words']}")
    print(f"   الفقرات: {stats['current_page']['paragraphs']}")
    print(f"   الجداول: {stats['current_page']['tables']}")
    print(f"   الرسومات: {stats['current_page']['graphics']}")

    # عرض الكلمات منخفضة الثقة
    print("\n⚠️ كلمات تحتاج مراجعة (ثقة < 70%):")
    for para in layout.paragraphs:
        for line in para.lines:
            for word in line.words:
                if word.confidence < 0.7:
                    print(f"   [{word.id}] '{word.text}' (ثقة: {word.confidence:.1%})")

    # وضع التعليم
    print("\n🎯 بدء وضع التعليم...")
    print("   - انقر على الكلمة للتصحيح")
    print("   - Enter للتأكيد")
    print("   - Space للتعليم كصحيحة")
    print("   - Ctrl+S للحفظ")

    corrections = system.teaching_mode(ui_type="desktop")

    print(f"\n✅ تم جمع {len(corrections)} تصحيح")

    # التعلم
    if len(corrections) > 5:
        print("\n🧠 التعلم من التصحيحات...")
        learn_stats = system.learn_from_corrections(force=True)
        print(f"   الحالة: {learn_stats['status']}")
        print(f"   الخسارة النهائية: {learn_stats.get('final_loss', 'N/A')}")

    # إنتاج المخرجات
    print("\n📄 إنتاج المستند...")

    # HTML تفاعلي
    html_path = system.render_with_layout(
        format="html",
        output_path=Path("./output/interactive.html"),
        preserve_graphics=True
    )
    print(f"   HTML: {html_path}")

    # PDF
    pdf_path = system.render_with_layout(
        format="pdf",
        output_path=Path("./output/document.pdf")
    )
    print(f"   PDF: {pdf_path}")

    # تصدير بيانات التدريب
    print("\n💾 تصدير بيانات التدريب...")
    train_data = system.export_training_data(Path("./output/training_data"))
    print(f"   التدريب: {train_data['train']}")
    print(f"   التحقق: {train_data.get('val', 'N/A')}")
    print(f"   الإجمالي: {train_data['total_pairs']} زوج")

    # الإحصائيات النهائية
    print("\n" + "=" * 60)
    print("📊 الإحصائيات النهائية:")
    final_stats = system.get_stats()
    print(f"   خطوات التدريب: {final_stats['learning']['training_steps']}")
    print(f"   التصحيحات الكلية: {final_stats['learning']['total_corrections']}")
    print("=" * 60)


def demo_with_graphics():
    """عرض مع رسومات ومخططات."""
    print("\n" + "=" * 60)
    print("📊 عرض الرسومات والمخططات")
    print("=" * 60)

    system = InteractiveLearningSystem()

    # رسم مخطط تدفق
    print("\n🔷 رسم مخطط تدفق...")

    flowchart_nodes = [
        {'id': 'start', 'type': 'start', 'text': 'البداية'},
        {'id': 'input', 'type': 'input', 'text': 'إدخال الصورة'},
        {'id': 'process', 'type': 'process', 'text': 'معالجة OCR'},
        {'id': 'decision', 'type': 'decision', 'text': 'الثقة > 90%؟'},
        {'id': 'output', 'type': 'output', 'text': 'إخراج النتيجة'},
        {'id': 'teach', 'type': 'process', 'text': 'وضع التعليم'},
        {'id': 'learn', 'type': 'process', 'text': 'تعلم'},
        {'id': 'end', 'type': 'end', 'text': 'النهاية'}
    ]

    flowchart_edges = [
        {'source': 'start', 'target': 'input', 'label': ''},
        {'source': 'input', 'target': 'process', 'label': ''},
        {'source': 'process', 'target': 'decision', 'label': ''},
        {'source': 'decision', 'target': 'output', 'label': 'نعم'},
        {'source': 'decision', 'target': 'teach', 'label': 'لا'},
        {'source': 'teach', 'target': 'learn', 'label': ''},
        {'source': 'learn', 'target': 'output', 'label': ''},
        {'source': 'output', 'target': 'end', 'label': ''}
    ]

    flowchart_path = system.render_flowchart(
        nodes=flowchart_nodes,
        edges=flowchart_edges,
        output_path=Path("./output/flowchart.svg"),
        interactive=True
    )
    print(f"   ✅ مخطط التدفق: {flowchart_path}")

    # رسم مخطط بياني
    print("\n📊 رسم مخطط بياني...")

    chart_data = [
        {'label': 'قبل التعلم', 'value': 65, 'color': '#ef5350'},
        {'label': 'بعد 10 تصحيحات', 'value': 78, 'color': '#ffa726'},
        {'label': 'بعد 50 تصحيح', 'value': 89, 'color': '#66bb6a'},
        {'label': 'بعد 100 تصحيح', 'value': 95, 'color': '#42a5f5'}
    ]

    chart_path = system.render_chart(
        chart_type='bar',
        data=chart_data,
        output_path=Path("./output/accuracy_chart.svg"),
        title="تحسين الدقة مع التعلم"
    )
    print(f"   ✅ المخطط البياني: {chart_path}")

    # مخطط دائري
    pie_data = [
        {'label': 'صحيحة', 'value': 75, 'color': '#66bb6a'},
        {'label': 'مصححة', 'value': 20, 'color': '#ffa726'},
        {'label': 'تحتاج مراجعة', 'value': 5, 'color': '#ef5350'}
    ]

    pie_path = system.render_chart(
        chart_type='pie',
        data=pie_data,
        output_path=Path("./output/status_pie.svg"),
        title="حالة الكلمات"
    )
    print(f"   ✅ المخطط الدائري: {pie_path}")


def demo_batch():
    """عرض المعالجة الدفعية."""
    print("\n" + "=" * 60)
    print("📚 معالجة دفعية")
    print("=" * 60)

    from interactive_learning import batch_process

    # جمع الصور
    samples_dir = Path("./samples")
    if not samples_dir.exists():
        print("❌ مجلد samples غير موجود")
        return

    image_paths = list(samples_dir.glob("*.jpg")) + list(samples_dir.glob("*.png"))

    if not image_paths:
        print("❌ لا توجد صور في المجلد")
        return

    print(f"📄 العثور على {len(image_paths)} صورة")

    # معالجة
    results = batch_process(
        image_paths=image_paths,
        output_dir=Path("./output/batch"),
        model_path="microsoft/trocr-large-handwritten"
    )

    print(f"\n✅ تم معالجة {len(results)} صفحة")
    print(f"📊 إجمالي الكلمات: {sum(r['stats']['current_page']['words'] for r in results)}")
    print(f"✏️ إجمالي التصحيحات: {sum(len(r['corrections']) for r in results)}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='OmniFile Interactive Learning Demo')
    parser.add_argument('--mode', choices=['basic', 'graphics', 'batch', 'all'],
                       default='basic', help='نوع العرض')

    args = parser.parse_args()

    if args.mode in ['basic', 'all']:
        demo_basic()

    if args.mode in ['graphics', 'all']:
        demo_with_graphics()

    if args.mode in ['batch', 'all']:
        demo_batch()

    print("\n✨ اكتمل العرض!")
