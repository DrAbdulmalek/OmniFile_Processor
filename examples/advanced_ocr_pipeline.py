#!/usr/bin/env python3
"""
Advanced OCR Pipeline — أنبوب معالجة OCR المتقدم
===================================================
مثال شامل يُظهِر كيفية دمج عدة وحدات من OmniFile Processor
لبناء أنبوب OCR متقدم مع:
  - اختيار ذكي للمحركات عبر EngineRouter
  - معالجة متوازية للصفحات عبر ParallelProcessor
  - دمج نتائج متعددة عبر ResultFusion
  - تتبع التقدم وإدارة الذاكرة عبر ModelCache
  - التعامل مع النصوص العربية (RTL)
  - تصدير متعدد الصيغات (Markdown)
  - معالجة الأخطاء مع الانحطاط السلس

Comprehensive example demonstrating how to combine multiple OmniFile
modules to build an advanced OCR pipeline with:
  - Smart engine selection via EngineRouter
  - Parallel page processing via ParallelProcessor
  - Multi-engine result fusion via ResultFusion
  - Progress tracking and memory management via ModelCache
  - Arabic RTL text handling
  - Multi-format export (Markdown)
  - Graceful error handling with degradation

Usage / الاستخدام:
    python examples/advanced_ocr_pipeline.py
    python examples/advanced_ocr_pipeline.py --input document.pdf --lang ar
    python examples/advanced_ocr_pipeline.py --input mixed_doc.pdf --lang mixed

Author: OmniFile AI Processor v5.0
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── إعداد التسجيل / Logging Setup ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("advanced_ocr_pipeline")

# ── الاستيرادات من المشروع / Project Imports ────────────────────────────
from modules.core.engine_router import EngineRouter
from modules.core.parallel_processor import ParallelProcessor
from modules.core.model_manager import ModelCache
from modules.vision.result_fusion import (
    ResultFusion,
    FusionStrategy,
    BoundingBox,
    LineResult,
    PageResult,
    DocumentResult,
    TextBlockType,
)
from modules.nlp.arabic_rtl import (
    RTLFixer,
    is_rtl_text,
    get_text_direction,
    fix_rtl_display,
    normalize_arabic_ocr,
)
from modules.export.markdown_exporter import export_to_markdown


# ═══════════════════════════════════════════════════════════════════════
# §1  هياكل البيانات المحلية / Local Data Structures
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class OCRPageInput:
    """مدخلات صفحة واحدة للمعالجة / Input for a single page to process."""
    page_number: int
    image_path: Optional[str] = None
    image_array: Optional[Any] = None          # np.ndarray
    estimated_quality: float = 0.80            # 0.0–1.0
    detected_language: str = "ar"              # ar | en | de | mixed
    block_types: List[str] = field(default_factory=lambda: ["paragraph"])


@dataclass
class PipelineResult:
    """نتيجة المعالجة الكاملة / Complete pipeline result."""
    filename: str = ""
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    merged_text: str = ""
    engine_usage: Dict[str, int] = field(default_factory=dict)
    processing_time_seconds: float = 0.0
    fusion_strategy: str = "highest_confidence"
    markdown_output: str = ""
    memory_report: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# §2  محاكاة محركات OCR (للتوضيح) / Simulated OCR Engines (for demo)
# ═══════════════════════════════════════════════════════════════════════

def _simulate_ocr_engine(
    page: OCRPageInput,
    engine_name: str,
) -> PageResult:
    """
    محاكاة محرك OCR — تُرجع نتيجة PageResult مع نص تجريبي.
    Simulates an OCR engine — returns a PageResult with demo text.

    في بيئة الإنتاج، يُستبدل هذا باستدعاء حقيقي مثل:
      - EasyOCR:  reader.readtext(image)
      - Tesseract: pytesseract.image_to_data(image, lang='ara+eng')
      - TrOCR:    processor(image, return_tensors="pt"); model.generate(**inputs)

    Args:
        page:         بيانات الصفحة المدخلة
        engine_name:  اسم المحرك (EasyOCR, Tesseract, TrOCR, PaddleOCR)

    Returns:
        PageResult مع أسطر نصية محاكاة
    """
    # نصوص تجريبية حسب اللغة المكتشفة
    demo_texts = {
        "ar": "المريض يعاني من ألم في مفصل الركبة اليسرى منذ أسبوعين",
        "en": "Patient reports persistent pain in the left knee joint for two weeks",
        "de": "Der Patient berichtet über anhaltende Schmerzen im linken Kniegelenk",
        "mixed": "التشخيص: Osteoarthritis —Grade II —العلاج: NSAIDs + Physical Therapy",
    }
    text = demo_texts.get(page.detected_language, demo_texts["en"])

    # محاكاة اختلاف الثقة بين المحركات
    confidence_map = {
        "EasyOCR":   0.88,
        "Tesseract": 0.76,
        "TrOCR":     0.92,
        "PaddleOCR": 0.85,
    }
    confidence = confidence_map.get(engine_name, 0.80)

    # محاكاة خطأ OCR شائع (حرف O بدل رقم 0)
    noisy_text = text
    if engine_name == "Tesseract" and page.detected_language == "en":
        noisy_text = text.replace("II", "11")  # Tesseract أحياناً يقلب II → 11

    # تحديد نوع الكتلة
    block_type = TextBlockType.PARAGRAPH
    if "header" in page.block_types:
        block_type = TextBlockType.HEADING
    elif "table" in page.block_types:
        block_type = TextBlockType.TABLE

    line = LineResult(
        text=noisy_text,
        confidence=confidence,
        bbox=BoundingBox(x=50, y=100, width=700, height=30),
        block_type=block_type,
        language=page.detected_language,
    )

    return PageResult(
        page_number=page.page_number,
        lines=[line],
        width=800,
        height=1100,
    )


# ═══════════════════════════════════════════════════════════════════════
# §3  فئة أنبوب OCR المتقدم / Advanced OCR Pipeline Class
# ═══════════════════════════════════════════════════════════════════════

class AdvancedOCRPipeline:
    """
    أنبوب معالجة OCR متقدم يجمع عدة وحدات.

    يُنفِّذ هذا الأنبوب المراحل التالية بالترتيب:
    1.  تحليل الصفحات واكتشاف اللغة
    2.  اختيار المحركات المناسبة لكل صفحة عبر EngineRouter
    3.  معالجة الصفحات بالتوازي عبر ParallelProcessor
    4.  دمج نتائج المحركات المتعددة عبر ResultFusion
    5.  إصلاح اتجاه النص RTL للعربية
    6.  تصدير النتيجة النهائية

    Example:
        >>> pipeline = AdvancedOCRPipeline(profile="balanced", fusion_strategy="voting")
        >>> result = pipeline.process_file("document.pdf")
        >>> print(result.merged_text)
        >>> print(result.markdown_output)
    """

    def __init__(
        self,
        profile: str = "balanced",
        use_gpu: bool = False,
        max_workers: int = 4,
        fusion_strategy: str = "highest_confidence",
        max_memory_gb: float = 8.0,
    ) -> None:
        """
        تهيئة الأنبوب / Initialize the pipeline.

        Args:
            profile:          بروفايل المحركات (low | balanced | high)
            use_gpu:          هل GPU متاح
            max_workers:      أقصى عدد عمال للتوازي
            fusion_strategy:  استراتيجية الدمج (highest_confidence | voting | weighted_average)
            max_memory_gb:    الحد الأقصى للذاكرة للمخزن المؤقت
        """
        self.profile = profile
        self.use_gpu = use_gpu
        self.max_workers = max_workers

        # ── تهيئة المكونات / Initialize components ───────────────────
        self.router = EngineRouter(
            profile=profile,
            use_gpu=use_gpu,
            max_engines=2,
        )
        self.processor = ParallelProcessor(
            max_workers=max_workers,
            default_executor_type="thread",
        )

        # إعداد استراتيجية الدمج
        strategy_enum = FusionStrategy(fusion_strategy)
        self.fusion = ResultFusion(strategy=strategy_enum)
        self.fusion_strategy_name = fusion_strategy

        # مخزن النماذج المؤقت (Singleton)
        self.model_cache = ModelCache.instance(max_memory_gb=max_memory_gb)

        # إصلاح RTL
        self.rtl_fixer = RTLFixer()

        logger.info(
            "تم تهيئة الأنبوب — profile=%s, gpu=%s, workers=%d, fusion=%s",
            profile, use_gpu, max_workers, fusion_strategy,
        )

    # ──────────────────────────────────────────────────────────────────
    # واجهة رئيسية / Main Interface
    # ──────────────────────────────────────────────────────────────────

    def process_file(self, file_path: str) -> PipelineResult:
        """
        معالجة ملف كامل (PDF أو صورة).

        Processes a complete file. For demo purposes, this generates
        simulated page inputs. In production, you would use:
            from modules.vision.pdf_processor import PDFProcessor
            pages = pdf_processor.extract_pages(file_path)

        Args:
            file_path: مسار الملف

        Returns:
            PipelineResult بنتائج المعالجة
        """
        start_time = time.time()
        result = PipelineResult(filename=str(file_path))

        logger.info("بدء معالجة الملف: %s", file_path)

        try:
            # ── المرحلة 1: تحضير الصفحات ─────────────────────────
            pages = self._prepare_pages(file_path)
            result.total_pages = len(pages)
            logger.info("تم تحضير %d صفحة للمعالجة", len(pages))

            # ── المرحلة 2: اختيار المحركات لكل صفحة ─────────────
            engine_assignments = self._assign_engines(pages, result)

            # ── المرحلة 3: معالجة متوازية للصفحات ────────────────
            page_results = self._process_pages_parallel(
                pages, engine_assignments, result
            )

            # ── المرحلة 4: دمج نتائج المحركات ───────────────────
            merged_pages = self._fuse_page_results(page_results)
            logger.info("تم دمج نتائج %d صفحة بنجاح", len(merged_pages))

            # ── المرحلة 5: إصلاح RTL وإعداد النص النهائي ────────
            result.merged_text = self._post_process_text(merged_pages)

            # ── المرحلة 6: التصدير ───────────────────────────────
            result.markdown_output = self._export_to_formats(
                merged_pages, file_path
            )

            # ── المرحلة 7: تقرير الذاكرة ────────────────────────
            result.memory_report = self.model_cache.get_memory_report()

        except Exception as exc:
            logger.error("فشل في معالجة الملف: %s", exc, exc_info=True)
            result.errors.append(f"خطأ عام: {exc}")

        result.processing_time_seconds = round(time.time() - start_time, 2)
        result.fusion_strategy = self.fusion_strategy_name

        logger.info(
            "اكتملت المعالجة — %d/%d صفحة ناجحة في %.2f ثانية",
            result.successful_pages, result.total_pages,
            result.processing_time_seconds,
        )
        return result

    # ──────────────────────────────────────────────────────────────────
    # مراحل داخلية / Internal Stages
    # ──────────────────────────────────────────────────────────────────

    def _prepare_pages(self, file_path: str) -> List[OCRPageInput]:
        """
        تحضير مدخلات الصفحات من الملف.
        Prepare page inputs from the file.

        في بيئة الإنتاج:
            from modules.vision.pdf_processor import PDFProcessor
            processor = PDFProcessor()
            images = processor.extract_page_images(file_path)

        هنا نُنشئ صفحات محاكاة للتوضيح.
        """
        ext = Path(file_path).suffix.lower()
        pages: List[OCRPageInput] = []

        if ext in (".pdf",):
            # محاكاة ملف PDF من 5 صفحات
            for i in range(1, 6):
                pages.append(OCRPageInput(
                    page_number=i,
                    image_path=file_path,
                    estimated_quality=0.75 + (i % 3) * 0.10,
                    detected_language="ar" if i % 2 == 1 else "en",
                    block_types=["paragraph"] if i != 3 else ["table"],
                ))
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            pages.append(OCRPageInput(
                page_number=1,
                image_path=file_path,
                estimated_quality=0.85,
                detected_language="ar",
            ))
        else:
            logger.warning("صيغة ملف غير مدعومة: %s — استخدام محاكاة", ext)
            for i in range(1, 4):
                pages.append(OCRPageInput(
                    page_number=i,
                    estimated_quality=0.80,
                    detected_language="ar",
                ))

        return pages

    def _assign_engines(
        self,
        pages: List[OCRPageInput],
        result: PipelineResult,
    ) -> Dict[int, Tuple[List[str], List[str]]]:
        """
        اختيار المحركات المناسبة لكل صفحة عبر EngineRouter.
        Assign optimal engines to each page using EngineRouter.

        Args:
            pages:  قائمة صفحات المدخلات
            result: كائن النتيجة (لتتبع استخدام المحركات)

        Returns:
            قاموس: رقم الصفحة → (محركات مختارة, أسباب الاختيار)
        """
        assignments: Dict[int, Tuple[List[str], List[str]]] = {}

        for page in pages:
            engines, reasons = self.router.select(
                image_quality=page.estimated_quality,
                language=page.detected_language,
                block_type=page.block_types[0] if page.block_types else "paragraph",
            )
            assignments[page.page_number] = (engines, reasons)

            # تتبع استخدام المحركات
            for engine in engines:
                result.engine_usage[engine] = (
                    result.engine_usage.get(engine, 0) + 1
                )

            logger.info(
                "  صفحة %d: محركات=%s (أسباب: %s)",
                page.page_number, engines, reasons,
            )

        return assignments

    def _process_pages_parallel(
        self,
        pages: List[OCRPageInput],
        assignments: Dict[int, Tuple[List[str], List[str]]],
        result: PipelineResult,
    ) -> Dict[int, PageResult]:
        """
        معالجة الصفحات بالتوازي — كل صفحة بمحركاتها المختارة.
        Process pages in parallel, each with its assigned engines.

        Args:
            pages:        قائمة الصفحات
            assignments:  تعيينات المحركات لكل صفحة
            result:       كائن النتيجة

        Returns:
            قاموس: رقم الصفحة → PageResult المدمج
        """
        def _process_single_page(page: OCRPageInput) -> Optional[PageResult]:
            """دالة معالجة صفحة واحدة / Function to process a single page."""
            try:
                engines, _ = assignments.get(page.page_number, (["Tesseract"], []))
                page_results_from_engines: List[PageResult] = []

                for engine_name in engines:
                    try:
                        engine_result = _simulate_ocr_engine(page, engine_name)
                        page_results_from_engines.append(engine_result)
                    except Exception as exc:
                        logger.warning(
                            "محرك %s فشل في صفحة %d: %s — انحطاط سلس",
                            engine_name, page.page_number, exc,
                        )
                        # الانحطاط السلس: نتخطى هذا المحرك ونكمل بالباقي
                        continue

                if not page_results_from_engines:
                    logger.error("جميع المحركات فشلت في صفحة %d", page.page_number)
                    return None

                # دمج نتائج المحركات لهذه الصفحة
                merged = self.fusion.merge_pages(page_results_from_engines)
                return merged

            except Exception as exc:
                logger.error("خطأ في معالجة صفحة %d: %s", page.page_number, exc)
                return None

        # استخدام ParallelProcessor لمعالجة متوازية
        merged_results = self.processor.process_batch(
            items=pages,
            process_fn=_process_single_page,
            n_workers=self.max_workers,
            executor_type="thread",
            description="معالجة OCR المتوازية",
        )

        # تجميع النتائج
        page_result_map: Dict[int, PageResult] = {}
        for idx, page in enumerate(pages):
            if merged_results[idx] is not None:
                page_result_map[page.page_number] = merged_results[idx]
                result.successful_pages += 1
            else:
                result.failed_pages += 1
                result.errors.append(f"صفحة {page.page_number}: فشلت المعالجة")

        return page_result_map

    def _fuse_page_results(
        self,
        page_results: Dict[int, PageResult],
    ) -> List[PageResult]:
        """
        ترتيب نتائج الصفحات المدمجة.
        Organize merged page results in order.
        """
        sorted_pages = sorted(page_results.values(), key=lambda p: p.page_number)
        return sorted_pages

    def _post_process_text(self, merged_pages: List[PageResult]) -> str:
        """
        المعالجة البعدية للنص: إصلاح RTL وتطبيع النص العربي.
        Post-process text: fix RTL and normalize Arabic text.
        """
        all_lines: List[str] = []

        for page in merged_pages:
            for line in page.lines:
                text = line.text

                # 1. تطبيع أشكال الحروف العربية (أهم خطوة لـ OCR)
                text = normalize_arabic_ocr(text)

                # 2. إصلاح اتجاه RTL إذا كان النص عربياً
                direction = get_text_direction(text)
                if direction in ("rtl", "mixed"):
                    text = fix_rtl_display(text)

                all_lines.append(text)

        return "\n".join(all_lines)

    def _export_to_formats(
        self,
        merged_pages: List[PageResult],
        file_path: str,
    ) -> str:
        """
        تصدير النتائج إلى صيغ متعددة.
        Export results to multiple formats.

        يدعم حالياً: Markdown مع محاذاة RTL.
        In production, add: DOCX, JSON, HTML, TXT.
        """
        # تحويل إلى تنسيق layout_data المتوقع من MarkdownExporter
        blocks = []
        for page in merged_pages:
            for line in page.lines:
                block_type = "paragraph"
                if line.block_type == TextBlockType.HEADING:
                    block_type = "header"
                elif line.block_type == TextBlockType.TABLE:
                    block_type = "table"
                elif line.block_type == TextBlockType.HEADER:
                    block_type = "header"
                elif line.block_type == TextBlockType.FOOTER:
                    block_type = "footer"

                blocks.append({
                    "type": block_type,
                    "text": line.text,
                    "confidence": line.confidence,
                    "language": line.language,
                })

        layout_data = {"blocks": blocks}

        # تحديد RTL من اللغة السائدة
        is_rtl = any(
            get_text_direction(line.text) in ("rtl", "mixed")
            for page in merged_pages
            for line in page.lines
            if line.text.strip()
        )

        md_output = export_to_markdown(layout_data, rtl=is_rtl)

        # حفظ الملف
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_name = Path(file_path).stem + "_ocr_output.md"
        output_path = output_dir / output_name
        export_to_markdown(layout_data, output_path=str(output_path), rtl=is_rtl)
        logger.info("تم حفظ Markdown: %s", output_path)

        return md_output


# ═══════════════════════════════════════════════════════════════════════
# §4  عرض النتائج / Result Display
# ═══════════════════════════════════════════════════════════════════════

def print_pipeline_report(result: PipelineResult) -> None:
    """طباعة تقرير مفصل عن نتائج الأنبوب / Print a detailed pipeline report."""
    print("\n" + "=" * 70)
    print("  تقرير أنبوب OCR المتقدم — Advanced OCR Pipeline Report")
    print("=" * 70)

    print(f"\n📄 الملف:                {result.filename}")
    print(f"📊 إجمالي الصفحات:       {result.total_pages}")
    print(f"✅ صفحات ناجحة:          {result.successful_pages}")
    print(f"❌ صفحات فاشلة:          {result.failed_pages}")
    print(f"⏱️  وقت المعالجة:         {result.processing_time_seconds} ثانية")
    print(f"🔀 استراتيجية الدمج:      {result.fusion_strategy}")

    # استخدام المحركات
    print(f"\n🔧 استخدام المحركات:")
    for engine, count in result.engine_usage.items():
        bar = "█" * count + "░" * (result.total_pages - count)
        print(f"   {engine:15s} {bar}  ({count} صفحة)")

    # تقدير الوقت
    router = EngineRouter()
    print(f"\n⏳ تقدير وقت المعالجة:")
    for engine in result.engine_usage:
        est = router.estimate_time([engine])
        print(f"   {engine}: ~{est} ثانية/صفحة")

    # النص المدمج
    if result.merged_text:
        print(f"\n📝 النص المدمج (أول 500 حرف):")
        print("-" * 40)
        preview = result.merged_text[:500]
        print(preview)
        if len(result.merged_text) > 500:
            print("...")
        print("-" * 40)

    # تقرير الذاكرة
    if result.memory_report:
        report = result.memory_report
        print(f"\n💾 تقرير الذاكرة:")
        print(f"   النماذج المخزنة:       {report['total_models']}")
        print(f"   الذاكرة المستخدمة:      {report['total_memory_mb']:.1f} MB")
        print(f"   الحد الأقصى:            {report['max_memory_gb']:.1f} GB")
        print(f"   معدل الإصابة:          {report['cache_hit_rate']:.1%}")
        print(f"   GPU allocated:         {report.get('gpu_allocated_mb', 'N/A')} MB")

    # الأخطاء
    if result.errors:
        print(f"\n⚠️  الأخطاء ({len(result.errors)}):")
        for err in result.errors:
            print(f"   • {err}")

    # ملخص إحصائيات المعالج المتوازي
    processor = ParallelProcessor()
    stats = processor.get_stats()
    print(f"\n🚀 إحصائيات المعالج المتوازي:")
    print(f"   العمال المتاحين:        {stats['max_workers']}")
    print(f"   العمال الأمثل:          {stats['optimal_workers']}")
    print(f"   المنفذ الافتراضي:       {stats['default_executor_type']}")

    print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════════════
# §5  نقطة الدخول / Entry Point
# ═══════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    دالة رئيسية توضح جميع قدرات الأنبوب.
    Main function demonstrating all pipeline capabilities.
    """
    parser = argparse.ArgumentParser(
        description="أنبوب OCR متقدم — Advanced OCR Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة / Examples:
  python examples/advanced_ocr_pipeline.py
  python examples/advanced_ocr_pipeline.py --input document.pdf
  python examples/advanced_ocr_pipeline.py --input doc.pdf --profile high --fusion voting
        """,
    )
    parser.add_argument(
        "--input", "-i",
        default="demo_document.pdf",
        help="مسار الملف المدخل / Input file path (default: demo_document.pdf)",
    )
    parser.add_argument(
        "--profile", "-p",
        choices=["low", "balanced", "high"],
        default="balanced",
        help="بروفايل المحركات / Engine profile (default: balanced)",
    )
    parser.add_argument(
        "--fusion", "-f",
        choices=["highest_confidence", "weighted_average", "voting", "longest_text"],
        default="highest_confidence",
        help="استراتيجية دمج النتائج / Fusion strategy (default: highest_confidence)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="عدد العمال المتوازي / Parallel workers (default: 4)",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="تفعيل دعم GPU / Enable GPU support",
    )
    args = parser.parse_args()

    print("┌─────────────────────────────────────────────────┐")
    print("│  OmniFile Processor — أنبوب OCR المتقدم         │")
    print("│  Advanced OCR Pipeline                         │")
    print("└─────────────────────────────────────────────────┘")
    print()

    # ── عرض إعدادات الموجّه / Show router settings ─────────
    router = EngineRouter(profile=args.profile, use_gpu=args.gpu)
    print("📋 إعدادات EngineRouter:")
    print(f"   {json.dumps(router.summary(), indent=4, ensure_ascii=False)}")
    print()

    # ── أمثلة اختيار المحركات / Engine selection examples ───
    print("🔍 أمثلة على اختيار المحركات الذكي:")
    scenarios = [
        {"quality": 0.90, "lang": "ar",  "block": "paragraph",   "label": "عربي عالي الجودة"},
        {"quality": 0.45, "lang": "en",  "block": "paragraph",   "label": "إنجليزي منخفض الجودة"},
        {"quality": 0.80, "lang": "ar",  "block": "handwriting", "label": "عربي خط يدوي"},
        {"quality": 0.85, "lang": "en",  "block": "table",       "label": "إنجليزي جدول"},
        {"quality": 0.70, "lang": "mixed","block": "paragraph",  "label": "مختلط"},
    ]
    for scenario in scenarios:
        engines, reasons = router.select(
            image_quality=scenario["quality"],
            language=scenario["lang"],
            block_type=scenario["block"],
        )
        est_time = router.estimate_time(engines)
        print(
            f"   {scenario['label']:25s} → {engines} "
            f"(~{est_time}s) — {'; '.join(reasons)}"
        )
    print()

    # ── إنشاء وتشغيل الأنبوب / Create and run pipeline ────────
    pipeline = AdvancedOCRPipeline(
        profile=args.profile,
        use_gpu=args.gpu,
        max_workers=args.workers,
        fusion_strategy=args.fusion,
    )

    result = pipeline.process_file(args.input)
    print_pipeline_report(result)

    # ── عرض ملخص المخرجات / Show output summary ───────────────
    print("\n✨ تم تشغيل الأنبوب بنجاح!")
    print(f"   ملف Markdown: output/{Path(args.input).stem}_ocr_output.md")


if __name__ == "__main__":
    main()
