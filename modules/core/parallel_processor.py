"""
وحدة المعالجة المتوازية — Parallel Processing Utility
=====================================================

وحدة لمعالجة المستندات والصفحات بشكل متوازي باستخدام
ProcessPoolExecutor و ThreadPoolExecutor و joblib.

تهدف هذه الوحدة إلى تحسين الأداء عند التعامل مع مستندات كبيرة
أو مجموعات ضخمة من الملفات عبر توزيع العمل على عدة عمليات أو خيوط.

This module provides parallel processing utilities for large documents
and massive batches using concurrent.futures and joblib.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# --- إعداد المسجل — Logger Setup ---
logger = logging.getLogger(__name__)


# =====================================================================
# دوال مساعدة داخلية — Internal Helper Functions
# =====================================================================

def _detect_optimal_workers() -> int:
    """
    حساب العدد الأمثل للعمال بناءً على عدد أنوية المعالج والذاكرة المتاحة.
    Detect the optimal number of workers based on CPU cores and available RAM.

    Returns:
        int: العدد الأمثل للعمال (لا يقل عن 1)
    """
    # الحد الأدنى هو 1 عامل
    min_workers = 1
    cpu_count = os.cpu_count() or 4
    max_workers = min(cpu_count, 32)  # حد أقصى 32 عامل لمنع الإفراط

    # محاولة استخدام psutil لقراءة الذاكرة المتاحة
    try:
        import psutil

        available_gb = psutil.virtual_memory().available / (1024**3)
        # التقدير التقريبي: كل عامل يحتاج ~0.5 جيجابايت على الأقل
        memory_based = max(min_workers, int(available_gb / 0.5))
        optimal = min(max_workers, memory_based)
        logger.info(
            "اكتُشف العدد الأمثل للعمال: %d (أنوية: %d, ذاكرة متاحة: %.1f جيجابايت)",
            optimal, cpu_count, available_gb,
        )
        return optimal
    except ImportError:
        # psutil غير متاح — نعتمد على عدد الأنوية فقط
        optimal = max(min_workers, cpu_count - 1)
        logger.info(
            "psutil غير متاح، تم حساب العدد الأمثل بناءً على الأنوية: %d",
            optimal,
        )
        return optimal


def _wrap_with_timeout(
    fn: Callable[..., Any],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    timeout: float,
) -> Any:
    """
    غلاف ينفّذ الدالة مع مهلة زمنية محددة.
    Wrapper that executes a function with a per-item timeout.

    Args:
        fn: الدالة المطلوب تنفيذها
        args: معاملات位置ية (positional arguments)
        kwargs: معاملات مُسمّاة (keyword arguments)
        timeout: المهلة الزمنية بالثواني

    Returns:
        نتيجة تنفيذ الدالة

    Raises:
        TimeoutError: إذا تجاوز التنفيذ المهلة المحددة
    """
    # استخدام خيط منفصل لتنفيذ الدالة مع مهلة
    result: Any = None
    exception: Optional[BaseException] = None
    done_event = threading.Event()

    def _target() -> None:
        nonlocal result, exception
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc:
            exception = exc
        finally:
            done_event.set()

    worker_thread = threading.Thread(target=_target, daemon=True)
    worker_thread.start()
    completed = done_event.wait(timeout=timeout)

    if not completed:
        raise TimeoutError(
            f"تجاوز التنفيذ المهلة المحددة ({timeout} ثانية) — "
            f"Function call exceeded timeout of {timeout}s"
        )

    if exception is not None:
        raise exception

    return result


# =====================================================================
# فئة المعالج المتوازي — ParallelProcessor Class
# =====================================================================

class ParallelProcessor:
    """
    معالج متوازي لتوزيع المهام على عدة عمال.
    Parallel processor for distributing tasks across multiple workers.

    يدعم هذه الفئة:
    - تنفيذ المهام على خيوط (ThreadPoolExecutor)
    - تنفيذ المهام على عمليات (ProcessPoolExecutor)
    - التتبع الآمن للتقدم عبر خيوط متعددة
    - كشف تلقائي للعدد الأمثل للعمال
    - دعم joblib عند توفره

    Example:
        >>> processor = ParallelProcessor()
        >>> results = processor.process_batch(
        ...     items=[1, 2, 3, 4, 5],
        ...     process_fn=lambda x: x ** 2,
        ...     executor_type='thread',
        ...     description="حساب المربعات",
        ... )
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        default_executor_type: str = "thread",
    ) -> None:
        """
        تهيئة المعالج المتوازي.
        Initialize the parallel processor.

        Args:
            max_workers: الحد الأقصى للعمال (لا شيء = كشف تلقائي)
            default_executor_type: نوع المنفّذ الافتراضي ('thread' أو 'process')
        """
        # كشف العدد الأمثل للعمال إذا لم يُحدّد
        self._max_workers: int = max_workers or _detect_optimal_workers()
        self._default_executor_type: str = default_executor_type
        self._progress_lock: threading.Lock = threading.Lock()
        self._completed_count: int = 0
        self._total_count: int = 0
        self._start_time: Optional[float] = None

        logger.info(
            "تم تهيئة المعالج المتوازي — عمال: %d, منفّذ افتراضي: %s",
            self._max_workers,
            self._default_executor_type,
        )

    # -----------------------------------------------------------------
    # خاصيات — Properties
    # -----------------------------------------------------------------

    @property
    def optimal_workers(self) -> int:
        """العدد الأمثل للعمال المكتشف تلقائيًا."""
        return _detect_optimal_workers()

    # -----------------------------------------------------------------
    # تتبع التقدم — Progress Tracking
    # -----------------------------------------------------------------

    def _reset_progress(self, total: int) -> None:
        """
        إعادة تعيين عداد التقدم.
        Reset the progress counter.

        Args:
            total: العدد الإجمالي للعناصر
        """
        with self._progress_lock:
            self._completed_count = 0
            self._total_count = total
            self._start_time = time.time()

    def _update_progress(
        self,
        increment: int = 1,
        description: str = "",
    ) -> None:
        """
        تحديث عداد التقدم بطريقة آمنة للخيوط.
        Update the progress counter in a thread-safe manner.

        Args:
            increment: مقدار الزيادة (الافتراضي 1)
            description: وصف إضافي للطباعة
        """
        with self._progress_lock:
            self._completed_count += increment
            completed = self._completed_count
            total = self._total_count

            if total > 0:
                percentage = (completed / total) * 100
                elapsed = time.time() - (self._start_time or time.time())
                # حساب السرعة التقريبية
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (total - completed) / rate if rate > 0 else 0

                logger.debug(
                    "[%s] التقدم: %d/%d (%.1f%%) — السرعة: %.1f عنصر/ث — "
                    "الوقت المتبقي: %.1f ث — Progress: %d/%d (%.1f%%)",
                    description,
                    completed,
                    total,
                    percentage,
                    rate,
                    eta,
                    completed,
                    total,
                    percentage,
                )

    # -----------------------------------------------------------------
    # إنشاء المنفّذ — Executor Factory
    # -----------------------------------------------------------------

    def _create_executor(
        self,
        executor_type: str,
        max_workers: Optional[int] = None,
    ):
        """
        إنشاء المنفّذ المناسب حسب النوع المطلوب.
        Create the appropriate executor based on the requested type.

        Args:
            executor_type: نوع المنفّذ ('thread' أو 'process')
            max_workers: عدد العمال (الافتراضي: العدد الأمثل)

        Returns:
            منفّذ (ThreadPoolExecutor أو ProcessPoolExecutor)

        Raises:
            ValueError: إذا كان نوع المنفّذ غير صالح
        """
        workers = max_workers or self._max_workers
        executor_type = executor_type.lower()

        if executor_type == "thread":
            logger.debug("إنشاء منفّذ الخيوط بعدد عمال: %d", workers)
            return ThreadPoolExecutor(max_workers=workers)
        elif executor_type == "process":
            logger.debug("إنشاء منفّذ العمليات بعدد عمال: %d", workers)
            return ProcessPoolExecutor(max_workers=workers)
        else:
            raise ValueError(
                f"نوع المنفّذ غير مدعوم: '{executor_type}' — "
                f"Unsupported executor type: '{executor_type}'. "
                f"Use 'thread' or 'process'."
            )

    # -----------------------------------------------------------------
    # معالجة الدفعات — Batch Processing
    # -----------------------------------------------------------------

    def process_batch(
        self,
        items: Sequence[Any],
        process_fn: Callable[[Any], Any],
        n_workers: Optional[int] = None,
        executor_type: str = "thread",
        description: str = "",
    ) -> List[Any]:
        """
        معالجة مجموعة من العناصر بالتوازي.
        Process a batch of items in parallel.

        توزّع هذه الدالة العناصر على عمال متعددين وتجمع النتائج
        بالترتيب الأصلي للعناصر.

        Args:
            items: مجموعة العناصر المراد معالجتها
            process_fn: دالة المعالجة المطلوب تطبيقها على كل عنصر
            n_workers: عدد العمال (الافتراضي: الكشف التلقائي)
            executor_type: نوع المنفّذ ('thread' أو 'process')
            description: وصف العملية لسجل الأحداث

        Returns:
            قائمة بالنتائج بنفس ترتيب العناصر الأصلية

        Raises:
            ValueError: إذا كانت قائمة العناصر فارغة

        Example:
            >>> pp = ParallelProcessor(max_workers=4)
            >>> results = pp.process_batch(
            ...     items=["file1.pdf", "file2.pdf"],
            ...     process_fn=extract_text,
            ...     executor_type='process',
            ... )
        """
        if not items:
            logger.warning("قائمة العناصر فارغة — items list is empty")
            return []

        workers = n_workers or self._max_workers
        total = len(items)
        desc = description or "معالجة الدُفعات"

        logger.info(
            "بدء معالجة %d عنصر بـ %d عامل (%s) — %s",
            total, workers, executor_type, desc,
        )

        self._reset_progress(total)
        results: List[Optional[Any]] = [None] * total

        try:
            with self._create_executor(executor_type, workers) as executor:
                # إرسال جميع المهام
                future_to_index: Dict[Future, int] = {}
                for idx, item in enumerate(items):
                    future = executor.submit(process_fn, item)
                    future_to_index[future] = idx

                # جمع النتائج عند اكتمالها
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        result = future.result()
                        results[idx] = result
                    except Exception as exc:
                        logger.error(
                            "[%s] خطأ في معالجة العنصر %d: %s",
                            desc, idx, exc,
                        )
                        results[idx] = None

                    self._update_progress(description=desc)

        except Exception as exc:
            logger.error("[%s] فشل في المعالجة المتوازية: %s", desc, exc)
            raise

        elapsed = time.time() - (self._start_time or time.time())
        logger.info(
            "[%s] اكتملت المعالجة — %d عنصر في %.2f ثانية",
            desc, total, elapsed,
        )
        return results

    # -----------------------------------------------------------------
    # معالجة الصفحات — Page-Level Processing
    # -----------------------------------------------------------------

    def process_pages(
        self,
        pages: Sequence[Any],
        ocr_fn: Callable[[Any, int], Any],
        max_workers: int = 4,
    ) -> List[Any]:
        """
        معالجة صفحات المستند بالتوازي — مُحسّن لعمليات OCR.
        Process document pages in parallel — optimized for OCR operations.

        هذه الدالة مخصصة لمعالجة الصفحات حيث يتم تمرير فهرس الصفحة
        إلى دالة OCR لتمكين التتبع والإبلاغ.

        Args:
            pages: مجموعة كائنات الصفحات
            ocr_fn: دالة OCR تستقبل (صفحة, فهرس) وتُرجع النتيجة
            max_workers: عدد العمال للتوازي (الافتراضي: 4)

        Returns:
            قائمة بنتائج OCR لكل صفحة

        Example:
            >>> pp = ParallelProcessor()
            >>> results = pp.process_pages(
            ...     pages=document.pages,
            ...     ocr_fn=lambda page, idx: run_ocr(page),
            ...     max_workers=4,
            ... )
        """
        if not pages:
            logger.warning("لا توجد صفحات للمعالجة — No pages to process")
            return []

        total = len(pages)
        logger.info(
            "بدء معالجة %d صفحة بـ %d عامل — Processing %d pages with %d workers",
            total, max_workers, total, max_workers,
        )

        self._reset_progress(total)
        results: List[Optional[Any]] = [None] * total

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_index: Dict[Future, int] = {}
                for idx, page in enumerate(pages):
                    future = executor.submit(ocr_fn, page, idx)
                    future_to_index[future] = idx

                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        result = future.result()
                        results[idx] = result
                    except Exception as exc:
                        logger.error(
                            "خطأ في معالجة الصفحة %d: %s — Error processing page %d: %s",
                            idx, exc, idx, exc,
                        )
                        results[idx] = None

                    self._update_progress(
                        description=f"معالجة الصفحات — Pages"
                    )

        except Exception as exc:
            logger.error("فشل في معالجة الصفحات: %s — Page processing failed: %s", exc, exc)
            raise

        elapsed = time.time() - (self._start_time or time.time())
        successful = sum(1 for r in results if r is not None)
        logger.info(
            "اكتملت معالجة الصفحات — %d/%d صفحة ناجحة في %.2f ثانية — "
            "%d/%d pages processed in %.2fs",
            successful, total, elapsed,
            successful, total, elapsed,
        )
        return results

    # -----------------------------------------------------------------
    # الخريطة مع التتبع — Map with Progress
    # -----------------------------------------------------------------

    def map_with_progress(
        self,
        items: Sequence[Any],
        fn: Callable[[Any], Any],
        n_workers: Optional[int] = None,
    ) -> List[Any]:
        """
        تطبيق دالة على مجموعة عناصر مع دعم التتبع.
        Apply a function to items with progress tracking support.

        تدعم هذه الدالة استخدام joblib عند توفره للحصول على
        أداء أفضل مع تتبع بصري للتقدم.

        Args:
            items: مجموعة العناصر
            fn: الدالة المطلوب تطبيقها
            n_workers: عدد العمال (الافتراضي: الكشف التلقائي)

        Returns:
            قائمة بالنتائج

        Example:
            >>> pp = ParallelProcessor()
            >>> texts = pp.map_with_progress(
            ...     items=image_paths,
            ...     fn=extract_text_from_image,
            ...     n_workers=4,
            ... )
        """
        if not items:
            logger.warning("قائمة العناصر فارغة في map_with_progress")
            return []

        workers = n_workers or self._max_workers
        total = len(items)

        # محاولة استخدام joblib إذا كان متاحًا
        try:
            from joblib import Parallel as JoblibParallel
            from joblib import delayed

            logger.info(
                "استخدام joblib لمعالجة %d عنصر بـ %d عامل — "
                "Using joblib for %d items with %d workers",
                total, workers, total, workers,
            )

            self._reset_progress(total)
            wrapped_fn = self._create_tracked_wrapper(fn, "joblib-map")
            results = JoblibParallel(
                n_jobs=workers,
                prefer="threads",
                backend="threading",
            )(delayed(wrapped_fn)(item) for item in items)

            return list(results)

        except ImportError:
            logger.info(
                "joblib غير متاح، استخدام ThreadPoolExecutor — "
                "joblib not available, falling back to ThreadPoolExecutor"
            )
            return self.process_batch(
                items=items,
                process_fn=fn,
                n_workers=workers,
                executor_type="thread",
                description="map_with_progress",
            )

    def _create_tracked_wrapper(
        self,
        fn: Callable[[Any], Any],
        label: str = "",
    ) -> Callable[[Any], Any]:
        """
        إنشاء غلاف لتنفيذ الدالة مع تتبع التقدم.
        Create a wrapper that executes the function with progress tracking.

        Args:
            fn: الدالة الأصلية
            label: تسمية للتتبع

        Returns:
            دالة مغلّفة مع تتبع التقدم
        """
        def _tracked_wrapper(item: Any) -> Any:
            try:
                result = fn(item)
                return result
            except Exception as exc:
                logger.error(
                    "[%s] خطأ في معالجة العنصر: %s — Error processing item: %s",
                    label, exc, exc,
                )
                raise
            finally:
                self._update_progress(description=label)

        return _tracked_wrapper

    # -----------------------------------------------------------------
    # المعالجة مع المهلة — Processing with Timeout
    # -----------------------------------------------------------------

    def process_with_timeout(
        self,
        items: Sequence[Any],
        fn: Callable[[Any], Any],
        timeout_per_item: float = 60,
        n_workers: Optional[int] = None,
    ) -> List[Any]:
        """
        معالجة العناصر مع مهلة زمنية لكل عنصر.
        Process items with a per-item timeout.

        إذا تجاوز عنصر المهلة المحددة، يُسجّل كفاشل ويُستمر
        مع بقية العناصر بدلًا من إيقاف المعالجة بالكامل.

        Args:
            items: مجموعة العناصر
            fn: الدالة المطلوب تطبيقها
            timeout_per_item: المهلة الزمنية لكل عنصر بالثواني (الافتراضي: 60)
            n_workers: عدد العمال (الافتراضي: الكشف التلقائي)

        Returns:
            قائمة بالنتائج (القيم الفاشلة تكون None)

        Example:
            >>> pp = ParallelProcessor()
            >>> results = pp.process_with_timeout(
            ...     items=urls,
            ...     fn=download_page,
            ...     timeout_per_item=30,
            ...     n_workers=8,
            ... )
        """
        if not items:
            logger.warning("قائمة العناصر فارغة في process_with_timeout")
            return []

        workers = n_workers or self._max_workers
        total = len(items)
        desc = f"process_with_timeout ({timeout_per_item}s)"

        logger.info(
            "بدء المعالجة مع مهلة — %d عنصر, مهلة: %.1f ث, عمال: %d",
            total, timeout_per_item, workers,
        )

        self._reset_progress(total)
        results: List[Optional[Any]] = [None] * total
        timeouts: int = 0
        errors: int = 0

        # إنشاء دالة مغلّفة مع المهلة
        def _timed_fn(item: Any) -> Any:
            return _wrap_with_timeout(fn, (item,), {}, timeout_per_item)

        try:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_index: Dict[Future, int] = {}
                for idx, item in enumerate(items):
                    future = executor.submit(_timed_fn, item)
                    future_to_index[future] = idx

                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        result = future.result()
                        results[idx] = result
                    except TimeoutError:
                        logger.warning(
                            "العنصر %d تجاوز المهلة (%.1f ث) — "
                            "Item %d timed out (%.1fs)",
                            idx, timeout_per_item,
                            idx, timeout_per_item,
                        )
                        results[idx] = None
                        timeouts += 1
                    except Exception as exc:
                        logger.error(
                            "خطأ في العنصر %d: %s — Error on item %d: %s",
                            idx, exc, idx, exc,
                        )
                        results[idx] = None
                        errors += 1

                    self._update_progress(description=desc)

        except Exception as exc:
            logger.error("فشل في المعالجة مع المهلة: %s", exc)
            raise

        elapsed = time.time() - (self._start_time or time.time())
        successful = total - timeouts - errors
        logger.info(
            "اكتملت المعالجة مع المهلة — ناجح: %d, مهلات: %d, أخطاء: %d — %.2f ثانية — "
            "Completed: %d successful, %d timeouts, %d errors — %.2fs",
            successful, timeouts, errors, elapsed,
            successful, timeouts, errors, elapsed,
        )
        return results

    # -----------------------------------------------------------------
    # معلومات إحصائية — Statistics
    # -----------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        الحصول على إحصائيات المعالج المتوازي.
        Get statistics about the parallel processor.

        Returns:
            قاموس يحتوي على إحصائيات الأداء
        """
        elapsed = 0.0
        if self._start_time is not None:
            elapsed = time.time() - self._start_time

        return {
            "max_workers": self._max_workers,
            "optimal_workers": self.optimal_workers,
            "default_executor_type": self._default_executor_type,
            "completed_count": self._completed_count,
            "total_count": self._total_count,
            "elapsed_seconds": round(elapsed, 2),
        }

    def __repr__(self) -> str:
        """تمثيل نصي للمعالج المتوازي."""
        return (
            f"ParallelProcessor("
            f"max_workers={self._max_workers}, "
            f"executor='{self._default_executor_type}')"
        )
