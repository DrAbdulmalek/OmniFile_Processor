#!/usr/bin/env python3
"""
Streamlit Multi-File Upload App for Medical Arabic Handwriting OCR
تطبيق ستريمليت لرفع ومعالجة ملفات متعددة للتعرف على الكتابة الطبية العربية

Features:
- Multi-file upload (PDF, JPG, PNG) / رفع ملفات متعددة
- PDF processing via PyMuPDF / معالجة ملفات PDF
- Progress bar during batch processing / شريط تقدم أثناء المعالجة
- SQLite database for results / قاعدة بيانات لحفظ النتائج
- Original image + extracted text + confidence / صورة أصلية + نص مستخرج + ثقة

Usage:
    streamlit run streamlit_multi_upload.py
    streamlit run streamlit_multi_upload.py --port 8501
"""

import streamlit as st
import cv2
import numpy as np
import sqlite3
import json
import io
import time
import tempfile
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# Page configuration / إعدادات الصفحة
st.set_page_config(
    page_title="OmniFile OCR - Medical Arabic Handwriting",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Constants / الثوابت ----
DB_NAME = "ocr_results.db"
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "tif", "tiff", "bmp"}
MAX_FILE_SIZE_MB = 50
SUPPORTED_LANGUAGES = ["ar", "en"]

# ---- Custom CSS / تنسيق مخصص ----
st.markdown("""
<style>
    .result-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    .confidence-high { color: #2e7d32; font-weight: bold; }
    .confidence-medium { color: #f57f17; font-weight: bold; }
    .confidence-low { color: #c62828; font-weight: bold; }
    .arabic-text {
        direction: rtl;
        text-align: right;
        font-family: 'Amiri', 'Noto Naskh Arabic', serif;
        font-size: 1.1em;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)


# ---- SQLite Database Functions / وظائف قاعدة البيانات ----

def init_database(db_path: str = DB_NAME) -> sqlite3.Connection:
    """
    Initialize SQLite database with results table.
    تهيئة قاعدة بيانات SQLite مع جدول النتائج.

    Args:
        db_path: Path to SQLite database file / مسار ملف قاعدة البيانات

    Returns:
        SQLite connection object / كائن اتصال SQLite
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            original_image BLOB,
            extracted_text TEXT,
            confidence REAL,
            language TEXT DEFAULT 'mixed',
            processing_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_filename
        ON ocr_results(filename)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at
        ON ocr_results(created_at)
    """)
    conn.commit()
    return conn


def save_result(conn: sqlite3.Connection, filename: str, file_type: str,
                image_bytes: Optional[bytes], extracted_text: str,
                confidence: float, processing_time: float,
                language: str = "mixed", notes: str = "") -> int:
    """
    Save OCR result to database.
    حفظ نتيجة OCR في قاعدة البيانات.

    Returns:
        Row ID of inserted record / معرف السجل المُدخل
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ocr_results
        (filename, file_type, original_image, extracted_text,
         confidence, language, processing_time, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, file_type, image_bytes, extracted_text,
          confidence, language, processing_time, notes))
    conn.commit()
    return cursor.lastrowid


