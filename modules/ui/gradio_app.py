#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/ui/gradio_app.py
========================

Unified Gradio interface for OmniFile Processor.

Supports:
- OCR (printed + handwritten)
- HTR specialized (with Line/Word Segmentation)
- NLP & Translation
- Study Guide
- AI Gateway

Author: Dr. Abdulmalek Al-husseini
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# ============================================================================
# Path setup
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# Lazy imports - only load when needed
# ============================================================================


class OmniFileConfig:
    """Application settings."""

    # OCR
    OCR_ENGINE = os.getenv("OMNIFILE_OCR_ENGINE", "trocr")

    # HTR
    HTR_MODEL_PATH = os.getenv("OMNIFILE_HTR_MODEL", None)
    HTR_USE_LINE_SEGMENTATION = os.getenv("OMNIFILE_HTR_LINE_SEG", "true").lower() == "true"
    HTR_USE_WORD_SEGMENTATION = os.getenv("OMNIFILE_HTR_WORD_SEG", "true").lower() == "true"
    HTR_USE_DOTTED_RECOVERY = os.getenv("OMNIFILE_HTR_DOTTED", "true").lower() == "true"

    # AI Gateway
    AI_GATEWAY_PROVIDERS = ["deepseek", "openrouter", "ollama"]

    # Security
    ENABLE_PII_SCAN = os.getenv("OMNIFILE_PII_SCAN", "true").lower() == "true"
    ENABLE_ENCRYPTION = os.getenv("OMNIFILE_ENCRYPTION", "false").lower() == "true"

    # Server
    SERVER_NAME = os.getenv("OMNIFILE_SERVER_NAME", "0.0.0.0")
    SERVER_PORT = int(os.getenv("OMNIFILE_SERVER_PORT", "7860"))
    SHARE = os.getenv("OMNIFILE_SHARE", "false").lower() == "true"


# ============================================================================
# Main Processor
# ============================================================================

