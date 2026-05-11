# ╔══════════════════════════════════════════════════════════════════════╗
# ║  OmniFile Medical OCR Reviewer — Colab Edition v2.0                  ║
# ║  معالجة الملاحظات الطبية بخط اليد + مراجعة تفاعلية + تصدير        ║
# ║                                                                      ║
# ║  الاستخدام:                                                          ║
# ║    1. شغّل Cell 1 (التثبيت)                                         ║
# ║    2. شغّل Cell 2 (التهيئة)                                         ║
# ║    3. شغّل Cell 3 (واجهة Gradio)                                    ║
# ║    4. ارفع صور الملاحظات الطبية وراجع النتائج                      ║
# ║                                                                      ║
# ║  المؤلف: Dr. Abdulmalek Tamer Al-husseini                           ║
# ║  الرخصة: MIT                                                        ║
# ╚══════════════════════════════════════════════════════════════════════╝

# =============================================================================
# Cell 1: تثبيت الاعتماديات
# =============================================================================
# في Google Colab، أزل التعليق من السطر التالي وابدأ:
#
# # !pip install -q easyocr opencv-python-headless gradio PyPDF2 Pillow \
# #     arabic-reshaper python-bidi pytesseract paddleocr
#
# ─────────────────────────────────────────────────────────────────────────────
# ملاحظة: إذا كنت تعمل محليًا، ثبّت مسبقًا:
#   pip install -r requirements-colab.txt
# ─────────────────────────────────────────────────────────────────────────────

import sys
import subprocess

def _ensure_dependencies():
    """التحقق من تثبيت الحزم الأساسية وتثبيتها إذا لزم الأمر."""
    required = {
        "opencv-python-headless": "cv2",
        "numpy": "numpy",
        "Pillow": "PIL",
        "easyocr": "easyocr",
        "arabic-reshaper": "arabic_reshaper",
        "python-bidi": "bidi",
        "gradio": "gradio",
    }
    missing = []
    for pkg, module in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"📦 جاري تثبيت الحزم المفقودة: {missing}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q"] + missing
        )
        print("✅ تمّ التثبيت بنجاح!")
    else:
        print("✅ جميع الحزم مثبتة مسبقًا.")

_ensure_dependencies()

# =============================================================================
# Cell 2: الاستيرادات والتهيئة
# =============================================================================
"""
هذا الخلية يحاول استيراد الوحدات من المشروع الكامل.
إذا لم يتوفّر المشروع (مثل في Colab)، يُستخدم البديل المضمّن.
"""

import cv2
import numpy as np
import os
import re
import json
import zipfile
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

import gradio as gr

# ── إعداد التسجيل (Logging) ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MedicalOCR_Colab")

# ── محاولة الاستيراد من المشروع، أو البديل المضمّن ──
_PROJECT_AVAILABLE = False
try:
    from modules.medical.medical_ocr_reviewer import AdvancedMedicalOCR
    _PROJECT_AVAILABLE = True
    logger.info("✅ تمّ الاستيراد من المشروع: modules.medical.medical_ocr_reviewer")
except ImportError:
    logger.info("ℹ️ المشروع غير متوفّر. سيُستخدم البديل المضمّن (standalone mode).")


# =============================================================================
# المصطلحات الطبية المحمية
# =============================================================================
MEDICAL_TERMS_AR = {
    # أدوية شائعة
    "بايريكسامول", "أموكسيسيلين", "ميتفورمين", "أنسولين", "أسبرين",
    "أوميبرازول", "ليزينوبريل", "آتورفاستاتين", "سيمفاستاتين",
    "أسيكلوفير", "أموكسيسيللاف", "أزيثرومايسين", "سيتالوبرام",
    "فلوكسيتين", "لوراتادين", "سالبوتامول", "بيوثيسونيد",
    # أسماء إنجليزية
    "paracetamol", "ibuprofen", "amoxicillin", "metformin",
    "insulin", "aspirin", "omeprazole", "lisinopril",
    "atorvastatin", "simvastatin", "acyclovir", "azithromycin",
    # تشخيصات
    "السكري", "ارتفاع الضغط", "الربو", "اضطراب نظم القلب",
    "diabetes", "hypertension", "asthma", "arrhythmia",
    "التهاب المفاصل", "التهاب الجيوب", "التهاب الشعب",
    # فحوصات
    "صورة دم كاملة", "تخطيط قلب", "أشعة سينية",
    "CBC", "ESR", "HbA1c", "ECG", "X-ray", "MRI", "CT scan",
    "TSH", "T3", "T4", "CRP", "WBC", "RBC",
}