def get_all_results(conn: sqlite3.Connection,
                    limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve all results from database, most recent first.
    استرجاع جميع النتائج من قاعدة البيانات، الأحدث أولاً.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, filename, file_type, extracted_text, confidence,
               processing_time, language, created_at
        FROM ocr_results
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    return [
        {
            "id": r[0], "filename": r[1], "file_type": r[2],
            "text": r[3], "confidence": r[4], "time": r[5],
            "language": r[6], "created_at": r[7],
        }
        for r in rows
    ]


def clear_database(conn: sqlite3.Connection):
    """Clear all OCR results from database. مسح جميع النتائج."""
    conn.execute("DELETE FROM ocr_results")
    conn.commit()


# ---- PDF Processing / معالجة PDF ----

def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[np.ndarray]:
    """
    Convert PDF pages to OpenCV images using PyMuPDF.
    تحويل صفحات PDF إلى صور OpenCV باستخدام PyMuPDF.

    Args:
        pdf_bytes: Raw PDF file bytes / بايتات ملف PDF
        dpi: Resolution for rendering / دقة العرض

    Returns:
        List of BGR images / قائمة بالصور BGR

    Raises:
        ImportError: If PyMuPDF (fitz) is not installed
    """
    try:
        import fitz
    except ImportError:
        st.error(
            "PyMuPDF is required for PDF processing. "
            "Install it with: pip install PyMuPDF\n"
            "PyMuPDF مطلوب لمعالجة PDF. ثبته بـ: pip install PyMuPDF"
        )
        raise

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("png")
        img_array = np.frombuffer(img_data, np.uint8)
        img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img_bgr is not None:
            images.append(img_bgr)

    doc.close()
    return images


# ---- Image Preprocessing / معالجة الصور ----

def preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Preprocess image for better OCR accuracy.
    معالجة الصورة مسبقاً لتحسين دقة OCR.

    Steps:
    1. Convert to grayscale / تحويل إلى تدرج رمادي
    2. CLAHE enhancement / تحسين CLAHE
    3. Denoising / إزالة الضوضاء
    4. Binarization / تثنيت
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Denoising
    denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

    return denoised


# ---- OCR Engine / محرك OCR ----

@st.cache_resource(show_spinner="Loading OCR engine... جاري تحميل محرك OCR...")
def load_ocr_reader(use_gpu: bool = False):
    """
    Load EasyOCR reader with Arabic and English support.
    تحميل قارئ EasyOCR مع دعم العربية والإنجليزية.
    """
    try:
        import easyocr
    except ImportError:
        st.error(
            "EasyOCR is required. Install with: pip install easyocr\n"
            "EasyOCR مطلوب. ثبته بـ: pip install easyocr"
        )
        raise

    return easyocr.Reader(
        SUPPORTED_LANGUAGES,
        gpu=use_gpu,
        verbose=False,
        paragraph=True,
    )


def perform_ocr(reader, img: np.ndarray) -> Tuple[str, float]:
    """
    Perform OCR on a single image and return text with confidence.
    إجراء OCR على صورة واحدة وإرجاع النص مع درجة الثقة.

    Args:
        reader: EasyOCR Reader instance / كائن قارئ EasyOCR
        img: Input image / صورة مدخلة

    Returns:
        Tuple of (extracted_text, average_confidence)
        زوج من (النص المستخرج، متوسط الثقة)
    """
    try:
        processed = preprocess_image(img)
        results = reader.readtext(processed, detail=1, paragraph=True)

        if not results:
            return "", 0.0

        texts = []
        confidences = []
        for item in results:
            if isinstance(item, tuple) and len(item) >= 3:
                # Full detail result: (bbox, text, confidence)
                texts.append(item[1])
                confidences.append(item[2])
            elif isinstance(item, tuple) and len(item) == 2:
                # Paragraph mode result: (bbox, text)
                texts.append(item[1])

        full_text = "\n".join(texts)
        avg_conf = np.mean(confidences) if confidences else 0.0
        return full_text, float(avg_conf)

    except Exception as e:
        st.warning(f"OCR error on image / خطأ في OCR: {str(e)}")
        return f"[OCR Error: {str(e)}]", 0.0


# ---- Confidence Display / عرض الثقة ----

def get_confidence_class(confidence: float) -> str:
    """Return CSS class based on confidence level."""
    if confidence >= 0.7:
        return "confidence-high"
    elif confidence >= 0.4:
        return "confidence-medium"
    return "confidence-low"


def format_confidence(confidence: float) -> str:
    """Format confidence as percentage with color indicator."""
    pct = confidence * 100
    css_class = get_confidence_class(confidence)
    return f'<span class="{css_class}">{pct:.1f}%</span>'


# ---- File Validation / التحقق من الملفات ----

def validate_file(file) -> Tuple[bool, str]:
    """
    Validate uploaded file type and size.
    التحقق من نوع وحجم الملف المرفوع.

    Returns:
        (is_valid, error_message)
    """
    if file is None:
        return False, "No file provided / لم يتم تقديم ملف"

    ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, (
            f"Unsupported file type: .{ext}\n"
            f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}\n"
            f"نوع ملف غير مدعوم: .{ext}"
        )

    file.seek(0, os.SEEK_END)
    size_mb = file.tell() / (1024 * 1024)
    file.seek(0)

    if size_mb > MAX_FILE_SIZE_MB:
        return False, (
            f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)\n"
            f"ملف كبير جداً: {size_mb:.1f} ميغابايت (الحد الأقصى {MAX_FILE_SIZE_MB})"
        )

    return True, ""


# ---- Main Application / التطبيق الرئيسي ----

