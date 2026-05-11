# ══════════════════════════════════════════════════════════╗
#  Streamlit Batch Processing App
#  Multi-file upload: Images + PDF -> OCR -> Export
# ══════════════════════════════════════════════════════════╝

import io
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List

import numpy as np
from PIL import Image

# === Project Path Setup ===
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# === App Constants ===
APP_TITLE = "OmniFile AI Processor - Batch Processing"
APP_SUBTITLE = "Upload images and PDF files for OCR processing"


def pdf_to_images_pymupdf(pdf_bytes: bytes, dpi: int = 200) -> List[Image.Image]:
    """Convert PDF pages to PIL Images using PyMuPDF."""
    images = []
    try:
        import fitz
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
        pdf_doc.close()
    except Exception as e:
        logger.error("Failed to convert PDF to images: %s", e)
    return images


def render_batch_processing_page():
    """Render the main batch processing page."""
    import streamlit as st

    st.header("Batch File Processing", divider="blue")
    st.markdown(
        "Upload images and PDF files. "
        "PDFs are converted to images page-by-page, then each image "
        "is processed individually through the OCR engine."
    )

    # Settings
    with st.expander("Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            target_lang = st.selectbox(
                "Expected text language",
                options=["ar", "en", "fr", "de", "tr"],
                format_func=lambda x: {
                    "ar": "Arabic", "en": "English", "fr": "French",
                    "de": "German", "tr": "Turkish",
                }.get(x, x),
                index=0,
            )
        with col2:
            dpi_setting = st.slider(
                "PDF extraction DPI",
                min_value=72, max_value=400, value=200, step=10,
            )

    # File uploader (unlimited files)
    uploaded_files = st.file_uploader(
        "Select images or PDF files",
        type=["png", "jpg", "jpeg", "bmp", "tiff", "pdf"],
        accept_multiple_files=True,
        key="batch_uploader",
        help="You can upload unlimited files at once.",
    )

    if not uploaded_files:
        st.info("Upload your files to begin processing.")
        return

    # File summary
    st.subheader(f"Selected Files ({len(uploaded_files)})")
    st.write(", ".join(f.name for f in uploaded_files))

    # Process button
    if st.button("Start Processing All Files", type="primary", use_container_width=True):
        ocr_engine = None

        # Try to load project OCR engine
        try:
            from modules.vision.ocr_engine import OCREngine
            ocr_engine = OCREngine()
            logger.info("Project OCR engine loaded successfully.")
        except Exception as e:
            logger.warning("Could not load project OCR engine: %s", e)
            st.warning("Project OCR engine unavailable. Using basic processing.")

        all_texts = []
        total_files = len(uploaded_files)
        progress = st.progress(0, text="Starting...")

        for file_idx, uploaded_file in enumerate(uploaded_files):
            file_name = uploaded_file.name
            st.divider()
            st.markdown(f"### Processing: {file_name}")

            try:
                file_bytes = uploaded_file.read()
                file_type = uploaded_file.type

                if file_type == "application/pdf":
                    # PDF processing
                    pages = pdf_to_images_pymupdf(file_bytes, dpi=dpi_setting)
                    st.write(f"Extracted {len(pages)} pages from PDF.")

                    if not pages:
                        st.warning("No pages extracted from this PDF.")
                        continue

                    page_texts = []
                    for page_num, page_img in enumerate(pages):
                        if ocr_engine:
                            try:
                                result = ocr_engine.recognize(
                                    page_img, languages=[target_lang]
                                )
                                text = result.get("text", "") if isinstance(result, dict) else str(result)
                                confidence = result.get("confidence", 0.0) if isinstance(result, dict) else 0.0
                            except Exception:
                                text = f"[Page {page_num + 1} - OCR failed]"
                                confidence = 0.0
                        else:
                            text = f"[Page {page_num + 1} - No OCR engine]"
                            confidence = 0.0

                        page_texts.append(
                            f"--- Page {page_num + 1} (Confidence: {confidence:.2f}) ---\n{text}"
                        )
                        prog = (file_idx + (page_num / len(pages))) / total_files
                        progress.progress(prog, text=f"Processing {file_name}: page {page_num + 1}")

                    full_text = "\n\n".join(page_texts)
                    all_texts.append(f"=== {file_name} ===\n\n{full_text}")
                    st.text_area(
                        f"Text from {file_name}",
                        full_text[:3000] + ("..." if len(full_text) > 3000 else ""),
                        height=200,
                        key=f"pdf_text_{file_idx}",
                    )

                else:
                    # Image processing
                    img = Image.open(io.BytesIO(file_bytes))
                    st.image(img, caption=file_name, width=300)

                    if ocr_engine:
                        try:
                            result = ocr_engine.recognize(
                                img, languages=[target_lang]
                            )
                            text = result.get("text", "") if isinstance(result, dict) else str(result)
                            confidence = result.get("confidence", 0.0) if isinstance(result, dict) else 0.0
                        except Exception:
                            text = "[OCR failed]"
                            confidence = 0.0
                    else:
                        text = "[No OCR engine]"
                        confidence = 0.0

                    all_texts.append(f"=== {file_name} (Confidence: {confidence:.2f}) ===\n{text}")
                    st.text_area(
                        f"Text from {file_name}",
                        text,
                        height=200,
                        key=f"img_text_{file_idx}",
                    )
                    progress.progress(
                        (file_idx + 1) / total_files,
                        text=f"Processed {file_name}",
                    )

            except Exception as e:
                st.error(f"Failed to process {file_name}: {e}")
                logger.error("Failed to process %s: %s", file_name, e, exc_info=True)

        progress.progress(1.0, text="Processing complete!")

        # Final results
        st.divider()
        st.header("All Results")
        if all_texts:
            full_output = "\n\n\n".join(all_texts)
            st.text_area("Complete extracted text", full_output, height=400, key="full_output")
            st.download_button(
                label="Download All Texts (TXT)",
                data=full_output,
                file_name=f"extracted_texts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
            )
        else:
            st.warning("No text was extracted.")


def main():
    """Main entry point for the Streamlit app."""
    import streamlit as st

    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    render_batch_processing_page()


if __name__ == "__main__":
    main()
