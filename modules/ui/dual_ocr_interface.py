# ══════════════════════════════════════════════════════════╗
#  Interactive Dual-OCR Verification UI (Gradio) - v5.0
#  Side-by-side comparison | Difference highlighting | Human confirmation
# ══════════════════════════════════════════════════════════╝

import gradio as gr
from pathlib import Path
from PIL import Image as PILImage
from typing import Optional, List, Dict

from modules.vision.dual_ocr_verifier import DualOCRVerifier
from modules.audit.pipeline import DualOCRVerificationPipeline


# ─── Global State ───
_pipeline: Optional[DualOCRVerificationPipeline] = None
_current_results: Optional[List[Dict]] = None
_current_idx: int = 0


def _get_pipeline(
    model_path: Optional[str] = None,
    auto_save_threshold: float = 0.85,
) -> DualOCRVerificationPipeline:
    """Get or create the pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DualOCRVerificationPipeline(
            model_path=model_path,
            auto_save_threshold=auto_save_threshold,
        )
    return _pipeline


# ────────────────────────────────────────────────────────
# UI Callbacks
# ────────────────────────────────────────────────────────

def init_engine(model_path: str = ""):
    """تهيئة المحركين TrOCR + EasyOCR"""
    global _pipeline
    path = model_path.strip() if model_path.strip() else None
    _pipeline = DualOCRVerificationPipeline(
        model_path=path,
        auto_save_threshold=0.85,
    )
    version = _pipeline.verifier.model_version
    return f"Engine initialized. Model: {version}"


def verify_and_display(file_path: str):
    """بدء التحقق المزدوج لصفحة مرفوعة"""
    global _current_results, _current_idx

    if not file_path:
        return None, "", "", "", "Please upload an image first", gr.update(visible=False)

    pipeline = _get_pipeline()
    result = pipeline.process_page(file_path)

    if 'error' in result:
        return None, "", "", "", f"Error: {result['error']}", gr.update(visible=False)

    review_results = result.get('manual_review_results', [])
    all_results = []

    # Get all verified lines from the verifier
    import cv2
    img = cv2.imread(file_path)
    lines = pipeline.verifier.extract_lines(img)
    for i, (y1, y2) in enumerate(lines):
        line_img = img[y1:y2]
        vr = pipeline.verifier.verify_line(line_img, i)
        all_results.append(vr)

    _current_results = all_results
    _current_idx = 0

    if all_results:
        return _display_line(0)
    else:
        return None, "", "", "", "No lines detected", gr.update(visible=False)


def _display_line(idx: int):
    """عرض سطر محدد من النتائج"""
    global _current_results, _current_idx

    if not _current_results or idx < 0 or idx >= len(_current_results):
        return None, "", "", "", "No data", gr.update()

    _current_idx = idx
    res = _current_results[idx]
    verifier = _current_results[idx]  # for highlight_differences (static method)

    diff_text = DualOCRVerifier.highlight_differences(
        res['trocr_text'], res['easyocr_text']
    )

    status_parts = [f"Similarity: {res['similarity']:.1%}"]
    if res['critical_content']:
        status_parts.append("Critical Content Detected")
    if res['has_critical_mismatch']:
        status_parts.append("Critical Mismatch")
    status_parts.append(f"Recommendation: {res['recommendation']}")

    line_img = PILImage.fromarray(res['image'])
    status = f"Line {idx + 1}/{len(_current_results)} | {' | '.join(status_parts)}"

    return line_img, res['trocr_text'], res['easyocr_text'], diff_text, status, gr.update()


def navigate_prev():
    """التنقل للسطر السابق"""
    global _current_idx
    if _current_idx > 0:
        return _display_line(_current_idx - 1)
    return _display_line(0)


def navigate_next():
    """التنقل للسطر التالي"""
    global _current_idx
    if _current_results and _current_idx < len(_current_results) - 1:
        return _display_line(_current_idx + 1)
    return _display_line(_current_idx)


def accept_current(text_override: str = ""):
    """قبول السطر الحالي وحفظه في سجل التدقيق"""
    global _current_results, _current_idx

    if not _current_results:
        return "No data to accept"

    pipeline = _get_pipeline()
    res = _current_results[_current_idx]

    if text_override and text_override.strip():
        final = text_override.strip()
        action = "USER_CORRECT"
    elif res['final_text']:
        final = res['final_text']
        action = "USER_CONFIRM"
    else:
        final = res['trocr_text']
        action = "USER_OVERRIDE"

    msg = pipeline.log_user_action(res, action, final)
    return f"Accepted line {_current_idx + 1}: {final[:60]}..."


def generate_report():
    """Generate audit report from current logs"""
    from modules.audit.report_generator import AuditReportGenerator

    generator = AuditReportGenerator()
    report = generator.generate_report()
    return report


# ────────────────────────────────────────────────────────
# Build Gradio Interface
# ────────────────────────────────────────────────────────

def build_dual_ocr_ui() -> gr.Blocks:
    """Build and return the Gradio Blocks interface."""

    with gr.Blocks(title="Dual-OCR Verification System") as dual_ui:
        gr.Markdown("# Dual-OCR Medical Verification System")
        gr.Markdown(
            "Compares TrOCR (trained model) vs EasyOCR (external reference) "
            "with automatic critical mismatch detection."
        )

        # ─── Initialization ───
        with gr.Row():
            model_input = gr.Textbox(
                label="Model Path (optional)", placeholder="Leave empty for default model"
            )
            btn_init = gr.Button("Initialize Engines", variant="secondary")
        status_init = gr.Textbox(label="Initialization Status", interactive=False)

        # ─── File Upload ───
        f_in = gr.File(label="Upload page for dual verification", type="filepath")
        btn_verify = gr.Button("Start Dual Verification", variant="primary")

        # ─── Results Display ───
        with gr.Row():
            with gr.Column(scale=1):
                img_out = gr.Image(label="Current Line", height=250)
            with gr.Column(scale=2):
                trocr_out = gr.Textbox(label="TrOCR (Trained Model)", lines=2)
                easyocr_out = gr.Textbox(label="EasyOCR (External Reference)", lines=2)
                diff_out = gr.Textbox(label="Highlighted Differences", lines=2)

        status_out = gr.Textbox(label="Verification Status")

        # ─── Navigation ───
        with gr.Row():
            btn_prev = gr.Button("Previous")
            text_override = gr.Textbox(label="Corrected Text (optional)", placeholder="Type correction here...")
            btn_next = gr.Button("Next")

        with gr.Row():
            btn_accept = gr.Button("Accept & Save", variant="primary")
            btn_report = gr.Button("Generate Audit Report", variant="secondary")

        # ─── Report Output ───
        report_out = gr.Textbox(label="Audit Report", lines=15, visible=False)

        # ─── Wire Events ───
        btn_init.click(init_engine, inputs=[model_input], outputs=[status_init])
        btn_verify.click(
            verify_and_display,
            inputs=[f_in],
            outputs=[img_out, trocr_out, easyocr_out, diff_out, status_out, gr.Button(visible=True)],
        )
        btn_prev.click(navigate_prev, outputs=[img_out, trocr_out, easyocr_out, diff_out, status_out, gr.Button()])
        btn_next.click(navigate_next, outputs=[img_out, trocr_out, easyocr_out, diff_out, status_out, gr.Button()])
        btn_accept.click(
            accept_current,
            inputs=[text_override],
            outputs=[status_out],
        )
        btn_report.click(
            generate_report,
            outputs=[report_out],
        )

    return dual_ui


def launch_ui(share: bool = False, server_port: int = 7860):
    """Launch the Gradio UI."""
    ui = build_dual_ocr_ui()
    ui.launch(share=share, server_port=server_port)
    return ui