def main():
    """Main Streamlit application entry point."""

    # Initialize database / تهيئة قاعدة البيانات
    conn = init_database()

    # Sidebar / الشريط الجانبي
    with st.sidebar:
        st.title("🏥 OmniFile OCR")
        st.caption("Medical Arabic Handwriting / الكتابة الطبية العربية")

        st.divider()

        # Settings / الإعدادات
        st.subheader("⚙️ Settings / الإعدادات")
        use_gpu = st.checkbox(
            "Use GPU / استخدام GPU",
            value=False,
            help="Enable GPU acceleration for OCR"
        )
        confidence_threshold = st.slider(
            "Min Confidence / الحد الأدنى للثقة",
            min_value=0.0, max_value=1.0,
            value=0.3, step=0.05,
            help="Minimum confidence score to highlight results"
        )
        dpi_setting = st.slider(
            "PDF DPI / دقة PDF",
            min_value=100, max_value=400,
            value=200, step=50,
            help="Resolution for PDF page rendering"
        )

        st.divider()

        # Database actions / إجراءات قاعدة البيانات
        st.subheader("🗄️ Database / قاعدة البيانات")
        results = get_all_results(conn)
        st.metric("Total Results / النتائج الكلية", len(results))

        if st.button("🗑️ Clear All Results / مسح الكل", type="secondary"):
            clear_database(conn)
            st.success("Database cleared! / تم مسح قاعدة البيانات!")
            st.rerun()

        st.divider()

        # Export / تصدير
        st.subheader("📤 Export / تصدير")
        if st.button("Export Results as JSON"):
            results = get_all_results(conn, limit=1000)
            json_data = json.dumps(results, ensure_ascii=False, indent=2)
            st.download_button(
                label="Download JSON / تحميل",
                data=json_data,
                file_name=f"ocr_results_{datetime.now():%Y%m%d_%H%M%S}.json",
                mime="application/json",
            )

    # Main content area / منطقة المحتوى الرئيسية
    st.title("📋 Multi-File OCR Processing / معالجة ملفات متعددة")
    st.markdown(
        "Upload PDF, JPG, or PNG files for Arabic medical handwriting recognition.\n"
        "ارفع ملفات PDF أو JPG أو PNG للتعرف على الكتابة الطبية العربية."
    )

    # File uploader / رفع الملفات
    uploaded_files = st.file_uploader(
        "Upload Files / رفع الملفات",
        type=list(ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
        key="file_uploader",
        help=f"Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))} "
             f"(max {MAX_FILE_SIZE_MB}MB each)",
    )

    if not uploaded_files:
        st.info(
            "👆 Drop files here or click to browse.\n"
            "ضع الملفات هنا أو انقر للتصفح."
        )
        st.stop()

    # Validate all files / التحقق من جميع الملفات
    valid_files = []
    for f in uploaded_files:
        is_valid, error = validate_file(f)
        if is_valid:
            valid_files.append(f)
        else:
            st.warning(f"⚠️ Skipped {f.name}: {error}")

    if not valid_files:
        st.error("No valid files to process! / لا توجد ملفات صالحة للمعالجة!")
        st.stop()

    st.success(f"✅ {len(valid_files)} file(s) ready for processing / جاهز للمعالجة")

    # Process button / زر المعالجة
    if st.button(f"🚀 Process {len(valid_files)} File(s)", type="primary"):
        try:
            reader = load_ocr_reader(use_gpu=use_gpu)
        except ImportError:
            st.stop()

        # Progress bar / شريط التقدم
        progress_bar = st.progress(0, text="Starting... / جاري البدء...")
        status_text = st.empty()

        # Results container / حاوية النتائج
        results_container = st.container()

        total_files = len(valid_files)
        processed = 0
        all_results = []

        for idx, uploaded_file in enumerate(valid_files):
            start_time = time.time()
            ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
            status_text.markdown(
                f"Processing ({idx + 1}/{total_files}): **{uploaded_file.name}**"
            )

            try:
                file_bytes = uploaded_file.read()

                # Handle PDF files / معالجة ملفات PDF
                if ext == "pdf":
                    page_images = pdf_to_images(file_bytes, dpi=dpi_setting)
                    all_texts = []
                    all_confs = []

                    for page_idx, page_img in enumerate(page_images):
                        page_text, page_conf = perform_ocr(reader, page_img)
                        if page_text.strip():
                            all_texts.append(
                                f"--- Page {page_idx + 1} / صفحة {page_idx + 1} ---\n"
                                f"{page_text}"
                            )
                            all_confs.append(page_conf)

                    full_text = "\n\n".join(all_texts)
                    avg_conf = float(np.mean(all_confs)) if all_confs else 0.0
                    image_bytes = file_bytes[:500000]  # Store first 500KB for preview

                # Handle image files / معالجة ملفات الصور
                else:
                    img_array = np.frombuffer(file_bytes, np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                    if img is None:
                        raise ValueError("Failed to decode image / فشل في فك تشفير الصورة")

                    full_text, avg_conf = perform_ocr(reader, img)
                    image_bytes = file_bytes

                processing_time = time.time() - start_time

                # Save to database / الحفظ في قاعدة البيانات
                row_id = save_result(
                    conn=conn,
                    filename=uploaded_file.name,
                    file_type=ext.upper(),
                    image_bytes=image_bytes,
                    extracted_text=full_text,
                    confidence=avg_conf,
                    processing_time=processing_time,
                )

                result_entry = {
                    "id": row_id,
                    "filename": uploaded_file.name,
                    "file_type": ext.upper(),
                    "text": full_text,
                    "confidence": avg_conf,
                    "time": processing_time,
                }
                all_results.append(result_entry)

                # Display individual result / عرض النتيجة الفردية
                with results_container:
                    with st.expander(
                        f"📄 {uploaded_file.name} — "
                        f"{format_confidence(avg_conf)} — "
                        f"{processing_time:.1f}s",
                        expanded=(avg_conf < confidence_threshold),
                    ):
                        col1, col2 = st.columns([1, 2])

                        with col1:
                            if ext != "pdf":
                                st.image(
                                    cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                                    caption=f"Original / الأصل",
                                    use_container_width=True,
                                )
                            else:
                                st.info(
                                    f"PDF with {len(page_images)} page(s)\n"
                                    f"ملف PDF بـ {len(page_images)} صفحة"
                                )

                        with col2:
                            st.markdown("**Extracted Text / النص المستخرج:**")
                            if full_text.strip():
                                st.markdown(
                                    f'<div class="arabic-text">{full_text}</div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.warning(
                                    "No text extracted / لم يتم استخراج نص"
                                )

                            st.caption(
                                f"Time: {processing_time:.2f}s | "
                                f"Confidence: {avg_conf:.1%} | "
                                f"Chars: {len(full_text)}"
                            )

            except Exception as e:
                st.error(
                    f"Error processing {uploaded_file.name}: {str(e)}\n"
                    f"خطأ في معالجة {uploaded_file.name}"
                )
                all_results.append({
                    "filename": uploaded_file.name,
                    "text": f"[Error: {str(e)}]",
                    "confidence": 0.0,
                    "time": time.time() - start_time,
                })

            # Update progress / تحديث التقدم
            processed += 1
            progress = processed / total_files
            progress_bar.progress(
                progress,
                text=f"Processing {processed}/{total_files}... / معالجة {processed}/{total_files}..."
            )

        # Final summary / الملخص النهائي
        progress_bar.progress(1.0, text="✅ Complete! / اكتمل!")
        status_text.empty()

        avg_time = np.mean([r["time"] for r in all_results])
        avg_conf = np.mean([r["confidence"] for r in all_results
                           if r["confidence"] > 0])
        success_count = sum(1 for r in all_results
                           if not r["text"].startswith("[Error"))

        st.divider()
        st.subheader("📊 Batch Summary / ملخص الدفعة")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Files / ملفات", f"{success_count}/{total_files}")
        col2.metric("Avg Confidence / متوسط الثقة", f"{avg_conf:.1%}")
        col3.metric("Avg Time / متوسط الوقت", f"{avg_time:.2f}s")
        col4.metric("Errors / أخطاء", total_files - success_count)

    # History section / قسم السجل
    st.divider()
    with st.expander("📜 Processing History / سجل المعالجة"):
        history = get_all_results(conn, limit=50)
        if history:
            for entry in history:
                st.markdown(
                    f"- **{entry['filename']}** "
                    f"({entry['file_type']}) — "
                    f"{format_confidence(entry['confidence'])} — "
                    f"{entry['created_at']}"
                )
        else:
            st.info("No history yet / لا يوجد سجل بعد")

    conn.close()


if __name__ == "__main__":
    main()