class OmniFileProcessor:
    """
    Main processor - unified access to all components.

    Replaces: src/gradio_ui.py + src/ocr/handwritten_ocr.py
    """

    def __init__(self, config: OmniFileConfig = None):
        self.config = config or OmniFileConfig()

        # Components (lazy loaded)
        self._ocr = None
        self._htr = None
        self._preprocessor = None
        self._text_analyzer = None
        self._translator = None
        self._study_guide = None
        self._ai_gateway = None
        self._security = None
        self._pii_scanner = None

    def _get_ocr(self):
        """Lazy load OCR engine."""
        if self._ocr is None:
            try:
                from modules.vision.ocr_engine import OCREngine
                self._ocr = OCREngine(engine=self.config.OCR_ENGINE)
            except ImportError:
                from src.recognition import OCREngine
                self._ocr = OCREngine()
        return self._ocr

    def _get_htr(self):
        """Lazy load HTR engine."""
        if self._htr is None:
            try:
                from modules.vision.htr import ArabicHandwrittenHTR
                self._htr = ArabicHandwrittenHTR(
                    model_path=self.config.HTR_MODEL_PATH,
                    use_line_segmentation=self.config.HTR_USE_LINE_SEGMENTATION,
                    use_word_segmentation=self.config.HTR_USE_WORD_SEGMENTATION,
                    use_dotted_recovery=self.config.HTR_USE_DOTTED_RECOVERY
                )
            except ImportError as e:
                raise RuntimeError(
                    f"HTR module not available: {e}. "
                    "Install with: pip install -e .[htr]"
                )
        return self._htr

    def _get_preprocessor(self):
        """Lazy load preprocessor."""
        if self._preprocessor is None:
            try:
                from modules.vision.image_preprocessor import ImagePreprocessor
                self._preprocessor = ImagePreprocessor()
            except ImportError:
                try:
                    from src.preprocessing import preprocess_image
                    self._preprocessor = preprocess_image
                except ImportError:
                    self._preprocessor = lambda x: x
        return self._preprocessor

    def _get_text_analyzer(self):
        """Lazy load text analyzer."""
        if self._text_analyzer is None:
            try:
                from modules.nlp.text_analyzer import TextAnalyzer
                self._text_analyzer = TextAnalyzer()
            except ImportError:
                self._text_analyzer = lambda text, **kw: {"text": text, "analysis": "basic"}
        return self._text_analyzer

    def _get_translator(self):
        """Lazy load translator."""
        if self._translator is None:
            try:
                from modules.nlp.translator import TranslationManager
                self._translator = TranslationManager()
            except ImportError:
                self._translator = lambda text, src, tgt, **kw: f"[Translation: {src}->{tgt}] {text}"
        return self._translator

    def _get_study_guide(self):
        """Lazy load study guide generator."""
        if self._study_guide is None:
            try:
                from modules.education.study_guide import StudyGuideGenerator
                self._study_guide = StudyGuideGenerator()
            except ImportError:
                try:
                    from src.study_guide import generate_study_guide
                    self._study_guide = generate_study_guide
                except ImportError:
                    self._study_guide = lambda **kw: {"guide": "Study guide generation not available"}
        return self._study_guide

    def _get_ai_gateway(self):
        """Lazy load AI gateway."""
        if self._ai_gateway is None:
            try:
                from modules.ai.gateway import AIGateway
                self._ai_gateway = AIGateway(providers=self.config.AI_GATEWAY_PROVIDERS)
            except ImportError:
                self._ai_gateway = None
        return self._ai_gateway

    def _get_pii_scanner(self):
        """Lazy load PII scanner."""
        if self._pii_scanner is None and self.config.ENABLE_PII_SCAN:
            try:
                from modules.security.pii_scanner import PIIScanner
                self._pii_scanner = PIIScanner()
            except ImportError:
                self._pii_scanner = None
        return self._pii_scanner

    def _get_security(self):
        """Lazy load security handler."""
        if self._security is None and self.config.ENABLE_ENCRYPTION:
            try:
                from modules.security.encryption import SecureFileHandler
                self._security = SecureFileHandler()
            except ImportError:
                self._security = None
        return self._security

    # -------------------------------------------------------------------------
    # OCR / HTR
    # -------------------------------------------------------------------------

    def process_image(
        self,
        image,
        mode: str = "auto",
        language: str = "ar",
        return_lines: bool = False,
        return_words: bool = False
    ) -> Dict:
        """
        Process image (OCR or HTR).

        Args:
            image: Input image (PIL, numpy, or path)
            mode: "auto", "printed", "handwritten"
            language: "ar", "en", "multi"
            return_lines: Return line details
            return_words: Return word details

        Returns:
            dict with results
        """
        # Load image
        if isinstance(image, str):
            from PIL import Image
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            from PIL import Image
            image = Image.fromarray(image)

        # Preprocess
        preprocessor = self._get_preprocessor()
        if callable(preprocessor):
            image = preprocessor(image)

        # Auto-detect mode
        if mode == "auto":
            mode = self._detect_mode(image)

        # Recognize
        if mode == "handwritten":
            result = self._process_handwritten(
                image, language, return_lines, return_words
            )
        else:
            result = self._process_printed(image, language)

        # PII scan
        pii_scanner = self._get_pii_scanner()
        if pii_scanner and result.get("text"):
            try:
                pii_findings = pii_scanner.scan(result["text"])
                result["pii_detected"] = len(pii_findings) > 0
                result["pii_findings"] = pii_findings
            except Exception:
                pass

        return result

    def _detect_mode(self, image) -> str:
        """Detect if text is printed or handwritten."""
        return "handwritten"

    def _process_handwritten(
        self, image, language: str, return_lines: bool, return_words: bool
    ) -> Dict:
        """Process handwritten text."""
        htr = self._get_htr()

        try:
            result = htr.recognize(
                image,
                return_lines=return_lines,
                return_words=return_words
            )

            return {
                "text": result.text,
                "mode": "handwritten",
                "confidence": getattr(result, 'confidence', 0.0),
                "lines": getattr(result, 'lines', None) if return_lines else None,
                "words": getattr(result, 'words', None) if return_words else None,
                "language": language
            }
        except Exception as e:
            return {
                "text": f"[HTR Error: {str(e)}]",
                "mode": "handwritten",
                "confidence": 0.0,
                "error": str(e),
                "language": language
            }

    def _process_printed(self, image, language: str) -> Dict:
        """Process printed text."""
        try:
            ocr = self._get_ocr()
            text, confidence = ocr.recognize(image, language=language)

            return {
                "text": text,
                "mode": "printed",
                "confidence": confidence,
                "language": language
            }
        except Exception as e:
            return {
                "text": f"[OCR Error: {str(e)}]",
                "mode": "printed",
                "confidence": 0.0,
                "error": str(e),
                "language": language
            }

    # -------------------------------------------------------------------------
    # NLP
    # -------------------------------------------------------------------------

    def analyze_text(self, text: str, analysis_type: str = "full") -> Dict:
        """Analyze text."""
        try:
            analyzer = self._get_text_analyzer()
            if callable(analyzer) and not hasattr(analyzer, 'analyze'):
                return {"text": text, "analysis_type": analysis_type, "result": analyzer(text)}
            return analyzer.analyze(text, analysis_type)
        except Exception as e:
            return {"text": text, "error": str(e)}

    def translate(self, text: str, source_lang: str, target_lang: str, use_ai: bool = True) -> str:
        """Translate text."""
        if use_ai and self._get_ai_gateway():
            try:
                return self._get_ai_gateway().translate(text, source_lang, target_lang)
            except Exception:
                pass
        try:
            translator = self._get_translator()
            return translator(text, source_lang, target_lang)
        except Exception as e:
            return f"[Translation Error: {str(e)}]"

    # -------------------------------------------------------------------------
    # Study Guide
    # -------------------------------------------------------------------------

    def generate_study_guide(self, content: str, title: str = "", difficulty: str = "medium") -> Dict:
        """Generate study guide."""
        try:
            sg = self._get_study_guide()
            if callable(sg) and not hasattr(sg, 'generate'):
                return sg(content=content, title=title, difficulty=difficulty)
            return sg.generate(content=content, title=title, difficulty=difficulty)
        except Exception as e:
            return {"error": str(e)}

    # -------------------------------------------------------------------------
    # AI Gateway
    # -------------------------------------------------------------------------

    def get_available_providers(self) -> List[str]:
        """Get available AI providers."""
        gateway = self._get_ai_gateway()
        if gateway and hasattr(gateway, 'get_available_providers'):
            return gateway.get_available_providers()
        return self.config.AI_GATEWAY_PROVIDERS

    def generate_ai_response(self, prompt: str, provider: str = "deepseek") -> Tuple[str, str]:
        """Generate AI response."""
        gateway = self._get_ai_gateway()
        if gateway:
            try:
                response, used_provider = gateway.generate(prompt, provider=provider)
                return response, used_provider
            except Exception as e:
                return f"[AI Error: {str(e)}]", "none"
        return "AI Gateway not available", "none"


