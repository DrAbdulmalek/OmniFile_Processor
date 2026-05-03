"""
تطبيق OmniFile AI Processor - واجهة المستخدم الرئيسية
=========================================================
تطبيق Streamlit متكامل يجمع بين جميع وحدات النظام:
1. وحدة معالجة الملفات (OCR + PDF)
2. وحدة المراجعة والتصحيح
3. وحدة الترجمة ومعالجة اللغة الطبيعية
4. وحدة تنظيم الملفات والحماية
5. لوحة القيادة والإحصائيات
6. الإعدادات والتهيئة

المؤلف: Dr Abdulmalek Tamer Al-husseini
الموقع: Homs, Syria
البريد الإلكتروني: Abdulmalek.husseini@gmail.com
الإصدار: 1.0.0
"""

import io
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import streamlit as st
import pandas as pd
import numpy as np

# === إعداد مسار المشروع ===
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# === استيراد وحدات المشروع ===
from config import OmniFileConfig
from database import OmniFileDB

# === إعداد التسجيل ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ===================================================================
#  ثوابت التطبيق
# ===================================================================

APP_TITLE = "🧠 OmniFile AI Processor"
APP_SUBTITLE = "نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص"
APP_ICON = "🧠"

# ألوان الواجهة
PRIMARY_COLOR = "#1E88E5"
SUCCESS_COLOR = "#43A047"
WARNING_COLOR = "#FB8C00"
DANGER_COLOR = "#E53935"
BG_COLOR = "#0E1117"
SIDEBAR_BG = "#1A1A2E"

# ===================================================================
#  دالات التهيئة
# ===================================================================


def init_config() -> OmniFileConfig:
    """تهيئة إعدادات المشروع بناءً على البيئة."""
    if "config" not in st.session_state:
        # كشف البيئة تلقائياً
        is_colab = False
        try:
            import google.colab
            is_colab = True
        except Exception:
            pass

        if is_colab:
            cfg = OmniFileConfig.from_colab_drive()
        else:
            cfg = OmniFileConfig.from_local(project_root=str(PROJECT_ROOT))

        cfg.setup_environment()
        st.session_state.config = cfg

    return st.session_state.config


def init_database(cfg: OmniFileConfig) -> OmniFileDB:
    """تهيئة قاعدة البيانات."""
    if "db" not in st.session_state:
        db_path = cfg.db_path
        db = OmniFileDB(db_path)
        db.create_tables()
        st.session_state.db = db
        logger.info("تم تهيئة قاعدة البيانات: %s", db_path)
    return st.session_state.db


