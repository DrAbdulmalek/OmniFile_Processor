"""
Gradio Tab for Medical Handwriting OCR
=======================================
دمج معالج OCR الطبي مع واجهة Gradio الحالية لـ OmniFile_Processor.

القدرات:
- رفع ملف PDF أو صورة
- استخراج النصوص مع التصحيح الطبي التلقائي
- تصدير JSON + HTML للمراجعة البشرية
- تكامل مباشر مع MedicalOCRProcessor
"""

import gradio as gr
from pathlib import Path
import tempfile
import shutil

from .medical_ocr import MedicalOCRProcessor, process_medical_pdf


def create_medical_ocr_tab():
    """
    إنشاء تبويب Gradio لمعالجة النصوص الطبية المكتوبة بخط اليد.

    Returns:
        gr.Blocks: التبويب الجاهز للإضافة إلى واجهة Gradio
    """
    with gr.Blocks() as medical_tab:
        gr.Markdown("## معالج النصوص الطبية (خط يدوي - عربي/إنجليزي)")
        gr.Markdown(
            "يرفع ملف PDF أو صورة، يستخرج النص باستخدام OCR متخصص، "
            "يسمح بالمراجعة والتصحيح عبر واجهة HTML تفاعلية."
        )

        with gr.Row():
            file_input = gr.File(
                label="رفع ملف PDF أو صورة",
                file_types=[".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
            )
            max_pages = gr.Number(
                label="عدد الصفحات (اتركه فارغاً للكل)",
                value=10,
                precision=0,
            )

        with gr.Row():
            use_gpu = gr.Checkbox(label="استخدام GPU (إن وُجد)", value=False)
            btn_run = gr.Button("بدء المعالجة", variant="primary", size="lg")

        with gr.Row():
            json_output = gr.File(label="النتيجة (JSON)")
            html_output = gr.File(label="صفحة المراجعة (HTML)")

        status = gr.Textbox(label="الحالة", interactive=False)

        def run_ocr(file_obj, pages, gpu):
            if file_obj is None:
                return None, None, "يرجى رفع ملف أولاً"

            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir) / file_obj.name
                    shutil.copy(file_obj.name, tmp_path)
                    out_dir = Path(tmpdir) / "output"

                    json_path, html_path = process_medical_pdf(
                        tmp_path,
                        out_dir,
                        max_pages=int(pages) if pages else None,
                        use_gpu=gpu,
                    )

                    # نسخ الملفات لمكان يمكن لـ Gradio الوصول إليه
                    final_json = Path(tmpdir) / "results.json"
                    final_html = Path(tmpdir) / "review.html"
                    shutil.copy(json_path, final_json)
                    shutil.copy(html_path, final_html)

                    total_lines = sum(
                        len(p.get("lines", []))
                        for p in (gr.load(json_path) if False else [])
                    )

                    return (
                        str(final_json),
                        str(final_html),
                        f"تمت المعالجة بنجاح. تم استخراج النصوص.",
                    )
            except Exception as e:
                return None, None, f"خطأ: {str(e)}"

        btn_run.click(
            run_ocr,
            inputs=[file_input, max_pages, use_gpu],
            outputs=[json_output, html_output, status],
        )

        gr.Markdown("### ملاحظات")
        gr.Markdown(
            "- النموذج يعمل محلياً (Offline) بعد التحميل الأول.\n"
            "- يمكن تحميل صفحة المراجعة وتعديل النصوص ثم إعادة رفعها.\n"
            "- القاموس الطبي قابل للتوسيع عبر ملف config/medical_dict.json."
        )

    return medical_tab
