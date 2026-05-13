"""
وحدة تتبّع التقدّم — Progress Tracking Module
================================================

نظام شامل لتتبّع التقدّم مع دعم الاستدعاءات الراجعة (callbacks) والعروض
المرئية. يوفر تتبّعاً متعدد المستويات (خطوة + عنصر داخل الخطوة)، وتوقيتاً
لكل خطوة، وآماناً للخيوط (thread-safe)، ونصوصاً عربية وإنجليزية.

A comprehensive progress tracking system with callback support, console
rendering, nested progress, per-step timing, and thread safety.

المكونات الرئيسية — Key Components:
- ProgressCallback: توقيعات الاستدعاءات الراجعة (callback signatures)
- ProgressTracker: المتتبّع الأساسي الآمن للخيوط
- ProgressRenderer: عارض التقدّم للطرفية (console renderer)
- PipelineStep: تعريف خطوة في خط المعالجة (pipeline step definition)
- ProcessingPipeline: مشغّل خطوات المعالجة (pipeline orchestrator)
- create_progress_callback: مصنع للأنماط الشائعة (callback factory)
- progress_to_logger: توجيه التقدّم إلى المسجّل (logger adapter)

مثال سريع — Quick Example:
    >>> tracker = ProgressTracker(total_steps=3, description="معالجة المستند")
    >>> tracker.add_callback(ProgressRenderer())
    >>> tracker.start_step("استخراج النص")
    >>> tracker.complete_step("استخراج النص")
    >>> tracker.start_step("التعرف الضوئي")
    >>> tracker.update_progress(5, 10, "معالجة الصفحة 5 من 10")
    >>> tracker.complete_step("التعرف الضوئي")

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    runtime_checkable,
)

# --- إعداد المسجل — Logger Setup ---
logger = logging.getLogger(__name__)


# =====================================================================
# توقيعات الاستدعاءات الراجعة — Callback Signatures / Protocols
# =====================================================================

@runtime_checkable
class ProgressCallback(Protocol):
    """
    بروتوكول الاستدعاء الراجع لتتبّع التقدّم.
    Callback protocol for progress tracking.

    يجب أن تطبّق أي فئة تريد تلقّي أحداث التقدّم هذا البروتوكول.
    جميع الطرق اختيارية — يمكن للفئة تنفيذ ما تحتاجه فقط.
    """

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """
        يُستدعى عند بدء خطوة جديدة.
        Called when a new step starts.

        Args:
            step_name: اسم الخطوة (مثلاً: "استخراج النص من PDF")
            step_index: فهرس الخطوة (يبدأ من 0)
            total_steps: العدد الإجمالي للخطوات
        """
        ...

    def on_step_complete(
        self,
        step_name: str,
        duration: float,
        result: Any = None,
    ) -> None:
        """
        يُستدعى عند اكتمال خطوة.
        Called when a step completes.

        Args:
            step_name: اسم الخطوة
            duration: مدة التنفيذ بالثواني
            result: نتيجة الخطوة (اختياري)
        """
        ...

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """
        يُستدعى عند تحديث التقدّم داخل خطوة.
        Called when progress is updated within a step.

        Args:
            current: العنصر الحالي
            total: العدد الإجمالي
            message: رسالة توضيحية
            percentage: النسبة المئوية (0.0 – 100.0)
        """
        ...

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """
        يُستدعى عند حدوث خطأ في خطوة.
        Called when an error occurs in a step.

        Args:
            step_name: اسم الخطوة التي حدث فيها الخطأ
            error: الاستثناء (exception) الذي حدث
        """
        ...

    def on_complete(
        self,
        total_duration: float,
        results_summary: Dict[str, Any],
    ) -> None:
        """
        يُستدعى عند اكتمال جميع الخطوات.
        Called when all steps are complete.

        Args:
            total_duration: المدة الإجمالية بالثواني
            results_summary: ملخص النتائج لكل خطوة
        """
        ...


# =====================================================================
# دالة الاستدعاء الراجع العامة — Generic Callback Function Type
# =====================================================================

CallbackFn = Callable[..., None]
"""
نوع عام لدوال الاستدعاء الراجع.
Generic type for callback functions.
يمكن أن يكون دالة أو أي كائن قابل للاستدعاء.
"""


# =====================================================================
# بيانات خطوة التقدّم — StepProgress Data
# =====================================================================

@dataclass
class StepProgress:
    """
    بيانات تقدّم خطوة واحدة.
    Progress data for a single step.

    تُستخدم داخل ProgressTracker لتخزين حالة كل خطوة.
    """
    name: str
    """اسم الخطوة — Step name"""

    index: int = 0
    """فهرس الخطوة — Step index (0-based)"""

    start_time: Optional[float] = None
    """وقت البدء (timestamp) — Start timestamp"""

    end_time: Optional[float] = None
    """وقت الانتهاء (timestamp) — End timestamp"""

    duration: float = 0.0
    """مدة التنفيذ بالثواني — Duration in seconds"""

    current: int = 0
    """العنصر الحالي داخل الخطوة — Current item within step"""

    total: int = 0
    """العدد الإجمالي داخل الخطوة — Total items within step"""

    message: str = ""
    """آخر رسالة تقدّم — Latest progress message"""

    result: Any = None
    """نتيجة الخطوة — Step result"""

    status: str = "pending"
    """حالة الخطوة: pending | running | completed | error — Step status"""

    error: Optional[Exception] = None
    """الخطأ الذي حدث (إن وُجد) — Error that occurred"""

    @property
    def percentage(self) -> float:
        """النسبة المئوية للتقدّم داخل الخطوة — Progress percentage within step."""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100.0)


# =====================================================================
# فئة المتتبّع الأساسي — ProgressTracker Class
# =====================================================================

class ProgressTracker:
    """
    متتبّع تقدّم آمن للخيوط مع دعم الاستدعاءات الراجعة.
    Thread-safe progress tracker with callback support.

    يدعم هذا المتتبّع:
    - تتبّع خطوات متعددة بالتتابع
    - تقدّم متداخل (خطوة + عناصر داخلها)
    - توقيت دقيق لكل خطوة
    - إضافة/حذف استدعاءات راجعة ديناميكياً
    - آمن للاستخدام من عدة خيوط

    Example:
        >>> tracker = ProgressTracker(total_steps=4, description="OCR Pipeline")
        >>> renderer = ProgressRenderer()
        >>> tracker.add_callback(renderer)
        >>>
        >>> tracker.start_step("Extracting text from PDF...")
        >>> for i, page in enumerate(pages):
        ...     result = process_page(page)
        ...     tracker.update_progress(i + 1, len(pages), f"Page {i+1}/{len(pages)}")
        >>> tracker.complete_step("Extracting text from PDF...", result=text)
    """

    def __init__(
        self,
        total_steps: int,
        description: str = "",
        callbacks: Optional[List[ProgressCallback]] = None,
    ) -> None:
        """
        تهيئة متتبّع التقدّم.
        Initialize the progress tracker.

        Args:
            total_steps: العدد الإجمالي للخطوات المتوقعة
            description: وصف عام لعملية المعالجة
            callbacks: قائمة مبدئية من الاستدعاءات الراجعة
        """
        self._total_steps: int = total_steps
        self._description: str = description
        self._callbacks: List[ProgressCallback] = list(callbacks or [])
        self._lock: threading.Lock = threading.Lock()

        # حالة الخطوات
        self._steps: Dict[str, StepProgress] = {}
        self._step_order: List[str] = []
        self._current_step: Optional[str] = None
        self._completed_steps: int = 0

        # التوقيت العام
        self._start_time: float = time.time()
        self._end_time: Optional[float] = None

        # حالة الخطأ
        self._error: Optional[Exception] = None
        self._has_error: bool = False

        logger.debug(
            "تم تهيئة متتبّع التقدّم — خطوات: %d, وصف: '%s' — "
            "ProgressTracker initialized — steps: %d, desc: '%s'",
            total_steps, description,
            total_steps, description,
        )

    # -----------------------------------------------------------------
    # إدارة الاستدعاءات الراجعة — Callback Management
    # -----------------------------------------------------------------

    def add_callback(self, callback_fn: ProgressCallback) -> None:
        """
        إضافة استدعاع راجع لاستقبال أحداث التقدّم.
        Add a callback to receive progress events.

        Args:
            callback_fn: كائن يطبّق بروتوكول ProgressCallback
                        أو دالة callable تقبل معاملات on_progress

        Example:
            >>> tracker.add_callback(ProgressRenderer())
            >>> tracker.add_callback(progress_to_logger(logger))
        """
        with self._lock:
            if callback_fn not in self._callbacks:
                self._callbacks.append(callback_fn)
                logger.debug("تمت إضافة استدعاع راجع — Callback added: %s", callback_fn)

    def remove_callback(self, callback_fn: ProgressCallback) -> None:
        """
        إزالة استدعاع راجع.
        Remove a callback.

        Args:
            callback_fn: الكائن المراد إزالته

        Returns:
            bool: True إذا تمت الإزالة بنجاح، False إذا لم يكن موجوداً
        """
        with self._lock:
            try:
                self._callbacks.remove(callback_fn)
                logger.debug("تمت إزالة الاستدعاع الراجع — Callback removed: %s", callback_fn)
            except ValueError:
                logger.debug(
                    "الاستدعاع الراجع غير موجود للإزالة — Callback not found: %s",
                    callback_fn,
                )

    def _notify(
        self,
        event_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        إرسال إشعار لجميع الاستدعاءات الراجعة.
        Notify all registered callbacks of an event.

        Args:
            event_name: اسم الحدث (مثلاً: on_step_start)
            *args: معاملات الموقع للحدث
            **kwargs: معاملات التسمية للحدث
        """
        with self._lock:
            callbacks = list(self._callbacks)

        for callback in callbacks:
            try:
                method = getattr(callback, event_name, None)
                if callable(method):
                    method(*args, **kwargs)
            except Exception as exc:
                logger.warning(
                    "خطأ في الاستدعاع الراجع '%s': %s — Callback error in '%s': %s",
                    event_name, exc, event_name, exc,
                )

    # -----------------------------------------------------------------
    # إدارة الخطوات — Step Management
    # -----------------------------------------------------------------

    def start_step(self, step_name: str) -> None:
        """
        بدء خطوة جديدة.
        Start a new processing step.

        Args:
            step_name: اسم الخطوة (يُستخدم كمفتاح فريد)

        Example:
            >>> tracker.start_step("Extracting text from PDF...")
            >>> # ... معالجة ...
            >>> tracker.complete_step("Extracting text from PDF...", result=text)
        """
        with self._lock:
            # تحديث حالة الخطوة السابقة إن وُجدت
            if self._current_step and self._current_step in self._steps:
                prev = self._steps[self._current_step]
                if prev.status == "running":
                    prev.end_time = time.time()
                    prev.duration = prev.end_time - (prev.start_time or prev.end_time)
                    prev.status = "completed"

            # إنشاء خطوة جديدة
            step_index = len(self._step_order)
            step = StepProgress(
                name=step_name,
                index=step_index,
                start_time=time.time(),
                status="running",
            )

            self._steps[step_name] = step
            self._step_order.append(step_name)
            self._current_step = step_name

            # تحديث العدد الإجمالي ديناميكياً إذا لزم
            if step_index >= self._total_steps:
                self._total_steps = step_index + 1

        # إرسال الإشعار
        self._notify(
            "on_step_start",
            step_name=step_name,
            step_index=step_index,
            total_steps=self._total_steps,
        )

        logger.info(
            "[%d/%d] بدء الخطوة: '%s' — Step started: '%s'",
            step_index + 1, self._total_steps, step_name,
            step_index + 1, self._total_steps, step_name,
        )

    def complete_step(
        self,
        step_name: str,
        result: Any = None,
    ) -> None:
        """
        إكمال خطوة وتسجيل نتيجتها.
        Complete a step and record its result.

        Args:
            step_name: اسم الخطوة
            result: نتيجة الخطوة (اختياري)

        Raises:
            ValueError: إذا لم تكن الخطوة موجودة
        """
        with self._lock:
            if step_name not in self._steps:
                raise ValueError(
                    f"الخطوة غير موجودة: '{step_name}' — "
                    f"Step not found: '{step_name}'"
                )

            step = self._steps[step_name]
            step.end_time = time.time()
            step.duration = step.end_time - (step.start_time or step.end_time)
            step.status = "completed"
            step.result = result

            self._completed_steps += 1

            # التحقق من اكتمال جميع الخطوات
            # نستخدم _total_steps لأن _step_order قد لا يحتوي على جميع الخطوات بعد
            # Use _total_steps because _step_order may not contain all steps yet
            all_done = self._completed_steps >= self._total_steps

        # إرسال إشعار اكتمال الخطوة
        self._notify(
            "on_step_complete",
            step_name=step_name,
            duration=step.duration,
            result=result,
        )

        logger.info(
            "[%d/%d] اكتملت الخطوة: '%s' (%.2f ث) — Step completed: '%s' (%.2fs)",
            step.index + 1, self._total_steps, step_name, step.duration,
            step.index + 1, self._total_steps, step_name, step.duration,
        )

        # إرسال إشعار اكتمال الكل
        if all_done:
            self._end_time = time.time()
            total_duration = self._end_time - self._start_time
            summary = self._build_summary(total_duration)

            self._notify(
                "on_complete",
                total_duration=total_duration,
                results_summary=summary,
            )

            logger.info(
                "اكتملت جميع الخطوات (%.2f ث) — All steps completed (%.2fs)",
                total_duration, total_duration,
            )

    def fail_step(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """
        تسجيل فشل خطوة.
        Record a step failure.

        Args:
            step_name: اسم الخطوة
            error: الاستثناء الذي سبّب الفشل
        """
        with self._lock:
            if step_name not in self._steps:
                raise ValueError(
                    f"الخطوة غير موجودة: '{step_name}' — "
                    f"Step not found: '{step_name}'"
                )

            step = self._steps[step_name]
            step.end_time = time.time()
            step.duration = step.end_time - (step.start_time or step.end_time)
            step.status = "error"
            step.error = error

            self._error = error
            self._has_error = True

        # إرسال إشعار الخطأ
        self._notify("on_error", step_name=step_name, error=error)

        logger.error(
            "فشلت الخطوة: '%s' — خطأ: %s — Step failed: '%s' — error: %s",
            step_name, error,
            step_name, error,
        )

    # -----------------------------------------------------------------
    # تحديث التقدّم — Progress Updates
    # -----------------------------------------------------------------

    def update_progress(
        self,
        current: int,
        total: int,
        message: str = "",
    ) -> None:
        """
        تحديث التقدّم داخل الخطوة الحالية.
        Update progress within the current step.

        Args:
            current: العنصر/الصفحة الحالية
            total: العدد الإجمالي للعناصر/الصفحات
            message: رسالة توضيحية

        Example:
            >>> tracker.start_step("Applying OCR...")
            >>> for i, page in enumerate(pages):
            ...     ocr_page(page)
            ...     tracker.update_progress(i + 1, len(pages), f"Processing page {i+1}")
            >>> tracker.complete_step("Applying OCR...", result=results)
        """
        with self._lock:
            step_name = self._current_step
            if step_name is None:
                logger.warning(
                    "لا توجد خطوة جارية لتحديث التقدّم — "
                    "No active step to update progress"
                )
                return

            step = self._steps.get(step_name)
            if step is None:
                return

            step.current = current
            step.total = max(total, 1)
            step.message = message

            percentage = step.percentage

        # حساب النسبة المئوية الإجمالية عبر جميع الخطوات
        overall = self._calculate_overall_percentage()

        # إرسال إشعار التقدّم
        self._notify(
            "on_progress",
            current=current,
            total=total,
            message=message,
            percentage=percentage,
        )

    def set_total(self, total: int) -> None:
        """
        تحديث العدد الإجمالي للخطوات.
        Update the total number of steps.

        مفيد عندما لا يكون العدد معروفاً مسبقاً وقت التهيئة.

        Args:
            total: العدد الإجمالي الجديد
        """
        with self._lock:
            self._total_steps = max(total, 1)
        logger.debug(
            "تم تحديث العدد الإجمالي للخطوات: %d — Total steps updated: %d",
            total, total,
        )

    def set_step_total(
        self,
        step_name: str,
        total: int,
    ) -> None:
        """
        تحديد العدد الإجمالي للعناصر داخل خطوة.
        Set the total number of items within a step.

        Args:
            step_name: اسم الخطوة
            total: العدد الإجمالي للعناصر
        """
        with self._lock:
            if step_name in self._steps:
                self._steps[step_name].total = max(total, 1)

    # -----------------------------------------------------------------
    # حالة التقدّم — Progress State
    # -----------------------------------------------------------------

    def get_progress(self) -> Dict[str, Any]:
        """
        الحصول على حالة التقدّم الحالية كقاموس.
        Get the current progress state as a dictionary.

        Returns:
            قاموس يحتوي على:
            - description: وصف العملية
            - total_steps: العدد الإجمالي للخطوات
            - completed_steps: الخطوات المكتملة
            - current_step: الخطوة الحالية
            - current_step_progress: تقدّم الخطوة الحالية (نسبة مئوية)
            - overall_percentage: النسبة المئوية الإجمالية
            - elapsed_seconds: الوقت المنقضي
            - has_error: هل حدث خطأ
            - steps: تفاصيل كل خطوة

        Example:
            >>> state = tracker.get_progress()
            >>> print(f"Overall: {state['overall_percentage']:.1f}%")
        """
        with self._lock:
            current_step_data: Optional[Dict[str, Any]] = None
            current_step_pct: float = 0.0

            if self._current_step and self._current_step in self._steps:
                step = self._steps[self._current_step]
                current_step_data = {
                    "name": step.name,
                    "index": step.index,
                    "current": step.current,
                    "total": step.total,
                    "percentage": round(step.percentage, 1),
                    "message": step.message,
                    "status": step.status,
                    "elapsed": round(step.duration, 2),
                }
                current_step_pct = step.percentage

            # حساب النسبة الإجمالية
            overall_pct = self._calculate_overall_percentage_unlocked()

            # وقت منقضي
            elapsed = 0.0
            if self._end_time is not None:
                elapsed = self._end_time - self._start_time
            else:
                elapsed = time.time() - self._start_time

            # تفاصيل الخطوات
            steps_details: List[Dict[str, Any]] = []
            for name in self._step_order:
                s = self._steps[name]
                steps_details.append({
                    "name": s.name,
                    "index": s.index,
                    "status": s.status,
                    "duration": round(s.duration, 2),
                    "percentage": round(s.percentage, 1),
                    "current": s.current,
                    "total": s.total,
                    "message": s.message,
                    "error": str(s.error) if s.error else None,
                })

            return {
                "description": self._description,
                "total_steps": self._total_steps,
                "completed_steps": self._completed_steps,
                "current_step": current_step_data,
                "current_step_percentage": round(current_step_pct, 1),
                "overall_percentage": round(overall_pct, 1),
                "elapsed_seconds": round(elapsed, 2),
                "has_error": self._has_error,
                "error": str(self._error) if self._error else None,
                "steps": steps_details,
            }

    def _calculate_overall_percentage(self) -> float:
        """حساب النسبة المئوية الإجمالية (مع القفل)."""
        with self._lock:
            return self._calculate_overall_percentage_unlocked()

    def _calculate_overall_percentage_unlocked(self) -> float:
        """حساب النسبة المئوية الإجمالية (بدون قفل — يجب استدعاؤها ضمن قسم محمي)."""
        if self._total_steps <= 0:
            return 0.0

        # مساهمة الخطوات المكتملة
        completed_contribution = (self._completed_steps / self._total_steps) * 100.0

        # مساهمة الخطوة الحالية
        current_contribution = 0.0
        if self._current_step and self._current_step in self._steps:
            step = self._steps[self._current_step]
            if step.status == "running":
                step_fraction = step.percentage / 100.0 if step.total > 0 else 0.0
                current_contribution = (step_fraction / self._total_steps) * 100.0

        return min(100.0, completed_contribution + current_contribution)

    def _build_summary(self, total_duration: float) -> Dict[str, Any]:
        """بناء ملخص النتائج النهائي."""
        steps_summary: Dict[str, Any] = {}
        for name in self._step_order:
            s = self._steps[name]
            steps_summary[name] = {
                "duration": round(s.duration, 2),
                "status": s.status,
                "result": s.result,
                "error": str(s.error) if s.error else None,
            }

        return {
            "description": self._description,
            "total_steps": self._total_steps,
            "completed_steps": self._completed_steps,
            "total_duration": round(total_duration, 2),
            "has_error": self._has_error,
            "steps": steps_summary,
        }

    # -----------------------------------------------------------------
    # سياق المساعد — Context Manager Support
    # -----------------------------------------------------------------

    def step(self, step_name: str) -> "_StepContext":
        """
        إنشاء سياق لإدارة خطوة تلقائياً.
        Create a context manager for automatic step lifecycle.

        Args:
            step_name: اسم الخطوة

        Returns:
            سياق يبدأ الخطوة عند الدخول ويُكملها عند الخروج

        Example:
            >>> with tracker.step("Extracting text..."):
            ...     text = extract_text(pdf)
            >>> # الخطوة اكتملت تلقائياً
        """
        return _StepContext(self, step_name)

    # -----------------------------------------------------------------
    # تمثيل نصي — String Representation
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        """تمثيل نصي للمتتبّع."""
        return (
            f"ProgressTracker("
            f"steps={self._completed_steps}/{self._total_steps}, "
            f"description='{self._description}')"
        )


# =====================================================================
# سياق الخطوة — Step Context Manager
# =====================================================================

class _StepContext:
    """
    مدير سياق لتغليف دورة حياة الخطوة.
    Context manager wrapping a step's lifecycle.

    يبدأ الخطوة عند الدخول ويُكملها عند الخروج.
    In case of error, the step is marked as failed.

    Example:
        >>> with tracker.step("Analyzing layout..."):
        ...     layout = analyze_layout(document)
    """

    def __init__(self, tracker: ProgressTracker, step_name: str) -> None:
        self._tracker = tracker
        self._step_name = step_name
        self._result: Any = None

    def __enter__(self) -> "_StepContext":
        self._tracker.start_step(self._step_name)
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        if exc_type is not None and exc_val is not None:
            self._tracker.fail_step(self._step_name, exc_val)
        else:
            self._tracker.complete_step(self._step_name, result=self._result)

    def set_result(self, result: Any) -> None:
        """
        تعيين نتيجة الخطوة.
        Set the step result.
        """
        self._result = result


# =====================================================================
# فئة عارض التقدّم — ProgressRenderer Class
# =====================================================================

class ProgressRenderer:
    """
    عارض التقدّم للطرفية مع شريط تقدّم بصري.
    Console-based progress renderer with visual progress bar.

    يدعم وضعين:
    - الطرفية (terminal): شريط متحرك مع إرجاع الحامل (\\r)
    - السجل (log): أسطر منفصلة بدون إرجاع الحامل

    Features:
    - شريط تقدّم بصري مع رموز Unicode
    - عرض الوقت المنقضي والوقت المتبقّي المتوقع
    - عرض الخطوة الحالية والنسبة الإجمالية
    - ألوان ANSI (اختيارية)

    Example:
        >>> tracker = ProgressTracker(total_steps=3)
        >>> tracker.add_callback(ProgressRenderer(use_colors=True))
    """

    # أحرف شريط التقدّم — Progress bar characters
    FILLED: str = "█"
    """حرف الجزء المكتمل — Filled bar character"""

    EMPTY: str = "░"
    """حرف الجزء الفارغ — Empty bar character"""

    HEAD: str = "▓"
    """حرف رأس التقدّم — Progress head character"""

    BAR_WIDTH: int = 30
    """عرض شريط التقدّم بالأحرف — Progress bar width in characters"""

    def __init__(
        self,
        bar_width: int = 30,
        use_colors: bool = False,
        terminal_mode: bool = True,
        show_eta: bool = True,
    ) -> None:
        """
        تهيئة عارض التقدّم.
        Initialize the progress renderer.

        Args:
            bar_width: عرض شريط التقدّم بالأحرف
            use_colors: استخدام ألوان ANSI (فقط في الطرفية)
            terminal_mode: وضع الطرفية (\\r) أو وضع السجل
            show_eta: عرض الوقت المتبقّي المتوقع
        """
        self._bar_width: int = max(bar_width, 10)
        self._use_colors: bool = use_colors and self._supports_color()
        self._terminal_mode: bool = terminal_mode
        self._show_eta: bool = show_eta
        self._last_print_length: int = 0
        self._step_start_time: Optional[float] = None
        self._step_item_total: int = 0

    @staticmethod
    def _supports_color() -> bool:
        """
        فحص ما إذا كانت الطرفية تدعم الألوان.
        Check if the terminal supports ANSI colors.
        """
        if not hasattr(sys.stdout, "isatty"):
            return False
        if not sys.stdout.isatty():
            return False
        # فحص بيئة Windows
        if sys.platform == "win32":
            return os.environ.get("ANSICON") is not None or "color" in os.environ
        return True

    def _color(self, text: str, color_code: str) -> str:
        """تلوين النص إذا كانت الألوان مفعّلة."""
        if not self._use_colors:
            return text
        return f"\033[{color_code}m{text}\033[0m"

    def _green(self, text: str) -> str:
        """نص أخضر — Green text."""
        return self._color(text, "32")

    def _yellow(self, text: str) -> str:
        """نص أصفر — Yellow text."""
        return self._color(text, "33")

    def _red(self, text: str) -> str:
        """نص أحمر — Red text."""
        return self._color(text, "31")

    def _cyan(self, text: str) -> str:
        """نص سماوي — Cyan text."""
        return self._color(text, "36")

    def _bold(self, text: str) -> str:
        """نص عريض — Bold text."""
        return self._color(text, "1")

    def _format_duration(self, seconds: float) -> str:
        """
        تنسيق المدة الزمنية بشكل مقروء.
        Format duration in a human-readable way.
        """
        if seconds < 0.001:
            return "0.0s"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"

    def _build_bar(self, percentage: float) -> str:
        """
        بناء شريط التقدّم المرئي.
        Build the visual progress bar.

        Args:
            percentage: النسبة المئوية (0.0 – 100.0)

        Returns:
            سلسلة نصية تمثّل شريط التقدّم
        """
        pct = max(0.0, min(100.0, percentage))
        filled_count = int((pct / 100.0) * self._bar_width)

        if filled_count >= self._bar_width:
            bar = self.FILLED * self._bar_width
        elif filled_count > 0:
            bar = (
                self.FILLED * (filled_count - 1)
                + self.HEAD
                + self.EMPTY * (self._bar_width - filled_count)
            )
        else:
            bar = self.EMPTY * self._bar_width

        # تلوين الشريط
        if self._use_colors:
            if pct >= 100:
                bar = self._green(bar)
            elif pct >= 50:
                bar = self._cyan(bar)
            elif pct >= 25:
                bar = self._yellow(bar)

        return f"|{bar}|"

    def _print_line(self, line: str) -> None:
        """
        طباعة سطر مع تنظيف السطر السابق في وضع الطرفية.
        Print a line, clearing the previous line in terminal mode.
        """
        try:
            if self._terminal_mode and sys.stdout.isatty():
                # تنظيف السطر السابق
                clear = " " * max(self._last_print_length, len(line))
                sys.stdout.write(f"\r{clear}\r")
                sys.stdout.write(line)
                sys.stdout.flush()
                self._last_print_length = len(line)
            else:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
                self._last_print_length = 0
        except Exception:
            # تجاهل أخطاء الطباعة في بيئات غير تفاعلية
            pass

    def _finalize(self) -> None:
        """
        إنهاء السطر الحالي في وضع الطرفية.
        Finalize the current line in terminal mode.
        """
        try:
            if self._terminal_mode and self._last_print_length > 0:
                sys.stdout.write("\n")
                sys.stdout.flush()
                self._last_print_length = 0
        except Exception:
            pass

    # -----------------------------------------------------------------
    # أحداث الاستدعاع الراجع — Callback Event Implementations
    # -----------------------------------------------------------------

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """
        عرض بداية الخطوة.
        Display step start.

        Args:
            step_name: اسم الخطوة
            step_index: فهرس الخطوة
            total_steps: العدد الإجمالي
        """
        self._finalize()
        self._step_start_time = time.time()
        self._step_item_total = 0

        # حساب النسبة الإجمالية المبدئية للخطوة
        if total_steps > 0:
            overall_pct = (step_index / total_steps) * 100.0
        else:
            overall_pct = 0.0

        step_label = self._bold(f"Step {step_index + 1}/{total_steps}")
        line = (
            f"\n{self._cyan('▶')} {step_label}: "
            f"{self._bold(step_name)} "
            f"[{self._format_bar_mini(overall_pct)}]"
        )
        self._print_line(line)

    def on_step_complete(
        self,
        step_name: str,
        duration: float,
        result: Any = None,
    ) -> None:
        """
        عرض اكتمال الخطوة.
        Display step completion.

        Args:
            step_name: اسم الخطوة
            duration: المدة بالثواني
            result: نتيجة الخطوة
        """
        self._finalize()
        line = (
            f"  {self._green('✓')} {step_name} — "
            f"{self._green(self._format_duration(duration))}"
        )
        self._print_line(line)

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """
        عرض تحديث التقدّم مع شريط بصري.
        Display progress update with visual bar.

        Args:
            current: العنصر الحالي
            total: العدد الإجمالي
            message: رسالة توضيحية
            percentage: النسبة المئوية
        """
        bar = self._build_bar(percentage)
        pct_str = f"{percentage:5.1f}%"
        count_str = f"{current}/{total}"

        # حساب الوقت المتبقّي المتوقع
        eta_str = ""
        if self._show_eta and self._step_start_time is not None and current > 0:
            elapsed = time.time() - self._step_start_time
            rate = current / elapsed if elapsed > 0 else 0
            if rate > 0:
                remaining = (total - current) / rate
                eta_str = f" ETA: {self._format_duration(remaining)}"

        msg_part = f"  {message}" if message else ""

        line = (
            f"  {bar} {pct_str}  "
            f"({count_str}){eta_str}{msg_part}"
        )
        self._print_line(line)

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """
        عرض رسالة الخطأ.
        Display error message.

        Args:
            step_name: اسم الخطوة
            error: الاستثناء
        """
        self._finalize()
        line = (
            f"  {self._red('✗')} {self._red(step_name)} — "
            f"{self._red(str(error))}"
        )
        self._print_line(line)

    def on_complete(
        self,
        total_duration: float,
        results_summary: Dict[str, Any],
    ) -> None:
        """
        عرض رسالة اكتمال الكل.
        Display overall completion message.

        Args:
            total_duration: المدة الإجمالية
            results_summary: ملخص النتائج
        """
        self._finalize()

        has_error = results_summary.get("has_error", False)
        completed = results_summary.get("completed_steps", 0)
        total = results_summary.get("total_steps", 0)

        if has_error:
            icon = self._red("⚠")
            status = self._red("completed with errors")
        else:
            icon = self._green("✓")
            status = self._green("completed successfully")

        line = (
            f"\n{icon} Pipeline {status} — "
            f"{completed}/{total} steps — "
            f"Total: {self._format_duration(total_duration)}\n"
        )
        self._print_line(line)

    # -----------------------------------------------------------------
    # أدوات مساعدة — Utility Methods
    # -----------------------------------------------------------------

    @staticmethod
    def _format_bar_mini(percentage: float) -> str:
        """
        تنسيق شريط تقدّم مصغّر (10 أحرف).
        Format a mini progress bar (10 characters wide).
        """
        pct = max(0.0, min(100.0, percentage))
        filled = int((pct / 100.0) * 10)
        return "█" * filled + "░" * (10 - filled)


# =====================================================================
# استيراد os للفحص — Import os for terminal detection
# =====================================================================
import os  # noqa: E402 (مطلوب لـ _supports_color)


# =====================================================================
# تعريف خطوة خط المعالجة — PipelineStep Dataclass
# =====================================================================

@dataclass
class PipelineStep:
    """
    تعريف خطوة في خط المعالجة.
    Definition of a step in a processing pipeline.

    كل خطوة لها اسم، دالة تنفيذ، وصف، وتبعيات محتملة.

    Example:
        >>> step = PipelineStep(
        ...     name="ocr",
        ...     fn=run_ocr,
        ...     description="Applying OCR to document",
        ...     depends_on=["extract"],
        ... )
    """
    name: str
    """
    اسم الخطوة — فريد داخل خط المعالجة.
    Step name — must be unique within the pipeline.
    """

    fn: Callable[..., Any]
    """
    دالة التنفيذ — تُستدعى عند تشغيل الخطوة.
    Execution function — called when the step runs.
    يمكن أن تقبل معاملات أو لا تقبل أي معامل.
    """

    description: str = ""
    """
    وصف الخطوة للعرض.
    Step description for display purposes.
    """

    depends_on: Optional[List[str]] = field(default_factory=list)
    """
    أسماء الخطوات التي يجب إكمالها قبل هذه الخطوة.
    Names of steps that must complete before this step runs.
    إذا كانت القائمة فارغة، يمكن تنفيذ الخطوة مباشرة.
    """

    timeout: Optional[float] = None
    """
    مهلة زمنية اختيارية بالثواني.
    Optional timeout in seconds. If None, no timeout.
    """

    retry_count: int = 0
    """
    عدد محاولات إعادة المحاولة عند الفشل.
    Number of retry attempts on failure.
    """

    def __post_init__(self) -> None:
        """التأكد من أن depends_on قائمة وليست None."""
        if self.depends_on is None:
            self.depends_on = []


# =====================================================================
# فئة خط المعالجة — ProcessingPipeline Class
# =====================================================================

class ProcessingPipeline:
    """
    خط معالجة أعلى مستوى يجمع بين ProgressTracker وتنفيذ الخطوات.
    Higher-level processing pipeline combining ProgressTracker and step execution.

    يدعم:
    - تنفيذ الخطوات بالتتابع (الافتراضي)
    - تنفيذ خطوات مستقلة بالتوازي (بناءً على التبعيات)
    - تتبّع التقدّم الشامل مع نسب مئوية
    - إعادة المحاولة عند الفشل
    - مهلات زمنية لكل خطوة

    Example:
        >>> pipeline = ProcessingPipeline(description="Document Processing")
        >>> pipeline.add_step(PipelineStep(
        ...     name="extract",
        ...     fn=extract_text,
        ...     description="Extracting text from PDF...",
        ... ))
        >>> pipeline.add_step(PipelineStep(
        ...     name="ocr",
        ...     fn=run_ocr,
        ...     description="Applying OCR...",
        ...     depends_on=["extract"],
        ... ))
        >>> results = pipeline.run()
    """

    def __init__(
        self,
        description: str = "",
        callbacks: Optional[List[ProgressCallback]] = None,
    ) -> None:
        """
        تهيئة خط المعالجة.
        Initialize the processing pipeline.

        Args:
            description: وصف عام لخط المعالجة
            callbacks: قائمة مبدئية من الاستدعاءات الراجعة
        """
        self._description: str = description
        self._steps: List[PipelineStep] = []
        self._callbacks: List[ProgressCallback] = list(callbacks or [])
        self._results: Dict[str, Any] = {}
        self._tracker: Optional[ProgressTracker] = None

    def add_step(self, step: PipelineStep) -> "ProcessingPipeline":
        """
        إضافة خطوة لخط المعالجة.
        Add a step to the pipeline.

        Args:
            step: الخطوة المراد إضافتها

        Returns:
            self (للسلسلة — method chaining)

        Example:
            >>> pipeline.add_step(PipelineStep(
            ...     name="step1", fn=func1, description="First step"
            ... )).add_step(PipelineStep(
            ...     name="step2", fn=func2, description="Second step"
            ... ))
        """
        # فحص تفرّد الاسم
        for existing in self._steps:
            if existing.name == step.name:
                raise ValueError(
                    f"اسم الخطوة مكرّر: '{step.name}' — "
                    f"Duplicate step name: '{step.name}'"
                )

        self._steps.append(step)
        return self

    def add_callback(self, callback: ProgressCallback) -> "ProcessingPipeline":
        """
        إضافة استدعاع راجع.
        Add a callback.

        Args:
            callback: كائن الاستدعاع الراجع

        Returns:
            self (للسلسلة — method chaining)
        """
        self._callbacks.append(callback)
        return self

    # -----------------------------------------------------------------
    # تنفيذ خط المعالجة — Pipeline Execution
    # -----------------------------------------------------------------

    def run(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        تشغيل خط المعالجة بالكامل.
        Run the complete pipeline.

        Args:
            context: سياق مشترك يُمرَّر لجميع الخطوات (اختياري).
                     يمكن للخطوات الوصول إلى نتائج الخطوات السابقة عبره.

        Returns:
            قاموس {اسم_الخطوة: نتيجة} لجميع الخطوات

        Example:
            >>> results = pipeline.run(context={"input_file": "doc.pdf"})
            >>> text = results["extract"]
            >>> ocr_text = results["ocr"]
        """
        ctx = dict(context or {})
        self._results = {}

        if not self._steps:
            logger.warning("لا توجد خطوات للتنفيذ — No steps to execute")
            return self._results

        # تحديد ترتيب التنفيذ بناءً على التبعيات
        execution_order = self._resolve_execution_order()

        # إنشاء المتتبّع
        self._tracker = ProgressTracker(
            total_steps=len(execution_order),
            description=self._description,
            callbacks=self._callbacks,
        )

        logger.info(
            "بدء خط المعالجة: '%s' — %d خطوة — "
            "Starting pipeline: '%s' — %d steps",
            self._description, len(execution_order),
            self._description, len(execution_order),
        )

        # تنفيذ الخطوات بالتتابع
        for step in execution_order:
            result = self._execute_step(step, ctx)
            self._results[step.name] = result
            ctx[step.name] = result

        return self._results

    def run_pipeline(
        self,
        steps: Optional[List[PipelineStep]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        تشغيل خط معالجة مع خطوات ممرّرة مباشرة.
        Run a pipeline with directly provided steps.

        Args:
            steps: قائمة الخطوات (إذا لم تُحدّد، تُستخدم الخطوات المضافة مسبقاً)
            context: سياق مشترك

        Returns:
            قاموس {اسم_الخطوة: نتيجة}
        """
        if steps is not None:
            # استبدال الخطوات الحالية مؤقتاً
            old_steps = self._steps
            self._steps = list(steps)
            try:
                results = self.run(context=context)
            finally:
                self._steps = old_steps
            return results
        else:
            return self.run(context=context)

    def _execute_step(
        self,
        step: PipelineStep,
        context: Dict[str, Any],
    ) -> Any:
        """
        تنفيذ خطوة واحدة مع إعادة المحاولة والمهلة.
        Execute a single step with retry and timeout support.

        Args:
            step: الخطوة المراد تنفيذها
            context: السياق المشترك

        Returns:
            نتيجة تنفيذ الخطوة
        """
        if self._tracker is None:
            raise RuntimeError("المتتبّع غير مهيأ — Tracker not initialized")

        # بدء الخطوة
        display_name = step.description or step.name
        self._tracker.start_step(display_name)

        last_error: Optional[Exception] = None
        attempts = step.retry_count + 1

        for attempt in range(attempts):
            try:
                # تنفيذ مع مهلة اختيارية
                if step.timeout is not None and step.timeout > 0:
                    result = self._run_with_timeout(step.fn, step.timeout, context)
                else:
                    result = step.fn(context)

                # نجاح — إكمال الخطوة
                self._tracker.complete_step(display_name, result=result)

                if attempt > 0:
                    logger.info(
                        "نجحت الخطوة '%s' بعد %d محاولات — "
                        "Step '%s' succeeded after %d attempts",
                        step.name, attempt + 1,
                        step.name, attempt + 1,
                    )

                return result

            except Exception as exc:
                last_error = exc

                if attempt < attempts - 1:
                    logger.warning(
                        "محاولة %d/%d فشلت للخطوة '%s': %s — "
                        "Attempt %d/%d failed for step '%s': %s",
                        attempt + 1, attempts, step.name, exc,
                        attempt + 1, attempts, step.name, exc,
                    )
                else:
                    # فشلت جميع المحاولات
                    self._tracker.fail_step(display_name, exc)
                    logger.error(
                        "فشلت الخطوة '%s' بعد %d محاولات: %s — "
                        "Step '%s' failed after %d attempts: %s",
                        step.name, attempts, exc,
                        step.name, attempts, exc,
                    )

        return None

    @staticmethod
    def _run_with_timeout(
        fn: Callable[..., Any],
        timeout: float,
        context: Dict[str, Any],
    ) -> Any:
        """
        تنفيذ دالة مع مهلة زمنية.
        Execute a function with a timeout.

        Args:
            fn: الدالة المراد تنفيذها
            timeout: المهلة بالثواني
            context: السياق المطلوب تمريره

        Returns:
            نتيجة الدالة

        Raises:
            TimeoutError: إذا تجاوز التنفيذ المهلة
        """
        result_holder: List[Any] = [None]
        error_holder: List[Optional[Exception]] = [None]
        done_event = threading.Event()

        def _target() -> None:
            try:
                result_holder[0] = fn(context)
            except Exception as exc:
                error_holder[0] = exc
            finally:
                done_event.set()

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        completed = done_event.wait(timeout=timeout)

        if not completed:
            raise TimeoutError(
                f"تجاوز التنفيذ المهلة ({timeout} ث) — "
                f"Execution timed out ({timeout}s)"
            )

        if error_holder[0] is not None:
            raise error_holder[0]

        return result_holder[0]

    # -----------------------------------------------------------------
    # تحليل التبعيات — Dependency Resolution
    # -----------------------------------------------------------------

    def _resolve_execution_order(self) -> List[PipelineStep]:
        """
        تحليل ترتيب تنفيذ الخطوات بناءً على التبعيات.
        Resolve the execution order based on dependencies.

        Uses topological sort to determine a valid execution order.
        Steps with no dependencies can potentially be parallelized
        (currently executed sequentially in resolved order).

        Returns:
            قائمة الخطوات مرتبة حسب التبعيات

        Raises:
            ValueError: إذا وُجدت تبعية دورية
        """
        # بناء رسم بياني للتبعيات
        step_map: Dict[str, PipelineStep] = {s.name: s for s in self._steps}
        in_degree: Dict[str, int] = {s.name: 0 for s in self._steps}
        dependents: Dict[str, List[str]] = {s.name: [] for s in self._steps}

        for step in self._steps:
            for dep in step.depends_on:
                if dep not in step_map:
                    raise ValueError(
                        f"تبعية غير موجودة: '{dep}' في الخطوة '{step.name}' — "
                        f"Dependency not found: '{dep}' in step '{step.name}'"
                    )
                in_degree[step.name] += 1
                dependents[dep].append(step.name)

        # الفرز الطوبولوجي — Topological sort (Kahn's algorithm)
        queue: List[str] = [
            name for name, degree in in_degree.items() if degree == 0
        ]
        order: List[str] = []

        while queue:
            # ترتيب أبجدي لضمان تناسق النتائج
            queue.sort()
            name = queue.pop(0)
            order.append(name)

            for dependent in dependents[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._steps):
            raise ValueError(
                "تبعية دورية مكتشفة في خط المعالجة — "
                "Circular dependency detected in pipeline"
            )

        return [step_map[name] for name in order]

    # -----------------------------------------------------------------
    # تمثيل نصي — String Representation
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        """تمثيل نصي لخط المعالجة."""
        step_names = ", ".join(s.name for s in self._steps)
        return (
            f"ProcessingPipeline("
            f"description='{self._description}', "
            f"steps=[{step_names}])"
        )


# =====================================================================
# دوال مساعدة للتكامل — Integration Helper Functions
# =====================================================================

def create_progress_callback(
    description: str = "",
    on_step_start_fn: Optional[CallbackFn] = None,
    on_step_complete_fn: Optional[CallbackFn] = None,
    on_progress_fn: Optional[CallbackFn] = None,
    on_error_fn: Optional[CallbackFn] = None,
    on_complete_fn: Optional[CallbackFn] = None,
) -> "_ProgressCallbackAdapter":
    """
    مصنع لإنشاء استدعاع راجع مخصّص.
    Factory for creating custom progress callbacks.

    يتيح إنشاء استدعاع راجع من دوال منفصلة دون الحاجة
    لتعريف فئة كاملة تطبّق البروتوكول.

    Args:
        description: وصف الاستدعاع الراجع
        on_step_start_fn: دالة (step_name, step_index, total_steps) -> None
        on_step_complete_fn: دالة (step_name, duration, result) -> None
        on_progress_fn: دالة (current, total, message, percentage) -> None
        on_error_fn: دالة (step_name, error) -> None
        on_complete_fn: دالة (total_duration, results_summary) -> None

    Returns:
        كائن يطبّق ProgressCallback

    Example:
        >>> def my_progress(current, total, message, percentage):
        ...     print(f"Progress: {percentage:.0f}% - {message}")
        >>>
        >>> callback = create_progress_callback(
        ...     description="My custom callback",
        ...     on_progress_fn=my_progress,
        ... )
        >>> tracker.add_callback(callback)
    """
    return _ProgressCallbackAdapter(
        description=description,
        on_step_start_fn=on_step_start_fn,
        on_step_complete_fn=on_step_complete_fn,
        on_progress_fn=on_progress_fn,
        on_error_fn=on_error_fn,
        on_complete_fn=on_complete_fn,
    )


class _ProgressCallbackAdapter:
    """
    محوّل يحوّل دوال منفصلة إلى كائن ProgressCallback.
    Adapter that converts standalone functions into a ProgressCallback object.

    تُستخدم داخلياً بواسطة create_progress_callback().
    """

    def __init__(
        self,
        description: str = "",
        on_step_start_fn: Optional[CallbackFn] = None,
        on_step_complete_fn: Optional[CallbackFn] = None,
        on_progress_fn: Optional[CallbackFn] = None,
        on_error_fn: Optional[CallbackFn] = None,
        on_complete_fn: Optional[CallbackFn] = None,
    ) -> None:
        self._description = description
        self._on_step_start = on_step_start_fn
        self._on_step_complete = on_step_complete_fn
        self._on_progress = on_progress_fn
        self._on_error = on_error_fn
        self._on_complete = on_complete_fn

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """تسليم الحدث للدالة المخصّصة إن وُجدت."""
        if self._on_step_start is not None:
            self._on_step_start(step_name, step_index, total_steps)

    def on_step_complete(
        self,
        step_name: str,
        duration: float,
        result: Any = None,
    ) -> None:
        """تسليم الحدث للدالة المخصّصة إن وُجدت."""
        if self._on_step_complete is not None:
            self._on_step_complete(step_name, duration, result)

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """تسليم الحدث للدالة المخصّصة إن وُجدت."""
        if self._on_progress is not None:
            self._on_progress(current, total, message, percentage)

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """تسليم الحدث للدالة المخصّصة إن وُجدت."""
        if self._on_error is not None:
            self._on_error(step_name, error)

    def on_complete(
        self,
        total_duration: float,
        results_summary: Dict[str, Any],
    ) -> None:
        """تسليم الحدث للدالة المخصّصة إن وُجدت."""
        if self._on_complete is not None:
            self._on_complete(total_duration, results_summary)

    def __repr__(self) -> str:
        return f"_ProgressCallbackAdapter(description='{self._description}')"


def progress_to_logger(
    logger_obj: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    progress_level: int = logging.DEBUG,
) -> "_LoggerCallbackAdapter":
    """
    إنشاء استدعاع راجع يوجّه أحداث التقدّم إلى المسجّل (logger).
    Create a callback that directs progress events to a Python logger.

    مفيد للتكامل مع أنظمة التسجيل الحالية.

    Args:
        logger_obj: كائن المسجّل (الافتراضي: logger الوحدة)
        level: مستوى السجل للأحداث المهمة (البدء، الاكتمال، الخطأ)
        progress_level: مستوى السجل لتحديثات التقدّم المتكررة
                       (الافتراضي: DEBUG لتجنّب الإفراط في السجل)

    Returns:
        كائن ProgressCallback يوجّه إلى المسجّل

    Example:
        >>> import logging
        >>> my_logger = logging.getLogger("my_app")
        >>> callback = progress_to_logger(my_logger, level=logging.INFO)
        >>> tracker.add_callback(callback)
    """
    return _LoggerCallbackAdapter(
        logger_obj=logger_obj or logger,
        level=level,
        progress_level=progress_level,
    )


class _LoggerCallbackAdapter:
    """
    محوّل يوجّه أحداث التقدّم إلى المسجّل.
    Adapter that directs progress events to a logger.

    تُستخدم داخلياً بواسطة progress_to_logger().
    """

    def __init__(
        self,
        logger_obj: logging.Logger,
        level: int = logging.INFO,
        progress_level: int = logging.DEBUG,
    ) -> None:
        self._logger = logger_obj
        self._level = level
        self._progress_level = progress_level

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """تسجيل بدء الخطوة."""
        self._logger.log(
            self._level,
            "[خطوة %d/%d] بدء: '%s' — [Step %d/%d] Start: '%s'",
            step_index + 1, total_steps, step_name,
            step_index + 1, total_steps, step_name,
        )

    def on_step_complete(
        self,
        step_name: str,
        duration: float,
        result: Any = None,
    ) -> None:
        """تسجيل اكتمال الخطوة."""
        self._logger.log(
            self._level,
            "اكتملت: '%s' (%.2f ث) — Completed: '%s' (%.2fs)",
            step_name, duration,
            step_name, duration,
        )

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """تسجيل تحديث التقدّم."""
        self._logger.log(
            self._progress_level,
            "التقدّم: %d/%d (%.1f%%) %s — Progress: %d/%d (%.1f%%) %s",
            current, total, percentage, message,
            current, total, percentage, message,
        )

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """تسجيل الخطأ."""
        self._logger.log(
            self._level,
            "خطأ في '%s': %s — Error in '%s': %s",
            step_name, error,
            step_name, error,
        )

    def on_complete(
        self,
        total_duration: float,
        results_summary: Dict[str, Any],
    ) -> None:
        """تسجيل اكتمال الكل."""
        has_error = results_summary.get("has_error", False)
        completed = results_summary.get("completed_steps", 0)
        total = results_summary.get("total_steps", 0)

        status_msg = "بأخطاء — with errors" if has_error else "بنجاح — successfully"
        self._logger.log(
            self._level,
            "اكتمل خط المعالجة %s — %d/%d خطوة — %.2f ث — "
            "Pipeline completed %s — %d/%d steps — %.2fs",
            status_msg, completed, total, total_duration,
            status_msg, completed, total, total_duration,
        )

    def __repr__(self) -> str:
        return f"_LoggerCallbackAdapter(logger='{self._logger.name}')"


# =====================================================================
# محوّلات لبيئات واجهة المستخدم — UI Framework Adapters
# =====================================================================

class GradioProgressAdapter:
    """
    محوّل لربط تتبّع التقدّم مع gradio.Progress.
    Adapter for connecting progress tracking with gradio.Progress.

    مفيد عند استخدام OmniFile داخل تطبيق Gradio.

    Example:
        >>> import gradio as gr
        >>> tracker = ProgressTracker(total_steps=3)
        >>> # داخل دالة Gradio:
        >>> def process(gr_progress=gr.Progress()):
        ...     adapter = GradioProgressAdapter(gr_progress)
        ...     tracker.add_callback(adapter)
        ...     # ... تنفيذ الخطوات ...
    """

    def __init__(self, gradio_progress: Any) -> None:
        """
        Args:
            gradio_progress: كائن gradio.Progress
        """
        self._progress = gradio_progress

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """تحديث وصف Gradio عند بدء خطوة."""
        try:
            if hasattr(self._progress, "desc"):
                self._progress.desc = step_name
        except Exception:
            pass

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """تحديث شريط Gradio."""
        try:
            self._progress(percentage / 100.0, desc=message or "")
        except Exception:
            pass

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """تسجيل الخطأ في Gradio."""
        try:
            if hasattr(self._progress, "desc"):
                self._progress.desc = f"Error: {step_name}"
        except Exception:
            pass


class StreamlitProgressAdapter:
    """
    محوّل لربط تتبّع التقدّم مع Streamlit st.progress.
    Adapter for connecting progress tracking with Streamlit st.progress.

    Example:
        >>> import streamlit as st
        >>> tracker = ProgressTracker(total_steps=3)
        >>> adapter = StreamlitProgressAdapter(st)
        >>> tracker.add_callback(adapter)
    """

    def __init__(self, st_module: Any) -> None:
        """
        Args:
            st_module: وحدة streamlit (st)
        """
        self._st = st_module
        self._progress_bar: Any = None
        self._status_text: Any = None

    def on_step_start(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
    ) -> None:
        """إنشاء أو تحديث شريط التقدّم في Streamlit."""
        try:
            if self._progress_bar is None:
                self._progress_bar = self._st.progress(0.0)
                self._status_text = self._st.empty()
            self._status_text.text(step_name)
        except Exception:
            pass

    def on_progress(
        self,
        current: int,
        total: int,
        message: str,
        percentage: float,
    ) -> None:
        """تحديث شريط التقدّم في Streamlit."""
        try:
            if self._progress_bar is not None:
                self._progress_bar.progress(percentage / 100.0)
            if self._status_text is not None and message:
                self._status_text.text(message)
        except Exception:
            pass

    def on_complete(
        self,
        total_duration: float,
        results_summary: Dict[str, Any],
    ) -> None:
        """إكمال شريط التقدّم في Streamlit."""
        try:
            if self._progress_bar is not None:
                self._progress_bar.progress(1.0)
            if self._status_text is not None:
                self._status_text.text(
                    f"✓ Completed in {total_duration:.1f}s"
                )
        except Exception:
            pass

    def on_error(
        self,
        step_name: str,
        error: Exception,
    ) -> None:
        """عرض الخطأ في Streamlit."""
        try:
            if self._status_text is not None:
                self._status_text.error(f"Error in {step_name}: {error}")
        except Exception:
            pass
