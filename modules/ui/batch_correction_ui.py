# ══════════════════════════════════════════════════════════╗
#  Interactive Batch Correction UI (Gradio)
#  Review and correct OCR results line by line
# ══════════════════════════════════════════════════════════╝

import json
from pathlib import Path
from typing import Dict, List, Optional

import gradio as gr
import numpy as np
from PIL import Image

from modules.vision.batch_ocr import BatchMedicalOCR


class BatchCorrectionUI:
    """
    واجهة مراجعة تصحيحية تفاعلية.

    تعرض نتائج OCR سطراً بسطر مع الصورة المقابلة،
    ويتدخل المستخدم لتصحيح الأخطاء قبل الحفظ النهائي.
    """

    def __init__(
        self,
        raw_data_path: Optional[str] = None,
        output_path: Optional[str] = None,
    ):
        self.raw_data_path = Path(raw_data_path) if raw_data_path else None
        self.output_path = Path(output_path) if output_path else None

        self.current_data: List[Dict] = []
        self.current_page_idx: int = 0
        self.current_line_idx: int = 0

    # ────────────────────────────────────────────────────────
    # Data Loading
    # ────────────────────────────────────────────────────────

    def load_raw_data(self) -> str:
        """تحميل البيانات الخام من ملف JSON."""
        if self.raw_data_path and self.raw_data_path.exists():
            self.current_data = json.loads(
                self.raw_data_path.read_text(encoding='utf-8')
            )
        else:
            return "No raw data file found. Run batch processing first."

        self.current_page_idx = 0
        self.current_line_idx = 0
        return f"Loaded {len(self.current_data)} pages for review."

    def load_from_results(self, results: List[Dict]) -> str:
        """تحميل البيانات مباشرة من نتائج BatchMedicalOCR."""
        # Convert numpy arrays to lists for JSON compatibility
        serializable = []
        for page in results:
            page_data = {'page': page['page'], 'lines': []}
            for line in page['lines']:
                line_data = {
                    'idx': line['idx'],
                    'text': line['text'],
                    'refs': line.get('refs', []),
                    'raw': line.get('raw', ''),
                }
                if 'crop' in line:
                    crop = line['crop']
                    if isinstance(crop, np.ndarray):
                        line_data['crop'] = crop.tolist()
                    else:
                        line_data['crop'] = crop
                page_data['lines'].append(line_data)
            serializable.append(page_data)

        self.current_data = serializable
        self.current_page_idx = 0
        self.current_line_idx = 0
        return f"Loaded {len(self.current_data)} pages for review."

    # ────────────────────────────────────────────────────────
    # Navigation
    # ────────────────────────────────────────────────────────

    def _get_current_line(self):
        """استرجاع السطر الحالي للعرض."""
        if not self.current_data:
            return None, "", "", "No data"

        # Find next non-empty line
        while self.current_page_idx < len(self.current_data):
            page = self.current_data[self.current_page_idx]
            if self.current_line_idx < len(page['lines']):
                line = page['lines'][self.current_line_idx]
                img = None
                if 'crop' in line and line['crop'] is not None:
                    crop = line['crop']
                    if isinstance(crop, list):
                        crop = np.array(crop, dtype=np.uint8)
                    if len(crop.shape) == 2:
                        img = Image.fromarray(crop)

                refs = line.get('refs', [])
                meta = (
                    f"Page {self.current_page_idx + 1}/{len(self.current_data)} | "
                    f"Line {self.current_line_idx + 1}/{len(page['lines'])} | "
                    f"Refs: {refs}"
                )
                return img, line['text'], line['text'], meta
            else:
                self.current_page_idx += 1
                self.current_line_idx = 0

        return None, "", "", "Review complete!"

    def save_and_next(self, corrected_text: str):
        """حفظ التصحيح والانتقال للسطر التالي."""
        if not self.current_data:
            return None, "", "", "No data"

        # Save correction
        page = self.current_data[self.current_page_idx]
        if self.current_line_idx < len(page['lines']):
            page['lines'][self.current_line_idx]['text'] = corrected_text.strip()

        # Move to next line
        self.current_line_idx += 1
        if self.current_line_idx >= len(page['lines']):
            self.current_line_idx = 0
            self.current_page_idx += 1

            # Check if review is complete
            if self.current_page_idx >= len(self.current_data):
                self._save_final()
                return None, "", "", "Review complete! Saved."

        return self._get_current_line()

    def _save_final(self):
        """حفظ النتائج النهائية المصححة."""
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            # Remove crop data (too large for JSON) before saving
            clean_data = []
            for page in self.current_data:
                clean_page = {'page': page['page'], 'lines': []}
                for line in page['lines']:
                    clean_line = {
                        'idx': line['idx'],
                        'text': line['text'],
                        'refs': line.get('refs', []),
                        'raw': line.get('raw', ''),
                    }
                    clean_page['lines'].append(clean_line)
                clean_data.append(clean_page)

            self.output_path.write_text(
                json.dumps(clean_data, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

    # ────────────────────────────────────────────────────────
    # Build Gradio Interface
    # ────────────────────────────────────────────────────────

    def build_ui(self) -> gr.Blocks:
        """Build and return the Gradio Blocks interface."""
        ui_ref = self

        with gr.Blocks(title="OCR Review & Correction") as ui:
            gr.Markdown("## Review and correct OCR results line by line.")
            gr.Markdown("Review each line, correct if needed, then click Save & Next.")

            btn_load = gr.Button("Load Raw Data", variant="secondary")
            status = gr.Textbox(label="Status", interactive=False)

            with gr.Row():
                with gr.Column(scale=1):
                    img_disp = gr.Image(label="Line Image", height=200)
                with gr.Column(scale=2):
                    pred_txt = gr.Textbox(label="Predicted Text")
                    corr_txt = gr.Textbox(label="Your Correction", lines=2)

            meta_txt = gr.Textbox(label="Info", interactive=False)

            with gr.Row():
                btn_prev = gr.Button("Previous")
                btn_next = gr.Button("Save & Next", variant="primary")
                btn_save = gr.Button("Save All", variant="stop")

            # Wire events
            btn_load.click(
                fn=ui_ref.load_raw_data,
                outputs=[status],
            )
            btn_load.click(
                fn=ui_ref._get_current_line,
                outputs=[img_disp, pred_txt, corr_txt, meta_txt],
            )
            btn_next.click(
                fn=ui_ref.save_and_next,
                inputs=[corr_txt],
                outputs=[img_disp, pred_txt, corr_txt, meta_txt],
            )
            btn_save.click(
                fn=ui_ref._save_final,
                outputs=[status],
            )

        return ui

    def launch(self, share: bool = False, server_port: int = 7861):
        """Launch the Gradio UI."""
        ui = self.build_ui()
        ui.launch(share=share, server_port=server_port)