def get_environment_info(cfg: OmniFileConfig) -> dict:
    """الحصول على معلومات البيئة الحالية."""
    is_colab = cfg.is_colab
    info = {
        "environment": "Google Colab ☁️" if is_colab else "محلي 💻",
        "project_root": str(cfg.root),
        "db_path": cfg.db_path,
        "gpu_available": False,
        "python_version": sys.version.split()[0],
    }

    # فحص GPU
    try:
        import torch
        info["gpu_available"] = torch.cuda.is_available()
        if info["gpu_available"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB"
    except ImportError:
        pass

    return info


# ===================================================================
#  التخزين المؤقت للنماذج (st.cache_resource)
# ===================================================================


@st.cache_resource(show_spinner="جارٍ تحميل النماذج...")
def load_ocr_engine(_cfg: OmniFileConfig):
    """تحميل محرك OCR مع التخزين المؤقت."""
    try:
        from modules.vision.ocr_engine import OCREngine
        engine = OCREngine(
            trocr_model_name=_cfg.trocr_model_name,
            easyocr_languages=_cfg.easyocr_languages,
            tesseract_langs=_cfg.tesseract_langs,
            dpi=_cfg.dpi,
            trocr_batch_size=_cfg.trocr_batch_size,
            num_beams=_cfg.num_beams,
            use_gpu=_cfg.use_gpu,
            easy_conf_threshold=_cfg.easy_conf_threshold,
            low_memory=_cfg.low_memory,
        )
        return engine
    except Exception as e:
        logger.error("فشل تحميل محرك OCR: %s", e)
        return None


@st.cache_resource(show_spinner="جارٍ تحميل نموذج الترجمة...")
def load_translator(_cfg: OmniFileConfig):
    """تحميل المترجم مع التخزين المؤقت."""
    try:
        from modules.nlp.translator import TechnicalTranslator
        device = "cuda" if _cfg.use_gpu else "cpu"
        translator = TechnicalTranslator(
            model_name=_cfg.translation_model,
            device=device,
        )
        return translator
    except Exception as e:
        logger.error("فشل تحميل المترجم: %s", e)
        return None


@st.cache_resource(show_spinner="جارٍ تحميل المصحح الإملائي...")
def load_spell_corrector():
    """تحميل المصحح الإملائي مع التخزين المؤقت."""
    try:
        from modules.nlp.spell_corrector import SpellCorrector
        corrector = SpellCorrector()
        return corrector
    except Exception as e:
        logger.error("فشل تحميل المصحح: %s", e)
        return None


@st.cache_resource(show_spinner="جارٍ تحميل مستخرج الكيانات...")
def load_entity_extractor(_cfg: OmniFileConfig):
    """تحميل مستخرج الكيانات المسماة مع التخزين المؤقت."""
    try:
        from modules.nlp.entity_extractor import EntityExtractor
        extractor = EntityExtractor()
        return extractor
    except Exception as e:
        logger.error("فشل تحميل مستخرج الكيانات: %s", e)
        return None


@st.cache_resource
def load_file_organizer():
    """تحميل منظم الملفات مع التخزين المؤقت."""
    try:
        from modules.security.file_organizer import FileOrganizer
        organizer = FileOrganizer(mode="copy", dry_run=True)
        return organizer
    except Exception as e:
        logger.error("فشل تحميل منظم الملفات: %s", e)
        return None


@st.cache_resource
def load_pdf_processor(_cfg: OmniFileConfig):
    """تحميل معالج PDF مع التخزين المؤقت."""
    try:
        from modules.vision.pdf_processor import PDFProcessor
        processor = PDFProcessor(dpi=_cfg.dpi)
        return processor
    except Exception as e:
        logger.error("فشل تحميل معالج PDF: %s", e)
        return None


# ===================================================================
#  نمط CSS مخصص
# ===================================================================


def get_custom_css() -> str:
    """إرجاع CSS مخصص لدعم RTL والعربية."""
    return f"""
    <style>
        /* دعم RTL */
        .stApp {{
            direction: rtl;
            text-align: right;
        }}

        /* لون الخلفية */
        .stApp {{
            background-color: {BG_COLOR};
        }}

        /* الشريط الجانبي */
        [data-testid="stSidebar"] {{
            background-color: {SIDEBAR_BG};
        }}

        /* العناوين */
        h1, h2, h3, h4, h5, h6 {{
            direction: rtl;
            text-align: right;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}

        /* الأزرار */
        .stButton > button {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border-radius: 8px;
            font-weight: bold;
        }}

        /* البيانات الوصفية */
        .stMetricLabel {{
            text-align: right;
            direction: rtl;
        }}

        /* الجداول */
        .stDataFrame {{
            direction: rtl;
            text-align: right;
        }}

        /* التبويبات */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 4px 4px 0 0;
            padding: 10px 20px;
            background-color: #1a1a2e;
            color: white;
        }}

        /* صناديق المعلومات */
        .info-box {{
            background-color: #1a1a2e;
            border-right: 4px solid {PRIMARY_COLOR};
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }}

        /* شريط التقدم */
        .stProgress > div > div > div {{
            background-color: {PRIMARY_COLOR};
        }}

        /* النجاح */
        .stSuccess {{
            background-color: {SUCCESS_COLOR}20;
            border-right: 4px solid {SUCCESS_COLOR};
        }}

        /* التحذير */
        .stWarning {{
            background-color: {WARNING_COLOR}20;
            border-right: 4px solid {WARNING_COLOR};
        }}
    </style>
    """


# ===================================================================
#  التبويب 1: معالجة الملفات
# ===================================================================


def render_file_processing_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض تبويب معالجة الملفات - رفع ومعالجة PDF والصور."""
    st.header("📄 معالجة الملفات", divider="blue")
    st.markdown("رفع ملفات PDF أو الصور واستخراج النصوص باستخدام محركات OCR المتعددة.")

    # خيارات الرفع
    col1, col2 = st.columns(2)

    with col1:
        uploaded_file = st.file_uploader(
            "📁 رفع ملف",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp", "webp"],
            help="يدعم ملفات PDF والصور المختلفة",
        )

    with col2:
        # رفع ملف من المسار المحلي (لبيئة Colab)
        file_path_input = st.text_input(
            "📂 أو أدخل مسار الملف (Colab/محلي)",
            placeholder="/content/drive/MyDrive/python notes.pdf",
        )

    source_file = None
    file_name = ""
    is_pdf = False

    if uploaded_file:
        source_file = uploaded_file
        file_name = uploaded_file.name
        is_pdf = file_name.lower().endswith(".pdf")
        st.success(f"✅ تم رفع: {file_name} ({uploaded_file.size / 1024:.1f} KB)")
    elif file_path_input:
        path = Path(file_path_input.strip())
        if path.exists():
            file_name = path.name
            is_pdf = file_name.lower().endswith(".pdf")
            source_file = path
            file_size = path.stat().st_size
            st.success(f"✅ تم العثور على: {file_name} ({file_size / 1024:.1f} KB)")
        else:
            st.error(f"❌ الملف غير موجود: {file_path_input}")

    if not source_file:
        st.info("💡 قم برفع ملف أو إدخال مساره لبدء المعالجة")
        return

    # إعدادات المعالجة
    with st.expander("⚙️ إعدادات المعالجة", expanded=False):
        ocr_engine_choice = st.selectbox(
            "محرك OCR",
            options=["تلقائي (الأفضل)", "EasyOCR", "TrOCR", "Tesseract"],
            help="اختر محرك التعرف على النصوص",
        )
        target_lang = st.selectbox(
            "لغة المستند",
            options=["ar", "en", "ar+en", "auto"],
            format_func=lambda x: {
                "ar": "العربية 🇸🇦",
                "en": "الإنجليزية 🇬🇧",
                "ar+en": "العربية + الإنجليزية",
                "auto": "تلقائي 🤖",
            }.get(x, x),
        )
        page_range = st.text_input(
            "نطاق الصفحات (للـ PDF)",
            placeholder="مثال: 0-5 أو 0,2,4 أو اتركه فارغاً للكل",
        )

    # زر المعالجة
    process_btn = st.button(
        "🚀 بدء المعالجة",
        type="primary",
        use_container_width=True,
    )

    if process_btn:
        start_time = time.time()

        with st.spinner(f"🔄 جارٍ معالجة {file_name}..."):
            try:
                # تسجيل العملية
                db.log_processing(
                    action="ocr_processing",
                    target=file_name,
                    status="started",
                )

                # تحميل محرك OCR
                ocr = load_ocr_engine(cfg)
                if ocr is None:
                    st.error("❌ فشل في تحميل محرك OCR")
                    return

                extracted_text = ""
                ocr_results_list = []
                page_count = 0

                if is_pdf:
                    # معالجة ملف PDF
                    pdf_proc = load_pdf_processor(cfg)

                    # تحليل نطاق الصفحات
                    pages = None
                    if page_range and page_range.strip():
                        try:
                            if "-" in page_range:
                                start_p, end_p = map(int, page_range.split("-"))
                                pages = list(range(start_p, end_p + 1))
                            elif "," in page_range:
                                pages = [int(p.strip()) for p in page_range.split(",")]
                            else:
                                pages = [int(page_range.strip())]
                        except ValueError:
                            st.warning("⚠️ صيغة نطاق الصفحات غير صحيحة، سيتم معالجة الكل")

                    # قراءة ملف PDF
                    if isinstance(source_file, Path):
                        pdf_bytes = source_file.read_bytes()
                    else:
                        pdf_bytes = source_file.read()

                    # الحصول على عدد الصفحات
                    page_count = pdf_proc.get_page_count(pdf_bytes)

                    # معالجة مع تتبع التقدم
                    progress_bar = st.progress(0, text="معالجة الصفحة 0 / 0")

                    def progress_cb(current, total, status):
                        progress_bar.progress(
                            current / max(total, 1),
                            text=f"{status} ({current}/{total})",
                        )

                    pdf_results = pdf_proc.process_pdf(
                        pdf_bytes,
                        pages=pages,
                        progress_callback=progress_cb,
                    )

                    progress_bar.progress(1.0, text="✅ اكتملت المعالجة!")

                    # تجميع النصوص
                    all_texts = []
                    for page_data in pdf_results:
                        text = page_data.get("text", "")
                        all_texts.append(text)
                        if text:
                            # حفظ نتائج OCR لكل صفحة
                            ocr_results_list.append({
                                "page_num": page_data["page_num"],
                                "word_text": text[:200],
                                "raw_text": text,
                                "confidence": 0.85,
                                "model_source": "pdf_extract",
                            })

                    extracted_text = "\n\n--- صفحة جديدة ---\n\n".join(all_texts)

                else:
                    # معالجة صورة
                    from PIL import Image

                    if isinstance(source_file, Path):
                        img = Image.open(source_file)
                    else:
                        img = Image.open(io.BytesIO(source_file.read()))

                    languages = None
                    if target_lang == "ar":
                        languages = ["ar"]
                    elif target_lang == "en":
                        languages = ["en"]

                    result = ocr.recognize(img, languages=languages)
                    extracted_text = result.get("text", "")
                    page_count = 1

                    ocr_results_list.append({
                        "page_num": 0,
                        "word_text": extracted_text[:200],
                        "raw_text": extracted_text,
                        "confidence": result.get("confidence", 0.0),
                        "model_source": result.get("source", "unknown"),
                    })

                # حساب مدة المعالجة
                duration = time.time() - start_time

                # حفظ في قاعدة البيانات
                doc_id = db.insert_document({
                    "file_name": file_name,
                    "file_type": "pdf" if is_pdf else "image",
                    "file_size": source_file.size if hasattr(source_file, 'size') else 0,
                    "page_count": page_count,
                    "raw_text": extracted_text,
                    "processed_text": extracted_text,
                    "category": "documents",
                    "language": target_lang,
                    "confidence": 0.85,
                    "source_type": "upload",
                })

                # حفظ نتائج OCR
                for ocr_r in ocr_results_list:
                    ocr_r["document_id"] = doc_id
                if ocr_results_list:
                    db.insert_ocr_results(ocr_results_list)

                # تسجيل الإنجاز
                db.log_processing(
                    action="ocr_processing",
                    target=file_name,
                    status="completed",
                    duration=duration,
                    details={
                        "pages": page_count,
                        "text_length": len(extracted_text),
                        "ocr_results": len(ocr_results_list),
                    },
                )

                # عرض النتائج
                st.success(f"🎉 تمت المعالجة بنجاح! ({duration:.1f} ثانية)")

                # حفظ في session_state
                st.session_state.current_doc_id = doc_id
                st.session_state.current_text = extracted_text
                st.session_state.current_file = file_name

            except Exception as e:
                duration = time.time() - start_time
                db.log_processing(
                    action="ocr_processing",
                    target=file_name,
                    status="failed",
                    duration=duration,
                    details={"error": str(e)},
                )
                st.error(f"❌ فشلت المعالجة: {e}")
                logger.error("فشلت معالجة الملف: %s", e, exc_info=True)
                return

        # عرض النتائج
        if "current_text" in st.session_state and st.session_state.current_text:
            st.subheader("📋 النص المستخرج")
            st.text_area(
                "النص الكامل",
                value=st.session_state.current_text,
                height=300,
                key="extracted_text_display",
            )

            # إجراءات سريعة
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("📝 انتقل للمراجعة"):
                    st.session_state.active_tab = 1
                    st.rerun()
            with col_b:
                if st.button("🌐 ترجم النص"):
                    st.session_state.active_tab = 2
                    st.rerun()
            with col_c:
                # تنزيل النص
                st.download_button(
                    "💾 تنزيل كنص",
                    data=st.session_state.current_text,
                    file_name=f"{file_name}.txt",
                    mime="text/plain",
                )


# ===================================================================
#  التبويب 2: المراجعة والتصحيح
# ===================================================================


def render_review_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض تبويب المراجعة والتصحيح."""
    st.header("📝 المراجعة والتصحيح", divider="green")
    st.markdown("مراجعة النصوص المستخرجة وتصحيح الأخطاء الإملائية والنحوية.")

    # اختيار المستند
    docs = db.get_unreviewed_documents()

    if not docs and "current_doc_id" not in st.session_state:
        st.info("📭 لا توجد مستندات تحتاج مراجعة حالياً.")
        st.markdown("👉 قم بمعالجة ملف من تبويب **معالجة الملفات** أولاً.")
        return

    # عرض قائمة المستندات غير المراجعة
    if docs:
        doc_options = {f"{d['file_name']} (id:{d['id']})": d for d in docs[:20]}
        selected_label = st.selectbox(
            "اختر مستند للمراجعة",
            options=list(doc_options.keys()),
            key="review_doc_select",
        )
        selected_doc = doc_options[selected_label]
        doc_id = selected_doc["id"]
    else:
        doc_id = st.session_state.current_doc_id
        selected_doc = db.get_document(doc_id)

    if not selected_doc:
        st.warning("⚠️ لم يتم العثور على المستند")
        return

    # عرض معلومات المستند
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 الملف", selected_doc.get("file_name", "-"))
    with col2:
        st.metric("📊 الثقة", f"{selected_doc.get('confidence', 0):.1%}")
    with col3:
        st.metric("📝 الصفحات", selected_doc.get("page_count", 0))
    with col4:
        st.metric("🌐 اللغة", selected_doc.get("language", "-"))

    # عرض النص الأصلي
    st.subheader("📄 النص الأصلي")
    raw_text = selected_doc.get("raw_text", "") or selected_doc.get("processed_text", "")
    edited_text = st.text_area(
        "حرّر النص هنا",
        value=raw_text,
        height=250,
        key="review_text_area",
    )

    # قسم التصحيح التلقائي
    st.subheader("🔧 التصحيح التلقائي")

    auto_col1, auto_col2 = st.columns(2)

    with auto_col1:
        if st.button("✨ تصحيح إملائي تلقائي", type="primary"):
            with st.spinner("جارٍ التصحيح الإملائي..."):
                try:
                    corrector = load_spell_corrector()
                    if corrector and edited_text:
                        # محاولة التصحيح
                        corrected = edited_text  # النص الافتراضي
                        try:
                            result = corrector.correct(edited_text)
                            if isinstance(result, dict):
                                corrected = result.get("corrected_text", edited_text)
                            elif isinstance(result, str):
                                corrected = result
                        except Exception:
                            pass

                        st.session_state.corrected_text = corrected
                        st.success("✅ تم التصحيح الإملائي")
                except Exception as e:
                    st.error(f"فشل التصحيح: {e}")

    with auto_col2:
        if st.button("🔄 تصحيح باستخدام ar-corrector"):
            with st.spinner("جارٍ التصحيح بـ ar-corrector..."):
                try:
                    import ar_corrector
                    corrector = ar_corrector.corrector()
                    corrected = corrector.correct(edited_text)
                    st.session_state.corrected_text = corrected
                    st.success("✅ تم التصحيح بـ ar-corrector")
                except ImportError:
                    st.warning("⚠️ ar-corrector غير مثبت. قم بتثبيته: pip install ar-corrector")
                except Exception as e:
                    st.error(f"فشل: {e}")

    # عرض النص المصحح
    if "corrected_text" in st.session_state:
        st.subheader("✅ النص المصحح")
        st.text_area(
            "النص بعد التصحيح",
            value=st.session_state.corrected_text,
            height=200,
            key="corrected_display",
        )

        # مقارنة
        if edited_text != st.session_state.corrected_text:
            col_diff1, col_diff2 = st.columns(2)
            with col_diff1:
                st.markdown("**الأصلي:**")
                st.code(edited_text[:500], language=None)
            with col_diff2:
                st.markdown("**بعد التصحيح:**")
                st.code(st.session_state.corrected_text[:500], language=None)

    # حفظ التعديلات
    st.subheader("💾 حفظ التعديلات")

    final_text = st.session_state.get("corrected_text", edited_text)

    save_col1, save_col2 = st.columns(2)

    with save_col1:
        if st.button("💾 حفظ النص المصحح", type="primary"):
            updates = {
                "processed_text": final_text,
                "corrected_text": final_text,
                "is_reviewed": True,
            }
            if db.update_document(doc_id, updates):
                # تسجيل التصحيح
                if raw_text != final_text:
                    db.log_correction(
                        doc_id=doc_id,
                        original=raw_text[:500],
                        corrected=final_text[:500],
                        correction_type="manual",
                        auto_or_manual="manual",
                    )
                st.success("✅ تم حفظ التعديلات بنجاح!")
                st.balloons()
            else:
                st.error("❌ فشل في حفظ التعديلات")

    with save_col2:
        if st.button("⏭️ تخطي المراجعة"):
            if db.update_document(doc_id, {"is_reviewed": True}):
                st.success("✅ تم تمييز المستند كمراجع")
                st.rerun()


# ===================================================================
#  التبويب 3: الترجمة ومعالجة اللغة الطبيعية
# ===================================================================


def render_nlp_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض تبويب الترجمة ومعالجة اللغة الطبيعية."""
    st.header("🌐 الترجمة ومعالجة اللغة الطبيعية", divider="violet")
    st.markdown("ترجمة النصوص التقنية واستخراج الكيانات وتصنيف المحتوى.")

    # النص المصدر
    source_text = ""
    if "current_text" in st.session_state and st.session_state.current_text:
        source_text = st.session_state.current_text

    text_input = st.text_area(
        "📝 أدخل أو الصق النص المراد معالجته",
        value=source_text,
        height=200,
        key="nlp_text_input",
        placeholder="أدخل النص هنا...",
    )

    # اختيار العملية
    operation = st.selectbox(
        "اختر العملية",
        options=[
            "ترجمة EN→AR",
            "استخراج الكيانات المسماة (NER)",
            "تصنيف النص",
            "كشف اللغة",
            "جميع العمليات",
        ],
    )

    target_lang = "ar"
    if operation == "ترجمة EN→AR":
        target_lang = st.selectbox(
            "لغة الهدف",
            options=["ar", "en", "fr", "de", "tr"],
            format_func=lambda x: {
                "ar": "العربية 🇸🇦",
                "en": "الإنجليزية 🇬🇧",
                "fr": "الفرنسية 🇫🇷",
                "de": "الألمانية 🇩🇪",
                "tr": "التركية 🇹🇷",
            }.get(x, x),
        )

    # زر التنفيذ
    if st.button("🚀 تنفيذ", type="primary", use_container_width=True):
        if not text_input.strip():
            st.warning("⚠️ أدخل نصاً أولاً")
            return

        doc_id = st.session_state.get("current_doc_id")

        # === الترجمة ===
        if operation in ("ترجمة EN→AR", "جميع العمليات"):
            with st.spinner("🔄 جارٍ الترجمة..."):
                start_time = time.time()
                try:
                    translator = load_translator(cfg)
                    if translator:
                        result = translator.translate_text(
                            text_input,
                            source="en",
                            target=target_lang,
                        )
                        duration = time.time() - start_time

                        st.subheader("📝 النص المترجم")
                        translated = result.get("translated_text", "")
                        st.text_area("الترجمة", value=translated, height=200, key="translation_result")

                        # حفظ في قاعدة البيانات
                        if doc_id:
                            db.insert_translation(
                                doc_id=doc_id,
                                source=text_input[:1000],
                                translated=translated[:1000],
                                source_lang="en",
                                target_lang=target_lang,
                                model_name=translator.model_name,
                            )
                            db.log_processing(
                                action="translation",
                                target=f"doc:{doc_id}",
                                status="completed",
                                duration=duration,
                            )

                        st.success(f"✅ تمت الترجمة ({duration:.1f} ثانية) - الطريقة: {result.get('method', 'N/A')}")

                        # تنزيل
                        st.download_button(
                            "💾 تنزيل الترجمة",
                            data=translated,
                            file_name="translation.txt",
                            mime="text/plain",
                        )
                    else:
                        st.warning("⚠️ لم يتم تحميل المترجم")
                except Exception as e:
                    st.error(f"❌ فشلت الترجمة: {e}")

        # === استخراج الكيانات ===
        if operation in ("استخراج الكيانات المسماة (NER)", "جميع العمليات"):
            with st.spinner("🔄 جارٍ استخراج الكيانات..."):
                try:
                    extractor = load_entity_extractor(cfg)
                    if extractor:
                        entities = []
                        try:
                            result = extractor.extract(text_input)
                            if isinstance(result, dict):
                                entities = result.get("entities", [])
                            elif isinstance(result, list):
                                entities = result
                        except Exception:
                            pass

                        if entities:
                            st.subheader("🏷️ الكيانات المسماة")
                            ent_df = pd.DataFrame(entities)
                            st.dataframe(ent_df, use_container_width=True, hide_index=True)

                            # حفظ في قاعدة البيانات
                            if doc_id:
                                db.insert_entities(doc_id, entities)

                            # رسم بياني
                            if not ent_df.empty:
                                st.subheader("📊 توزيع الكيانات")
                                type_col = None
                                for col_name in ent_df.columns:
                                    if "type" in col_name.lower():
                                        type_col = col_name
                                        break
                                if type_col:
                                    st.bar_chart(
                                        ent_df[type_col].value_counts().head(10)
                                    )
                        else:
                            st.info("لم يتم العثور على كيانات مسماة")
                    else:
                        st.info("المستخرج غير متاح - استخدم النص لتجربة")
                except Exception as e:
                    st.warning(f"⚠️ فشل استخراج الكيانات: {e}")

        # === كشف اللغة ===
        if operation in ("كشف اللغة", "جميع العمليات"):
            with st.spinner("🔄 جارٍ كشف اللغة..."):
                try:
                    from langdetect import detect, detect_langs

                    lang = detect(text_input)
                    probabilities = detect_langs(text_input)
                    st.subheader("🌍 نتيجة كشف اللغة")
                    lang_map = {
                        "ar": "العربية", "en": "الإنجليزية", "fr": "الفرنسية",
                        "de": "الألمانية", "tr": "التركية", "ur": "الأردية",
                        "fa": "الفارسية", "he": "العبرية", "es": "الإسبانية",
                    }
                    st.metric(
                        "اللغة الأساسية",
                        lang_map.get(lang, lang),
                    )
                    st.write("**الاحتمالات:**")
                    for prob in probabilities:
                        lang_name = lang_map.get(prob.lang, prob.lang)
                        st.write(f"  {lang_name}: {prob.prob:.1%}")
                except Exception as e:
                    st.warning(f"⚠️ فشل كشف اللغة: {e}")


# ===================================================================
#  التبويب 4: تنظيم الملفات والحماية
# ===================================================================


def render_organizer_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض تبويب تنظيم الملفات والحماية."""
    st.header("🗂️ تنظيم الملفات والحماية", divider="orange")
    st.markdown("تنظيم الملفات تلقائياً وفحص سلامتها وحماية الأكواد البرمجية.")

    # === قسم تنظيم الملفات ===
    st.subheader("📁 تنظيم الملفات التلقائي")

    col1, col2 = st.columns(2)
    with col1:
        source_dir = st.text_input(
            "📂 مجلد المصدر",
            placeholder="/path/to/messy/folder",
            key="org_source",
        )
    with col2:
        target_dir = st.text_input(
            "📂 مجلد الهدف",
            placeholder="/path/to/organized",
            key="org_target",
        )

    org_mode = st.radio(
        "وضع التنظيم",
        options=["محاكاة فقط (عرض التقرير)", "نقل الملفات", "نسخ الملفات"],
        horizontal=True,
    )

    if st.button("🗂️ بدء التنظيم", use_container_width=True):
        if not source_dir or not target_dir:
            st.warning("⚠️ أدخل مجلد المصدر والهدف")
            return

        with st.spinner("🔄 جارٍ تحليل الملفات..."):
            try:
                from modules.security.file_organizer import FileOrganizer

                dry_run = org_mode == "محاكاة فقط (عرض التقرير)"
                mode = "copy" if org_mode == "نسخ الملفات" else "move"

                organizer = FileOrganizer(mode=mode, dry_run=dry_run)
                report = organizer.organize_directory(source_dir, target_dir)
                stats = report.get("stats", {})

                # عرض النتائج
                st.success(f"✅ اكتمل التنظيم!")
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    st.metric("إجمالي الملفات", stats.get("total_files", 0))
                with col_s2:
                    st.metric("تمت المعالجة", stats.get("processed", 0))
                with col_s3:
                    st.metric("تم تخطيه", stats.get("skipped", 0))

                # توزيع الفئات
                categories = stats.get("categories", {})
                if categories:
                    st.subheader("📊 توزيع الفئات")
                    cat_df = pd.DataFrame(
                        list(categories.items()),
                        columns=["الفئة", "العدد"],
                    )
                    st.dataframe(cat_df, use_container_width=True, hide_index=True)

                    # رسم بياني
                    st.bar_chart(cat_df.set_index("الفئة"))

                # تسجيل العملية
                db.log_processing(
                    action="file_organization",
                    target=source_dir,
                    status="completed",
                    details=stats,
                )

            except Exception as e:
                db.log_processing(
                    action="file_organization",
                    target=source_dir,
                    status="failed",
                    details={"error": str(e)},
                )
                st.error(f"❌ فشل التنظيم: {e}")

    st.divider()

    # === قسم فحص الأمان ===
    st.subheader("🔒 فحص الأمان والحماية")

    scan_path = st.text_input(
        "🔍 مسار المجلد للفحص",
        placeholder="/path/to/scan",
        key="security_scan_path",
    )

    if st.button("🔍 فحص الأمان", use_container_width=True):
        if not scan_path:
            st.warning("⚠️ أدخل مسار المجلد")
            return

        with st.spinner("🔄 جارٍ فحص الملفات..."):
            try:
                from modules.security.file_scanner import FileScanner

                scanner = FileScanner()
                scan_results = scanner.scan_directory(scan_path)

                st.subheader("📊 نتائج الفحص")
                st.json(scan_results)

                db.log_processing(
                    action="security_scan",
                    target=scan_path,
                    status="completed",
                    details=scan_results,
                )

            except Exception as e:
                st.warning(f"⚠️ فشل الفحص: {e}")


# ===================================================================
#  التبويب 5: لوحة القيادة
# ===================================================================


def render_dashboard_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض لوحة القيادة والإحصائيات."""
    st.header("📊 لوحة القيادة", divider="rainbow")
    st.markdown("نظرة شاملة على إحصائيات المشروع وسجل المعالجة.")

    # جلب الإحصائيات
    with st.spinner("🔄 جارٍ تحميل الإحصائيات..."):
        stats = db.get_stats()

    # === مقاييس رئيسية ===
    st.subheader("📈 المقاييس الرئيسية")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 المستندات", stats.get("total_documents", 0))
    with col2:
        st.metric("✅ المراجعة", stats.get("reviewed_documents", 0))
    with col3:
        st.metric("📝 بانتظار المراجعة", stats.get("unreviewed_documents", 0))
    with col4:
        st.metric("📊 متوسط الثقة", f"{stats.get('avg_confidence', 0):.1%}")

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("🔍 نتائج OCR", stats.get("total_ocr_results", 0))
    with col6:
        st.metric("🌐 الترجمات", stats.get("total_translations", 0))
    with col7:
        st.metric("🏷️ الكيانات", stats.get("total_entities", 0))
    with col8:
        st.metric("💾 حجم DB", f"{stats.get('db_size_mb', 0):.1f} MB")

    # === الرسوم البيانية ===
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📊 المستندات حسب النوع")
        by_type = stats.get("documents_by_type", {})
        if by_type:
            type_df = pd.DataFrame(
                list(by_type.items()),
                columns=["النوع", "العدد"],
            )
            st.bar_chart(type_df.set_index("النوع"))
        else:
            st.info("لا توجد بيانات بعد")

    with chart_col2:
        st.subheader("📂 المستندات حسب التصنيف")
        by_cat = stats.get("documents_by_category", {})
        if by_cat:
            cat_df = pd.DataFrame(
                list(by_cat.items()),
                columns=["التصنيف", "العدد"],
            )
            st.bar_chart(cat_df.set_index("التصنيف"))
        else:
            st.info("لا توجد بيانات بعد")

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("🌍 المستندات حسب اللغة")
        by_lang = stats.get("documents_by_language", {})
        if by_lang:
            lang_df = pd.DataFrame(
                list(by_lang.items()),
                columns=["اللغة", "العدد"],
            )
            st.bar_chart(lang_df.set_index("اللغة"))
        else:
            st.info("لا توجد بيانات بعد")

    with chart_col4:
        st.subheader("⚙️ العمليات حسب النوع")
        by_action = stats.get("processing_by_action", {})
        if by_action:
            action_df = pd.DataFrame(
                list(by_action.items()),
                columns=["العملية", "العدد"],
            )
            st.bar_chart(action_df.set_index("العملية"))
        else:
            st.info("لا توجد بيانات بعد")

    # === سجل المعالجة ===
    st.subheader("📜 سجل المعالجة الأخيرة")
    history = db.get_processing_history(limit=20)

    if history:
        hist_data = []
        for h in history:
            hist_data.append({
                "العملية": h.get("action", ""),
                "الهدف": h.get("target", ""),
                "الحالة": "✅" if h.get("status") == "completed" else "❌" if h.get("status") == "failed" else "⏳",
                "المدة (ث)": f"{h.get('duration_sec', 0):.1f}",
                "التاريخ": h.get("created_at", ""),
            })
        hist_df = pd.DataFrame(hist_data)
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد سجلات معالجة بعد")

    # === أحدث المستندات ===
    st.subheader("📄 أحدث المستندات")
    recent_docs = db.get_all_documents(limit=10)
    if recent_docs:
        docs_data = []
        for d in recent_docs:
            docs_data.append({
                "المعرّف": d["id"],
                "الملف": d.get("file_name", ""),
                "النوع": d.get("file_type", ""),
                "الثقة": f"{d.get('confidence', 0):.1%}",
                "المراجعة": "✅" if d.get("is_reviewed") else "⏳",
                "التاريخ": d.get("created_at", ""),
            })
        docs_df = pd.DataFrame(docs_data)
        st.dataframe(docs_df, use_container_width=True, hide_index=True)

    # === تصدير ===
    st.divider()
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        if st.button("📦 تصدير البيانات كـ JSON"):
            export_path = str(cfg.exports_dir / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            try:
                path = db.export_to_json(export_path)
                st.success(f"✅ تم التصدير إلى: {path}")
            except Exception as e:
                st.error(f"❌ فشل التصدير: {e}")

    with export_col2:
        if st.button("🔄 تنظيف السجلات القديمة (30 يوم)"):
            result = db.cleanup_old_records(days=30)
            st.success(
                f"✅ تم التنظيف: {result['deleted_processing']} معالجة, "
                f"{result['deleted_corrections']} تصحيح"
            )


# ===================================================================
#  التبويب 6: الإعدادات
# ===================================================================


def render_settings_tab(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض تبويب الإعدادات والتهيئة."""
    st.header("⚙️ الإعدادات", divider="gray")
    st.markdown("إعدادات المشروع والاتصال والنسخ الاحتياطي.")

    # === إعدادات عامة ===
    st.subheader("🔧 الإعدادات العامة")

    with st.form("settings_form"):
        st.write("**🤖 نماذج AI**")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            cfg.trocr_model_name = st.text_input(
                "نموذج TrOCR",
                value=cfg.trocr_model_name,
                key="set_trocr",
            )
        with col_m2:
            cfg.translation_model = st.text_input(
                "نموذج الترجمة",
                value=cfg.translation_model,
                key="set_translation",
            )

        st.write("**📐 إعدادات المعالجة**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            cfg.dpi = st.number_input(
                "DPI",
                min_value=72,
                max_value=600,
                value=cfg.dpi,
                key="set_dpi",
            )
        with col_p2:
            cfg.trocr_batch_size = st.number_input(
                "حجم الدفعة",
                min_value=1,
                max_value=32,
                value=cfg.trocr_batch_size,
                key="set_batch",
            )
        with col_p3:
            cfg.easy_conf_threshold = st.slider(
                "حد ثقة OCR",
                min_value=0.0,
                max_value=1.0,
                value=cfg.easy_conf_threshold,
                key="set_conf",
            )

        st.write("**🖥️ بيئة التشغيل**")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            cfg.use_gpu = st.checkbox(
                "استخدام GPU",
                value=cfg.use_gpu,
                key="set_gpu",
            )
        with col_e2:
            cfg.share_public = st.checkbox(
                "مشاركة عامة (pyngrok)",
                value=cfg.share_public,
                key="set_share",
            )

        if st.form_submit_button("💾 حفظ الإعدادات", type="primary"):
            cfg.save()
            st.success("✅ تم حفظ الإعدادات")

    st.divider()

    # === اتصال GitHub ===
    st.subheader("🐙 اتصال GitHub")

    gh_col1, gh_col2 = st.columns(2)
    with gh_col1:
        cfg.github_token = st.text_input(
            "GitHub Token",
            value=cfg.github_token,
            type="password",
            key="set_gh_token",
        )
        cfg.github_repo = st.text_input(
            "المستودع",
            value=cfg.github_repo,
            key="set_gh_repo",
        )
    with gh_col2:
        cfg.github_username = st.text_input(
            "اسم المستخدم",
            value=cfg.github_username,
            key="set_gh_user",
        )
        cfg.github_email = st.text_input(
            "البريد الإلكتروني",
            value=cfg.github_email,
            key="set_gh_email",
        )

    if st.button("🔗 اختبار الاتصال بـ GitHub"):
        try:
            import requests
            if cfg.github_token:
                resp = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {cfg.github_token}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    user = resp.json()
                    st.success(f"✅ متصل بـ GitHub: {user.get('login', 'N/A')}")
                else:
                    st.error(f"❌ فشل الاتصال: {resp.status_code}")
            else:
                st.warning("⚠️ أدخل GitHub Token أولاً")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")

    st.divider()

    # === اتصال HuggingFace ===
    st.subheader("🤗 اتصال HuggingFace")

    hf_col1, hf_col2 = st.columns(2)
    with hf_col1:
        cfg.hf_token = st.text_input(
            "HuggingFace Token",
            value=cfg.hf_token,
            type="password",
            key="set_hf_token",
        )
    with hf_col2:
        cfg.hf_username = st.text_input(
            "اسم المستخدم HF",
            value=cfg.hf_username,
            key="set_hf_user",
        )

    if st.button("🔗 اختبار الاتصال بـ HuggingFace"):
        try:
            from huggingface_hub import HfFolder, whoami
            if cfg.hf_token:
                HfFolder.save_token(cfg.hf_token)
                user_info = whoami()
                st.success(f"✅ متصل بـ HuggingFace: {user_info.get('name', 'N/A')}")
            else:
                st.warning("⚠️ أدخل HuggingFace Token أولاً")
        except ImportError:
            st.warning("⚠️ huggingface_hub غير مثبت")
        except Exception as e:
            st.error(f"❌ خطأ: {e}")

    st.divider()

    # === النسخ الاحتياطي ===
    st.subheader("💾 النسخ الاحتياطي")

    backup_col1, backup_col2, backup_col3 = st.columns(3)
    with backup_col1:
        if st.button("💾 نسخ احتياطي للـ DB"):
            try:
                backup_path = db.backup_database()
                st.success(f"✅ تم النسخ: {backup_path}")
            except Exception as e:
                st.error(f"❌ فشل: {e}")

    with backup_col2:
        if st.button("📦 تصدير كامل JSON"):
            try:
                export_path = str(
                    cfg.exports_dir / f"full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                path = db.export_to_json(export_path)
                st.success(f"✅ تم التصدير: {path}")
            except Exception as e:
                st.error(f"❌ فشل: {e}")

    with backup_col3:
        if st.button("🧹 ضغط قاعدة البيانات"):
            try:
                db.vacuum()
                st.success("✅ تم الضغط")
            except Exception as e:
                st.error(f"❌ فشل: {e}")

    # === معلومات النظام ===
    st.divider()
    st.subheader("ℹ️ معلومات النظام")

    env_info = get_environment_info(cfg)
    info_cols = st.columns(3)
    with info_cols[0]:
        st.write(f"**البيئة:** {env_info['environment']}")
        st.write(f"**Python:** {env_info['python_version']}")
    with info_cols[1]:
        st.write(f"**GPU:** {'✅ ' + env_info.get('gpu_name', 'متاح') if env_info['gpu_available'] else '❌ غير متاح'}")
        if env_info.get("gpu_memory"):
            st.write(f"**ذاكرة GPU:** {env_info['gpu_memory']}")
    with info_cols[2]:
        st.write(f"**مسار المشروع:** `{env_info['project_root']}`")
        st.write(f"**حجم DB:** {db.get_db_size()}")


# ===================================================================
#  الشريط الجانبي
# ===================================================================


def render_sidebar(cfg: OmniFileConfig, db: OmniFileDB):
    """عرض الشريط الجانبي."""
    with st.sidebar:
        # العنوان
        st.markdown(f"## {APP_TITLE}")
        st.markdown("---")

        # معلومات البيئة
        env_info = get_environment_info(cfg)
        st.markdown(f"**البيئة:** {env_info['environment']}")

        if env_info["gpu_available"]:
            st.success(f"🟢 GPU: {env_info.get('gpu_name', 'متاح')}")
        else:
            st.warning("🟡 GPU: غير متاح")

        st.markdown("---")

        # إحصائيات سريعة
        st.markdown("### 📊 إحصائيات سريعة")
        try:
            stats = db.get_stats()
            st.metric("📄 المستندات", stats.get("total_documents", 0))
            st.metric("⏳ بانتظار المراجعة", stats.get("unreviewed_documents", 0))
            st.metric("💾 حجم DB", f"{stats.get('db_size_mb', 0):.1f} MB")
        except Exception as e:
            st.error(f"خطأ في الإحصائيات: {e}")

        st.markdown("---")

        # إجراءات سريعة
        st.markdown("### ⚡ إجراءات سريعة")

        if st.button("🔄 تحديث الإحصائيات", use_container_width=True):
            st.rerun()

        if st.button("🧹 تنظيف السجلات القديمة", use_container_width=True):
            result = db.cleanup_old_records(days=30)
            st.success(
                f"تم التنظيف: {result['deleted_processing']} معالجة"
            )

        st.markdown("---")

        # معلومات المشروع
        st.markdown("### ℹ️ المشروع")
        st.markdown(f"**الإصدار:** v1.0.0")
        st.markdown(f"**المؤلف:** Dr Abdulmalek Tamer Al-husseini")
        st.markdown(f"**الموقع:** Homs, Syria")
        st.markdown(f"**البريد الإلكتروني:** [Abdulmalek.husseini@gmail.com](mailto:Abdulmalek.husseini@gmail.com)")
        st.markdown(f"**الرخصة:** MIT")

        # محركات OCR
        st.markdown("---")
        st.markdown("### 🔍 محركات OCR")
        try:
            ocr = load_ocr_engine(cfg)
            if ocr:
                engines = ocr.get_available_engines()
                for eng in engines:
                    status = "🟢" if eng.get("available") and eng.get("enabled") else "🔴"
                    loaded = " (مُحمّل)" if eng.get("loaded") else ""
                    st.markdown(f"{status} {eng['name']}{loaded}")
            else:
                st.markdown("⚠️ لم يتم تحميل المحركات")
        except Exception:
            st.markdown("⚠️ غير متاح")


# ===================================================================
#  التطبيق الرئيسي
# ===================================================================


def main():
    """دالة التطبيق الرئيسية."""
    # === إعداد الصفحة ===
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS مخصص
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # === العنوان الرئيسي ===
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)

    # === تهيئة ===
    cfg = init_config()
    db = init_database(cfg)

    # === الشريط الجانبي ===
    render_sidebar(cfg, db)

    # === التبويبات الرئيسية ===
    # تحديد التبويب النشط
    active_tab_idx = st.session_state.get("active_tab", 0)

    tabs = st.tabs([
        "📄 معالجة الملفات",
        "📝 المراجعة والتصحيح",
        "🌐 الترجمة والنLP",
        "🗂️ تنظيم الملفات",
        "📊 لوحة القيادة",
        "⚙️ الإعدادات",
    ])

    # معالجة التبويبات
    with tabs[0]:
        render_file_processing_tab(cfg, db)

    with tabs[1]:
        render_review_tab(cfg, db)

    with tabs[2]:
        render_nlp_tab(cfg, db)

    with tabs[3]:
        render_organizer_tab(cfg, db)

    with tabs[4]:
        render_dashboard_tab(cfg, db)

    with tabs[5]:
        render_settings_tab(cfg, db)

    # === تذييل الصفحة ===
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "🧠 OmniFile AI Processor v1.0 | Dr Abdulmalek Tamer Al-husseini | Homs, Syria | MIT License"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