# ============================================================================
# Gradio Interface
# ============================================================================

def create_gradio_interface() -> 'gr.Blocks':
    """Create Gradio interface."""
    try:
        import gradio as gr
    except ImportError:
        raise ImportError(
            "gradio is required for the web interface. "
            "Install with: pip install gradio"
        )

    processor = OmniFileProcessor()

    with gr.Blocks(title="OmniFile Processor", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # OmniFile Processor
        ### Smart File Processor - OCR, HTR, NLP & Translation

        **Version 5.0** | New Architecture: `modules/`
        """)

        with gr.Tab("OCR / HTR"):
            with gr.Row():
                with gr.Column():
                    image_input = gr.Image(
                        type="pil",
                        label="Input Image",
                        sources=["upload", "clipboard"]
                    )

                    with gr.Row():
                        mode = gr.Radio(
                            choices=["auto", "printed", "handwritten"],
                            value="auto",
                            label="Recognition Mode"
                        )
                        language = gr.Dropdown(
                            choices=["ar", "en", "multi"],
                            value="ar",
                            label="Language"
                        )

                    with gr.Row():
                        return_lines = gr.Checkbox(label="Return Line Details", value=False)
                        return_words = gr.Checkbox(label="Return Word Details", value=False)

                    process_btn = gr.Button("Process", variant="primary")

                with gr.Column():
                    text_output = gr.Textbox(label="Extracted Text", lines=10)
                    confidence_output = gr.Number(label="Confidence")
                    mode_output = gr.Textbox(label="Detected Mode")

                    with gr.Accordion("Additional Details", open=False):
                        lines_output = gr.JSON(label="Lines")
                        words_output = gr.JSON(label="Words")

            def process_ocr(image, mode, language, return_lines, return_words):
                if image is None:
                    return "Please upload an image", 0, "", None, None

                result = processor.process_image(
                    image,
                    mode=mode,
                    language=language,
                    return_lines=return_lines,
                    return_words=return_words
                )

                return (
                    result["text"],
                    result.get("confidence", 0),
                    result["mode"],
                    result.get("lines"),
                    result.get("words")
                )

            process_btn.click(
                fn=process_ocr,
                inputs=[image_input, mode, language, return_lines, return_words],
                outputs=[text_output, confidence_output, mode_output, lines_output, words_output]
            )

        with gr.Tab("NLP"):
            with gr.Row():
                with gr.Column():
                    nlp_input = gr.Textbox(label="Text to Analyze", lines=5)
                    analysis_type = gr.Dropdown(
                        choices=["full", "sentiment", "entities", "keywords", "summary"],
                        value="full",
                        label="Analysis Type"
                    )
                    analyze_btn = gr.Button("Analyze")

                with gr.Column():
                    nlp_output = gr.JSON(label="Analysis Results")

            analyze_btn.click(
                fn=lambda text, type: processor.analyze_text(text, type),
                inputs=[nlp_input, analysis_type],
                outputs=nlp_output
            )

        with gr.Tab("Translation"):
            with gr.Row():
                with gr.Column():
                    trans_input = gr.Textbox(label="Text", lines=5)
                    source_lang = gr.Dropdown(
                        choices=["ar", "en", "fr", "de", "es", "zh"],
                        value="ar",
                        label="From"
                    )
                    target_lang = gr.Dropdown(
                        choices=["ar", "en", "fr", "de", "es", "zh"],
                        value="en",
                        label="To"
                    )
                    trans_btn = gr.Button("Translate")

                with gr.Column():
                    trans_output = gr.Textbox(label="Translation", lines=5)

            trans_btn.click(
                fn=lambda text, src, tgt: processor.translate(text, src, tgt),
                inputs=[trans_input, source_lang, target_lang],
                outputs=trans_output
            )

        with gr.Tab("Study Guide"):
            with gr.Row():
                with gr.Column():
                    study_input = gr.Textbox(label="Study Content", lines=10)
                    study_title = gr.Textbox(label="Title")
                    study_difficulty = gr.Dropdown(
                        choices=["easy", "medium", "hard"],
                        value="medium",
                        label="Difficulty"
                    )
                    study_btn = gr.Button("Generate Guide")

                with gr.Column():
                    study_output = gr.JSON(label="Study Guide")

            study_btn.click(
                fn=lambda content, title, diff: processor.generate_study_guide(content, title, diff),
                inputs=[study_input, study_title, study_difficulty],
                outputs=study_output
            )

        with gr.Tab("AI Gateway"):
            providers = processor.get_available_providers()
            gr.Markdown("""
            ### AI Gateway

            Providers: DeepSeek, NVIDIA NIM, OpenRouter, Ollama, LM Studio, llama.cpp, Kimi, Wafer
            """)

            with gr.Row():
                with gr.Column():
                    prompt_input = gr.Textbox(label="Question / Request", lines=5)
                    provider = gr.Dropdown(
                        choices=providers,
                        value=providers[0] if providers else "deepseek",
                        label="Provider"
                    )
                    ai_btn = gr.Button("Send")

                with gr.Column():
                    ai_output = gr.Textbox(label="Response", lines=10)
                    ai_provider = gr.Textbox(label="Provider Used")

            def process_ai(prompt, provider):
                response, used_provider = processor.generate_ai_response(prompt, provider)
                return response, used_provider

            ai_btn.click(
                fn=process_ai,
                inputs=[prompt_input, provider],
                outputs=[ai_output, ai_provider]
            )

        gr.Markdown("""
        ---
        **OmniFile Processor v5.0** | [GitHub](https://github.com/DrAbdulmalek/OmniFile_Processor)
        """)

    return app


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    config = OmniFileConfig()
    app = create_gradio_interface()
    app.launch(
        server_name=config.SERVER_NAME,
        server_port=config.SERVER_PORT,
        share=config.SHARE,
        debug=True
    )