# =============================================================================
# الفئة البديلة — AdvancedMedicalOCR (Standalone)
# =============================================================================
class AdvancedMedicalOCR:
    """معالج الملاحظات الطبية بخط اليد — نسخة مستقلة لـ Colab.

    توفر هذه الفئة نفس الوظائف المتوفرة في المشروع الكامل لكنها
    تعمل بدون أي اعتماديات خارجية (ما عدا easyocr و opencv).

    الميزات:
        - التعرف على الخط اليدوي العربي (EasyOCR)
        - كشف المصطلحات الطبية وحمايتها
        - تصحيح إملائي ذكي مع حفظ المصطلحات
        - حفظ التصحيحات محليًا
        - تصدير بصيغ متعددة (TXT, JSON, ZIP)
    """

    def __init__(
        self,
        protect_terminology: bool = True,
        language: str = "ar",
        device: str = "cuda",
    ):
        """تهيئة معالج الملاحظات الطبية.

        Args:
            protect_terminology: تفعيل حماية المصطلحات الطبية.
            language: اللغة الرئيسية ('ar' أو 'en').
            device: الجهاز ('cuda' للـ GPU أو 'cpu').
        """
        self.protect = protect_terminology
        self.language = language
        self.device = device
        self.terms = MEDICAL_TERMS_AR.copy()

        # ── تهيئة EasyOCR ──
        logger.info("⏳ جاري تحميل EasyOCR...")
        gpu = device == "cuda"
        self.reader = easyocr.Reader(
            ["ar", "en"],
            gpu=gpu,
            verbose=False,
            model_storage_directory=".",
            download_enabled=True,
        )
        logger.info("✅ تمّ تحميل EasyOCR بنجاح.")

        # ── قاعدة التصحيحات المحلية (ذاكرة + JSON) ──
        self._corrections: Dict[str, str] = {}
        self._corrections_file = Path("medical_corrections.json")
        self._load_corrections()

        # ── إحصائيات ──
        self._stats = {
            "total_processed": 0,
            "total_corrections": 0,
            "total_protected": 0,
        }

    # ─────────────────────────────────────────────────────────────────
    # core: process_image — المعالجة الكاملة
    # ─────────────────────────────────────────────────────────────────
    def process_image(self, image_input) -> "MedicalOCRResult":
        """معالجة صورة ملاحظة طبية كاملة.

        خطوات المعالجة:
            1. تحميل الصورة وتحويلها إلى RGB
            2. تحسين الصورة (contrast + denoise)
            3. التعرف على النصوص (EasyOCR)
            4. كشف المصطلحات الطبية
            5. التصحيح مع الحماية
            6. حفظ النتائج

        Args:
            image_input: مسار ملف (str/Path) أو numpy array أو PIL.Image.

        Returns:
            كائن MedicalOCRResult.
        """
        start_time = time.time()

        # 1. تحميل الصورة
        img = self._load_image(image_input)

        # 2. تحسين الصورة
        img_enhanced = self._enhance_image(img)

        # 3. التعرف بالـ OCR
        ocr_results = self._run_ocr(img_enhanced)

        # 4. تجميع النص
        original_text = "\n".join(
            item[1] for item in ocr_results
        )

        # 5. كشف المصطلحات المحمية
        protected = self._find_protected_terms(original_text)

        # 6. تصحيح مع حماية المصطلحات
        if self.protect:
            corrected_text = self._correct_with_protection(
                original_text, protected
            )
        else:
            corrected_text = original_text

        # 7. إنشاء النتيجة
        processing_time = round(time.time() - start_time, 2)
        self._stats["total_processed"] += 1
        self._stats["total_protected"] += len(protected)

        result = MedicalOCRResult(
            text=corrected_text,
            original_text=original_text,
            confidence=self._compute_confidence(ocr_results),
            protected_terms=protected,
            processing_time=processing_time,
            word_count=len(original_text.split()),
            line_count=len(ocr_results),
        )

        logger.info(
            "✅ تمّت المعالجة خلال %.1f ثانية — %.0f كلمة — %d مصطلح محمي",
            processing_time,
            result.word_count,
            len(protected),
        )
        return result

    # ─────────────────────────────────────────────────────────────────
    # image handling
    # ─────────────────────────────────────────────────────────────────
    def _load_image(self, image_input) -> np.ndarray:
        """تحميل الصورة من أي مصدر."""
        if isinstance(image_input, np.ndarray):
            return cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB) \
                if image_input.ndim == 3 and image_input.shape[2] == 3 \
                else image_input
        if isinstance(image_input, Image.Image):
            return np.array(image_input.convert("RGB"))
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
            if img is None:
                raise FileNotFoundError(f"لم يتم العثور على الصورة: {image_input}")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        raise TypeError(f"نوع المدخل غير مدعوم: {type(image_input)}")

    def _enhance_image(self, img: np.ndarray) -> np.ndarray:
        """تحسين الصورة: contrast + denoise + sharpen."""
        # تحويل إلى grayscale للمعالجة
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # زيادة التباين (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # إزالة الضوضاء
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

        # إعادة التحويل إلى RGB
        result = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
        return result

    # ─────────────────────────────────────────────────────────────────
    # OCR
    # ─────────────────────────────────────────────────────────────────
    def _run_ocr(self, img: np.ndarray) -> list:
        """تشغيل EasyOCR على الصورة."""
        results = self.reader.readtext(
            img,
            paragraph=True,
            detail=1,
        )
        return results

    def _compute_confidence(self, ocr_results: list) -> float:
        """حساب متوسط الثقة."""
        if not ocr_results:
            return 0.0
        confidences = [item[2] for item in ocr_results if len(item) > 2]
        return round(
            sum(confidences) / len(confidences) if confidences else 0.0, 4
        )

    # ─────────────────────────────────────────────────────────────────
    # terminology protection
    # ─────────────────────────────────────────────────────────────────
    def _find_protected_terms(self, text: str) -> List[str]:
        """كشف المصطلحات الطبية في النص."""
        found = []
        text_lower = text.lower()
        for term in self.terms:
            if term.lower() in text_lower:
                found.append(term)
        return sorted(set(found))

    def _correct_with_protection(
        self, text: str, protected: List[str]
    ) -> str:
        """تصحيح النص مع حماية المصطلحات الطبية.

        الاستراتيجية:
        1. استبدال المصطلحات بعلامات مؤقتة
        2. تطبيق التصحيحات المعروفة
        3. إعادة المصطلحات الأصلية
        """
        # استبدال المصطلحات بعلامات
        placeholders: Dict[str, str] = {}
        counter = 0
        for term in protected:
            ph = f"\x00MED{counter}\x00"
            placeholders[ph] = term
            # استبدال بحساسية الحالة
            text = re.sub(
                re.escape(term), ph, text, flags=re.IGNORECASE
            )
            counter += 1

        # تطبيق التصحيحات من القاموس
        for original, corrected in self._corrections.items():
            text = text.replace(original, corrected)

        # إعادة المصطلحات
        for ph, original in placeholders.items():
            text = text.replace(ph, original)

        return text

    # ─────────────────────────────────────────────────────────────────
    # corrections management
    # ─────────────────────────────────────────────────────────────────
    def add_correction(self, original: str, corrected: str) -> None:
        """إضافة تصحيح يدوي."""
        self._corrections[original] = corrected
        self._stats["total_corrections"] += 1
        self._save_corrections()
        logger.info("📝 تصحيح جديد: '%s' → '%s'", original, corrected)

    def _load_corrections(self) -> None:
        """تحميل التصحيحات من الملف."""
        if self._corrections_file.exists():
            try:
                data = json.loads(
                    self._corrections_file.read_text(encoding="utf-8")
                )
                self._corrections = data.get("corrections", {})
                # دمج مصطلحات مخصصة
                custom_terms = data.get("custom_terms", [])
                self.terms.update(custom_terms)
            except Exception as e:
                logger.warning("تعذّر تحميل التصحيحات: %s", e)

    def _save_corrections(self) -> None:
        """حفظ التصحيحات إلى الملف."""
        data = {
            "corrections": self._corrections,
            "custom_terms": list(self.terms - MEDICAL_TERMS_AR),
            "stats": self._stats,
            "updated_at": datetime.now().isoformat(),
        }
        self._corrections_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_stats(self) -> Dict:
        """الحصول على الإحصائيات."""
        return {
            **self._stats,
            "corrections_count": len(self._corrections),
            "terms_count": len(self.terms),
        }

    def export_results_zip(
        self,
        result: "MedicalOCRResult",
        output_path: str = "medical_ocr_results.zip",
    ) -> str:
        """تصدير النتائج في ملف ZIP.

        يحتوي على:
        - result.txt: النص المصحّح
        - result.json: البيانات المهيكلة
        - original.txt: النص الأصلي قبل التصحيح
        - stats.json: الإحصائيات
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # نص مصحّح
            zf.writestr("result.txt", result.text)
            # نص أصلي
            zf.writestr("original.txt", result.original_text)
            # بيانات مهيكلة
            result_data = {
                "text": result.text,
                "original_text": result.original_text,
                "confidence": result.confidence,
                "protected_terms": result.protected_terms,
                "word_count": result.word_count,
                "line_count": result.line_count,
                "processing_time": result.processing_time,
            }
            zf.writestr(
                "result.json",
                json.dumps(result_data, ensure_ascii=False, indent=2),
            )
            # إحصائيات
            zf.writestr(
                "stats.json",
                json.dumps(self.get_stats(), ensure_ascii=False, indent=2),
            )

        logger.info("📦 تمّ تصدير النتائج إلى: %s", output_path)
        return output_path


# ── إذا كان المشروع متوفّرًا، استخدم فئته بدلًا من البديل ──
if not _PROJECT_AVAILABLE:
    # استيراد easyocr محليًا
    import easyocr
    logger.info("✅ تمّ تهيئة النسخة المستقلة.")
else:
    # استخدم الفئة من المشروع
    AdvancedMedicalOCR = AdvancedMedicalOCR  # noqa: F811
    import easyocr


# =============================================================================
# حاوية النتائج
# =============================================================================
@dataclass
class MedicalOCRResult:
    """نتيجة معالجة ملاحظة طبية.

    Attributes:
        text: النص المصحّح النهائي.
        original_text: النص الأصلي من OCR.
        confidence: مستوى الثقة (0–1).
        protected_terms: قائمة المصطلحات الطبية المحمية.
        processing_time: وقت المعالجة بالثواني.
        word_count: عدد الكلمات.
        line_count: عدد الأسطر.
    """
    text: str = ""
    original_text: str = ""
    confidence: float = 0.0
    protected_terms: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    word_count: int = 0
    line_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "original_text": self.original_text,
            "confidence": self.confidence,
            "protected_terms": self.protected_terms,
            "processing_time": self.processing_time,
            "word_count": self.word_count,
            "line_count": self.line_count,
        }

    def summary(self) -> str:
        """ملخص قصير للنتيجة."""
        terms_str = "، ".join(self.protected_terms[:5])
        if len(self.protected_terms) > 5:
            terms_str += f" (+{len(self.protected_terms) - 5})"
        return (
            f"📊 **ملخص المعالجة:**\n"
            f"  - الكلمات: {self.word_count} | الأسطر: {self.line_count}\n"
            f"  - الثقة: {self.confidence:.1%}\n"
            f"  - الوقت: {self.processing_time:.1f} ثانية\n"
            f"  - المصطلحات المحمية ({len(self.protected_terms)}): {terms_str}\n"
            f"\n---\n"
            f"📝 **النص المصحّح:**\n{self.text}"
        )


# =============================================================================
# Cell 3: واجهة Gradio التفاعلية
# =============================================================================

# ── إنشاء مثيل عام ──
_ocr_instance: Optional[AdvancedMedicalOCR] = None


def _get_ocr() -> AdvancedMedicalOCR:
    """الحصول على مثيل OCR (singleton pattern)."""
    global _ocr_instance
    if _ocr_instance is None:
        device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
        _ocr_instance = AdvancedMedicalOCR(device=device)
    return _ocr_instance


def process_single_image(image, enable_protection):
    """معالجة صورة واحدة — callback لـ Gradio."""
    if image is None:
        return "❌ يرجى رفع صورة أولًا.", "", ""

    ocr = _get_ocr()
    ocr.protect = enable_protection

    result = ocr.process_image(image)
    return (
        result.summary(),
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        result.original_text,
    )


def process_batch_images(files, enable_protection):
    """معالجة مجموعة صور — callback لـ Gradio."""
    if not files:
        return "❌ يرجى رفع صور أولًا.", ""

    ocr = _get_ocr()
    ocr.protect = enable_protection

    all_results = []
    total_start = time.time()

    for idx, file_path in enumerate(files):
        logger.info("معالجة الصورة %d/%d: %s", idx + 1, len(files), file_path)
        result = ocr.process_image(file_path)
        all_results.append(result)

    total_time = round(time.time() - total_start, 2)

    # تجميع التقرير
    report_lines = [
        f"📊 **تقرير المعالجة الجماعية**",
        f"  - عدد الصور: {len(all_results)}",
        f"  - الوقت الإجمالي: {total_time} ثانية",
        f"  - إجمالي الكلمات: {sum(r.word_count for r in all_results)}",
        f"  - متوسط الثقة: {np.mean([r.confidence for r in all_results]):.1%}",
        f"  - المصطلحات المحمية: {set().union(*[r.protected_terms for r in all_results])}",
        f"\n---\n",
    ]

    for i, r in enumerate(all_results, 1):
        report_lines.append(f"### 📄 الصورة {i}")
        report_lines.append(r.text)
        report_lines.append("")

    full_report = "\n".join(report_lines)

    # تصدير JSON
    export_data = {
        "summary": {
            "total_images": len(all_results),
            "total_time": total_time,
            "avg_confidence": round(
                np.mean([r.confidence for r in all_results]), 4
            ),
        },
        "results": [r.to_dict() for r in all_results],
    }

    return full_report, json.dumps(export_data, ensure_ascii=False, indent=2)


def add_manual_correction(original_text, corrected_text):
    """إضافة تصحيح يدوي — callback لـ Gradio."""
    if not original_text.strip() or not corrected_text.strip():
        return "⚠️ يرجى ملء كلا الحقلين."

    ocr = _get_ocr()
    ocr.add_correction(original_text.strip(), corrected_text.strip())

    return (
        f"✅ تمّ إضافة التصحيح: '{original_text.strip()}' → '{corrected_text.strip()}'\n\n"
        f"📊 إجمالي التصحيحات: {ocr.get_stats()['corrections_count']}"
    )


def export_zip(progress_report):
    """تصدير النتائج في ملف ZIP."""
    if not progress_report.strip():
        return None

    ocr = _get_ocr()
    export_path = "medical_ocr_results.zip"

    with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.txt", progress_report)
        zf.writestr(
            "stats.json",
            json.dumps(ocr.get_stats(), ensure_ascii=False, indent=2),
        )
        if ocr._corrections_file.exists():
            zf.write(
                str(ocr._corrections_file), "corrections.json"
            )

    return export_path


# ── بناء الواجهة ──

def build_interface() -> gr.Blocks:
    """بناء واجهة Gradio الكاملة."""

    with gr.Blocks(
        title="OmniFile Medical OCR Reviewer v2.0",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="green",
        ),
        css="""
            .container { max-width: 1200px; margin: auto; }
            footer { display: none !important; }
            .gradio-container { direction: rtl; }
        """,
    ) as app:

        # ── العنوان ──
        gr.Markdown(
            """
            # 🏥 OmniFile Medical OCR Reviewer — v2.0
            ### معالجة الملاحظات الطبية بخط اليد + مراجعة تفاعلية + تصدير

            **الميزات:**
            - ✅ التعرف على الخط اليدوي العربي والإنجليزي
            - ✅ حماية المصطلحات الطبية من التصحيح الخاطئ
            - ✅ تصحيح إملائي ذكي
            - ✅ معالجة جماعية للصور
            - ✅ تصدير بصيغة TXT + JSON + ZIP
            """
        )

        with gr.Tabs():
            # ════════════════════════════════════════════════════════════
            # التبويب 1: معالجة صورة واحدة
            # ════════════════════════════════════════════════════════════
            with gr.Tab("📄 معالجة واحدة"):
                with gr.Row():
                    with gr.Column(scale=1):
                        single_image = gr.Image(
                            label="رفع صورة الملاحظة الطبية",
                            type="filepath",
                            height=400,
                        )
                        protect_toggle = gr.Checkbox(
                            label="حماية المصطلحات الطبية",
                            value=True,
                            info="منع التصحيح الإملائي من تعديل المصطلحات الطبية",
                        )
                        process_btn = gr.Button(
                            "🔍 معالجة", variant="primary", size="lg"
                        )

                    with gr.Column(scale=1):
                        single_output = gr.Markdown(label="النتيجة")
                        single_json = gr.Code(
                            label="بيانات JSON", language="json"
                        )
                        single_original = gr.Textbox(
                            label="النص الأصلي (قبل التصحيح)",
                            lines=6,
                            interactive=False,
                        )

                process_btn.click(
                    fn=process_single_image,
                    inputs=[single_image, protect_toggle],
                    outputs=[single_output, single_json, single_original],
                )

            # ════════════════════════════════════════════════════════════
            # التبويب 2: معالجة جماعية
            # ════════════════════════════════════════════════════════════
            with gr.Tab("📁 معالجة جماعية"):
                with gr.Row():
                    with gr.Column(scale=1):
                        batch_files = gr.File(
                            label="رفع صور متعددة",
                            file_count="multiple",
                            file_types=["image"],
                        )
                        batch_protect = gr.Checkbox(
                            label="حماية المصطلحات الطبية",
                            value=True,
                        )
                        batch_btn = gr.Button(
                            "🚀 معالجة الكل", variant="primary", size="lg"
                        )

                    with gr.Column(scale=2):
                        batch_report = gr.Markdown(label="تقرير المعالجة")
                        batch_json = gr.Code(
                            label="بيانات JSON", language="json"
                        )

                batch_btn.click(
                    fn=process_batch_images,
                    inputs=[batch_files, batch_protect],
                    outputs=[batch_report, batch_json],
                )

            # ════════════════════════════════════════════════════════════
            # التبويب 3: التصحيح اليدوي
            # ════════════════════════════════════════════════════════════
            with gr.Tab("✏️ تصحيح يدوي"):
                gr.Markdown(
                    """
                    أضف تصحيحات يدوية لتخصيص النظام. ستُستخدم تلقائيًا
                    في المعالجات اللاحقة.
                    """
                )
                with gr.Row():
                    with gr.Column():
                        orig_input = gr.Textbox(
                            label="النص الخاطئ (من OCR)",
                            placeholder="مثال: باسال",
                            lines=2,
                        )
                        corr_input = gr.Textbox(
                            label="التصحيح الصحيح",
                            placeholder="مثال: بايسال",
                            lines=2,
                        )
                        corr_btn = gr.Button(
                            "➕ إضافة تصحيح", variant="secondary"
                        )

                    with gr.Column():
                        corr_output = gr.Markdown(label="النتيجة")

                corr_btn.click(
                    fn=add_manual_correction,
                    inputs=[orig_input, corr_input],
                    outputs=[corr_output],
                )

            # ════════════════════════════════════════════════════════════
            # التبويب 4: التصدير
            # ════════════════════════════════════════════════════════════
            with gr.Tab("📦 تصدير"):
                gr.Markdown(
                    """
                    صدّر النتائج والتصحيحات في ملف ZIP.
                    """
                )
                export_input = gr.Textbox(
                    label="الصق تقرير المعالجة هنا",
                    lines=8,
                    placeholder="انسخ التقرير من تبويب 'معالجة جماعية' والصقه هنا...",
                )
                export_btn = gr.Button("💾 تصدير ZIP", variant="primary")
                export_file = gr.File(label="ملف ZIP")

                export_btn.click(
                    fn=export_zip,
                    inputs=[export_input],
                    outputs=[export_file],
                )

        # ── التذييل ──
        gr.Markdown(
            """
            ---
            **OmniFile Medical OCR Reviewer v2.0** | Dr. Abdulmalek Tamer Al-husseini
            | MIT License
            """
        )

    return app


# =============================================================================
# Cell 4: تشغيل الواجهة
# =============================================================================
"""
شغّل هذا الخلية لإطلاق واجهة Gradio.
في Colab، سيظهر رابط مؤقت (ngrok أو public URL).
"""

if __name__ == "__main__":
    print("=" * 65)
    print("  OmniFile Medical OCR Reviewer — Colab Edition v2.0")
    print("  معالجة الملاحظات الطبية بخط اليد + مراجعة تفاعلية")
    print("=" * 65)

    app = build_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,          # إنشاء رابط عام (لـ Colab)
        debug=False,
        show_error=True,
    )
