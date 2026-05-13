"""
وحدة إدارة النماذج والذاكرة — Model Memory Manager
===================================================

وحدة لإدارة ذاكرة نماذج الذكاء الاصطناعي عبر التخزين المؤقت
والإزاحة إلى المعالج (CPU) لتحرير ذاكرة كرت الشاشة (GPU).

تُعالج هذه الوحدة التوصية التالية من مراجعة المشروع:
"مع وجود العديد من نماذج الذكاء الاصطناعي المتكاملة، يمكن أن يصبح
استهلاك الذاكرة مشكلة. راجع استخدام الذاكرة وطبّق تقنيات مثل إزاحة
النماذج إلى المعالج عند عدم استخدامها النشط."

This module provides a singleton model cache with LRU eviction,
memory tracking, and GPU/CPU offloading capabilities.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Tuple

# --- إعداد المسجل — Logger Setup ---
logger = logging.getLogger(__name__)


# =====================================================================
# ثوابت — Constants
# =====================================================================

DEFAULT_MAX_MEMORY_GB: float = 8.0
"""الحد الأقصى الافتراضي للذاكرة بالجيجابايت — Default max memory in GB"""

# =====================================================================
# هيكل بيانات النموذج المخزّن — Cached Model Entry
# =====================================================================

class _ModelEntry:
    """
    سجل نموذج مُخزّن في الذاكرة المؤقتة.
    Internal entry representing a cached model.

    يحتفظ هذا الكائن بمعلومات النموذج بما في ذلك
    مرجع النموذج، ووقت التحميل، وحجم الذاكرة، وحالة التحميل.

    Attributes:
        model: المرجع الفعلي للنموذج
        device: الجهاز الحالي ('cuda', 'cpu', أو 'auto')
        memory_mb: حجم الذاكرة المقدّر بالميجابايت
        loaded_at: وقت تحميل النموذج (timestamp)
        last_accessed: وقت آخر وصول للنموذج
        load_time_ms: وقت تحميل النموذج بالميلي ثانية
        is_on_gpu: هل النموذج حاليًا على كرت الشاشة
    """

    __slots__ = (
        "model",
        "device",
        "memory_mb",
        "loaded_at",
        "last_accessed",
        "load_time_ms",
        "is_on_gpu",
    )

    def __init__(
        self,
        model: Any,
        device: str = "cpu",
        memory_mb: float = 0.0,
        load_time_ms: float = 0.0,
    ) -> None:
        self.model: Any = model
        self.device: str = device
        self.memory_mb: float = memory_mb
        self.loaded_at: float = time.time()
        self.last_accessed: float = time.time()
        self.load_time_ms: float = load_time_ms
        self.is_on_gpu: bool = (device == "cuda")

    def touch(self) -> None:
        """تحديث وقت آخر وصول (لخوارزمية LRU)."""
        self.last_accessed = time.time()

    def __repr__(self) -> str:
        return (
            f"_ModelEntry(device='{self.device}', "
            f"memory_mb={self.memory_mb:.1f}, "
            f"is_on_gpu={self.is_on_gpu})"
        )


# =====================================================================
# فئة إدارة النماذج — ModelCache Singleton
# =====================================================================

class ModelCache:
    """
    مخزن مؤقت أحادي (Singleton) لإدارة نماذج الذكاء الاصطناعي.
    Singleton model cache for managing AI models.

    يوفر هذا المخزن المؤقت:
    - تخزين مؤقت للنماذج لتفادي إعادة التحميل
    - تتبع استخدام الذاكرة لكل نموذج
    - إزاحة النماذج إلى المعالج لتحرير ذاكرة كرت الشاشة
    - إعادة تحميل النماذج إلى كرت الشاشة عند الحاجة
    - إخلاء LRU عند تجاوز حد الذاكرة
    - تتبع أوقات التحميل ومعدل الإصابة في المخزن المؤقت

    Example:
        >>> cache = ModelCache.instance()
        >>>
        >>> # تحميل نموذج
        >>> model = cache.load_model(
        ...     model_key="ocr_model",
        ...     load_fn=lambda: load_ocr_model(),
        ...     device="auto",
        ... )
        >>>
        >>> # الإبلاغ عن الذاكرة
        >>> report = cache.get_memory_report()
        >>>
        >>> # إزاحة إلى المعالج لتحرير ذاكرة كرت الشاشة
        >>> cache.offload_to_cpu("ocr_model")
        >>>
        >>> # إعادة تحميل إلى كرت الشاشة
        >>> cache.reload_to_gpu("ocr_model")
        >>>
        >>> # تفريغ نموذج
        >>> cache.unload_model("ocr_model")
    """

    _instance: Optional["ModelCache"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "ModelCache":
        """
        تطبيق نمط Singleton — ضمان وجود نسخة واحدة فقط.
        Ensure only one instance exists (Singleton pattern).
        """
        if cls._instance is None:
            with cls._lock:
                # التحقق المزدوج لمنع حالات السباق
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        max_memory_gb: float = DEFAULT_MAX_MEMORY_GB,
    ) -> None:
        """
        تهيئة مخزن النماذج المؤقت.
        Initialize the model cache.

        Args:
            max_memory_gb: الحد الأقصى للذاكرة بالجيجابايت
        """
        # تجنب إعادة التهيئة عند استدعاء __init__ مرة أخرى
        if getattr(self, "_initialized", False):
            return

        self._max_memory_bytes: int = int(max_memory_gb * 1024**3)
        self._max_memory_gb: float = max_memory_gb

        # مخزن مؤقت مرتّب للحفاظ على ترتيب الوصول (LRU)
        self._cache: OrderedDict[str, _ModelEntry] = OrderedDict()

        # قفل لضمان سلامة الخيوط
        self._cache_lock: threading.Lock = threading.Lock()

        # إحصائيات الأداء
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._total_memory_used_mb: float = 0.0

        # دالة إعادة التحميل لكل نموذج (لإعادة التحميل من المعالج إلى كرت الشاشة)
        self._reload_fns: Dict[str, Callable[..., Any]] = {}

        # التحقق من توفر torch
        self._torch_available: bool = self._check_torch()

        logger.info(
            "تم تهيئة مخزن النماذج — ذاكرة قصوى: %.1f جيجابايت, "
            "torch: %s",
            self._max_memory_gb,
            "متاح" if self._torch_available else "غير متاح",
        )
        self._initialized = True

    # -----------------------------------------------------------------
    # خصائص — Properties
    # -----------------------------------------------------------------

    @property
    def max_memory_gb(self) -> float:
        """الحد الأقصى للذاكرة بالجيجابايت."""
        return self._max_memory_gb

    @max_memory_gb.setter
    def max_memory_gb(self, value: float) -> None:
        """
        تعيين الحد الأقصى للذاكرة مع إخلاء تلقائي إذا لزم الأمر.
        Set the max memory limit and evict if necessary.
        """
        if value <= 0:
            raise ValueError(
                f"الحد الأقصى للذاكرة يجب أن يكون أكبر من 0 — "
                f"Max memory must be > 0, got {value}"
            )
        self._max_memory_gb = value
        self._max_memory_bytes = int(value * 1024**3)
        logger.info(
            "تم تحديث الحد الأقصى للذاكرة إلى: %.1f جيجابايت",
            value,
        )
        # إخلاء النماذج الزائدة
        self._evict_if_needed()

    @property
    def cache_hit_rate(self) -> float:
        """
        معدل الإصابة في المخزن المؤقت (0.0 - 1.0).
        Cache hit rate (0.0 - 1.0).
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total

    @property
    def model_count(self) -> int:
        """عدد النماذج المخزنة حاليًا."""
        return len(self._cache)

    @property
    def total_memory_used_mb(self) -> float:
        """إجمالي الذاكرة المستخدمة بالميجابايت."""
        return self._total_memory_used_mb

    # -----------------------------------------------------------------
    # التحقق من torch — Torch Availability
    # -----------------------------------------------------------------

    @staticmethod
    def _check_torch() -> bool:
        """
        التحقق من توفر مكتبة torch وكرت الشاشة.
        Check if torch is available with CUDA support.
        """
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _get_cuda_memory_allocated_mb(self) -> float:
        """
        الحصول على ذاكرة كرت الشاشة المستخدمة عبر torch.
        Get GPU memory allocated via torch.

        Returns:
            الذاكرة المستخدمة بالميجابايت (0.0 إذا لم يتوفر torch)
        """
        if not self._torch_available:
            return 0.0
        try:
            import torch

            return torch.cuda.memory_allocated() / (1024**2)
        except Exception:
            return 0.0

    def _get_cuda_memory_reserved_mb(self) -> float:
        """
        الحصول على ذاكرة كرت الشاشة المحجوزة عبر torch.
        Get GPU memory reserved via torch.

        Returns:
            الذاكرة المحجوزة بالميجابايت (0.0 إذا لم يتوفر torch)
        """
        if not self._torch_available:
            return 0.0
        try:
            import torch

            return torch.cuda.memory_reserved() / (1024**2)
        except Exception:
            return 0.0

    # -----------------------------------------------------------------
    # تحديد الجهاز — Device Detection
    # -----------------------------------------------------------------

    @staticmethod
    def _resolve_device(device: str) -> str:
        """
        تحديد الجهاز الفعلي بناءً على القيمة المطلوبة.
        Resolve the actual device based on the requested value.

        Args:
            device: الجهاز المطلوب ('auto', 'cuda', 'cpu')

        Returns:
            الجهاز الفعلي ('cuda' أو 'cpu')
        """
        device = device.lower().strip()
        if device == "auto":
            try:
                import torch

                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
            return "cpu"
        elif device == "cuda":
            try:
                import torch

                if torch.cuda.is_available():
                    return "cuda"
                logger.warning(
                    "تم طلب كرت الشاشة لكنه غير متاح، سيُستخدم المعالج — "
                    "CUDA requested but unavailable, falling back to CPU"
                )
                return "cpu"
            except ImportError:
                logger.warning(
                    "torch غير متاح، سيُستخدم المعالج — "
                    "torch not available, falling back to CPU"
                )
                return "cpu"
        return "cpu"

    # -----------------------------------------------------------------
    # تقدير حجم الذاكرة — Memory Estimation
    # -----------------------------------------------------------------

    @staticmethod
    def _estimate_model_memory_mb(model: Any) -> float:
        """
        تقدير حجم الذاكرة المستخدمة بواسطة النموذج بالميجابايت.
        Estimate the memory usage of a model in megabytes.

        Args:
            model: كائن النموذج

        Returns:
            الحجم التقديري بالميجابايت
        """
        # محاولة استخدام psutil لقياس الذاكرة
        try:
            import psutil
            import sys

            # تقدير مبني على حجم الكائن في الذاكرة
            size_bytes = sys.getsizeof(model)
            return max(1.0, size_bytes / (1024**2))
        except ImportError:
            pass

        # محاولة استخدام torch إذا كان النموذج torch.nn.Module
        try:
            import torch

            if isinstance(model, torch.nn.Module):
                param_bytes = sum(
                    p.numel() * p.element_size()
                    for p in model.parameters()
                )
                buffer_bytes = sum(
                    b.numel() * b.element_size()
                    for b in model.buffers()
                )
                total_bytes = param_bytes + buffer_bytes
                return max(1.0, total_bytes / (1024**2))
        except (ImportError, Exception):
            pass

        # تقدير افتراضي محافظ
        return 128.0  # 128 ميجابايت كافتراضي

    # -----------------------------------------------------------------
    # إخلاء LRU — LRU Eviction
    # -----------------------------------------------------------------

    def _evict_if_needed(self) -> None:
        """
        إخلاء النماذج الأقل استخدامًا عند تجاوز حد الذاكرة.
        Evict least-recently-used models when memory limit is exceeded.

        تُنفَّذ خوارزمية LRU: يُزال النموذج الذي لم يُ accessed
        لأطول فترة حتى يصبح استخدام الذاكرة ضمن الحد المسموح.
        """
        with self._cache_lock:
            # التحقق مما إذا كنا نحتاج إلى إخلاء
            while (
                self._total_memory_used_mb > self._max_memory_gb * 1024
                and self._cache
            ):
                # إزالة أقدم عنصر (أقل استخدامًا)
                oldest_key, oldest_entry = self._cache.popitem(last=False)
                self._total_memory_used_mb -= oldest_entry.memory_mb

                logger.warning(
                    "تم إخلاء النموذج '%s' بسبب تجاوز حد الذاكرة "
                    "(%.1f ميجابايت) — Evicted model '%s' (%.1f MB)",
                    oldest_key,
                    oldest_entry.memory_mb,
                    oldest_key,
                    oldest_entry.memory_mb,
                )

                # تنظيف ذاكرة كرت الشاشة إذا لزم الأمر
                if self._torch_available:
                    try:
                        import torch

                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass

    # -----------------------------------------------------------------
    # تحميل نموذج — Load Model
    # -----------------------------------------------------------------

    def load_model(
        self,
        model_key: str,
        load_fn: Callable[..., Any],
        device: str = "auto",
        memory_mb: Optional[float] = None,
    ) -> Any:
        """
        تحميل نموذج أو إرجاع النسخة المخزنة مؤقتًا.
        Load a model or return the cached version.

        إذا كان النموذج موجودًا بالفعل في المخزن المؤقت، يُعاد
        فورًا مع تحديث وقت الوصول. وإلّا يُحمّل عبر load_fn.

        Args:
            model_key: مفتاح فريد للنموذج
            load_fn: دالة التحميل التي تُرجع كائن النموذج
            device: الجهاز المستهدف ('auto', 'cuda', 'cpu')
            memory_mb: حجم الذاكرة المقدّر (الافتراضي: تقدير تلقائي)

        Returns:
            كائن النموذج المُحمّل

        Example:
            >>> cache = ModelCache.instance()
            >>> model = cache.load_model(
            ...     model_key="whisper_base",
            ...     load_fn=lambda: whisper.load_model("base"),
            ...     device="auto",
            ... )
        """
        resolved_device = self._resolve_device(device)

        with self._cache_lock:
            # التحقق من وجود النموذج في المخزن المؤقت
            if model_key in self._cache:
                entry = self._cache[model_key]
                entry.touch()
                self._cache.move_to_end(model_key)  # تحديث ترتيب LRU
                self._cache_hits += 1

                logger.info(
                    "إصابة في المخزن المؤقت — النموذج '%s' موجود (%.1f ميجابايت) — "
                    "Cache hit for model '%s' (%.1f MB)",
                    model_key,
                    entry.memory_mb,
                    model_key,
                    entry.memory_mb,
                )

                # إذا كان الجهاز المطلوب مختلفًا، ننقل النموذج
                if resolved_device == "cuda" and not entry.is_on_gpu:
                    self._move_entry_to_gpu(model_key, entry)
                elif resolved_device == "cpu" and entry.is_on_gpu:
                    self._move_entry_to_cpu(model_key, entry)

                return entry.model

            # إصابة فائتة — تحميل جديد
            self._cache_misses += 1

        # التحميل يتم خارج القفل لتجنب حظره أثناء التحميل
        logger.info(
            "إصابة فائتة — تحميل النموذج '%s' على '%s' — "
            "Cache miss — loading model '%s' on '%s'",
            model_key,
            resolved_device,
            model_key,
            resolved_device,
        )

        start_time = time.time()
        try:
            model = load_fn()
        except Exception as exc:
            logger.error(
                "فشل تحميل النموذج '%s': %s — Failed to load model '%s': %s",
                model_key,
                exc,
                model_key,
                exc,
            )
            raise

        load_time_ms = (time.time() - start_time) * 1000

        # تقدير حجم الذاكرة
        estimated_mb = memory_mb or self._estimate_model_memory_mb(model)

        # إنشاء سجل النموذج
        entry = _ModelEntry(
            model=model,
            device=resolved_device,
            memory_mb=estimated_mb,
            load_time_ms=load_time_ms,
        )

        # تخزين دالة إعادة التحميل
        with self._cache_lock:
            self._cache[model_key] = entry
            self._cache.move_to_end(model_key)
            self._total_memory_used_mb += estimated_mb
            self._reload_fns[model_key] = load_fn

        logger.info(
            "تم تحميل النموذج '%s' — حجم: %.1f ميجابايت, "
            "وقت: %.0f ميلي ثانية, جهاز: %s — "
            "Model '%s' loaded — size: %.1f MB, time: %.0f ms, device: %s",
            model_key,
            estimated_mb,
            load_time_ms,
            resolved_device,
            model_key,
            estimated_mb,
            load_time_ms,
            resolved_device,
        )

        # إخلاء إذا تجاوزنا الحد
        self._evict_if_needed()

        return model

    # -----------------------------------------------------------------
    # نقل بين الأجهزة — Device Transfer
    # -----------------------------------------------------------------

    def _move_entry_to_cpu(
        self,
        model_key: str,
        entry: _ModelEntry,
    ) -> None:
        """
        نقل نموذج من كرت الشاشة إلى المعالج (داخلي).
        Move a model from GPU to CPU (internal).

        Args:
            model_key: مفتاح النموذج
            entry: سجل النموذج
        """
        if not entry.is_on_gpu:
            return

        try:
            import torch

            if hasattr(entry.model, "to"):
                entry.model.to("cpu")
                entry.is_on_gpu = False
                entry.device = "cpu"
                entry.touch()
                logger.info(
                    "تم نقل النموذج '%s' إلى المعالج — "
                    "Model '%s' moved to CPU",
                    model_key,
                    model_key,
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        except ImportError:
            logger.debug("torch غير متاح، لا يمكن نقل النموذج")
        except Exception as exc:
            logger.error(
                "خطأ في نقل النموذج '%s' إلى المعالج: %s — "
                "Error moving model '%s' to CPU: %s",
                model_key,
                exc,
                model_key,
                exc,
            )

    def _move_entry_to_gpu(
        self,
        model_key: str,
        entry: _ModelEntry,
    ) -> None:
        """
        نقل نموذج من المعالج إلى كرت الشاشة (داخلي).
        Move a model from CPU to GPU (internal).

        Args:
            model_key: مفتاح النموذج
            entry: سجل النموذج
        """
        if entry.is_on_gpu or not self._torch_available:
            return

        try:
            import torch

            if hasattr(entry.model, "to"):
                entry.model.to("cuda")
                entry.is_on_gpu = True
                entry.device = "cuda"
                entry.touch()
                logger.info(
                    "تم نقل النموذج '%s' إلى كرت الشاشة — "
                    "Model '%s' moved to GPU",
                    model_key,
                    model_key,
                )
        except Exception as exc:
            logger.error(
                "خطأ في نقل النموذج '%s' إلى كرت الشاشة: %s — "
                "Error moving model '%s' to GPU: %s",
                model_key,
                exc,
                model_key,
                exc,
            )

    # -----------------------------------------------------------------
    # إزاحة إلى المعالج — Offload to CPU
    # -----------------------------------------------------------------

    def offload_to_cpu(
        self,
        model_key: Optional[str] = None,
    ) -> bool:
        """
        إزاحة نموذج (أو جميع النماذج) إلى المعالج لتحرير ذاكرة كرت الشاشة.
        Offload a model (or all models) to CPU to free GPU memory.

        Args:
            model_key: مفتاح النموذج (لا شيء = إزاحة الكل)

        Returns:
            True إذا نجحت العملية، False غير ذلك

        Example:
            >>> cache = ModelCache.instance()
            >>> cache.offload_to_cpu("large_language_model")
            >>> # أو إزالة الكل
            >>> cache.offload_to_cpu()
        """
        with self._cache_lock:
            if model_key is None:
                # إزاحة جميع النماذج إلى المعالج
                logger.info(
                    "إزاحة جميع النماذج إلى المعالج — "
                    "Offloading all models to CPU (%d models)",
                    len(self._cache),
                )
                success = True
                for key, entry in list(self._cache.items()):
                    if entry.is_on_gpu:
                        self._move_entry_to_cpu(key, entry)
                return success

            if model_key not in self._cache:
                logger.warning(
                    "النموذج '%s' غير موجود في المخزن المؤقت — "
                    "Model '%s' not found in cache",
                    model_key,
                    model_key,
                )
                return False

            entry = self._cache[model_key]
            if not entry.is_on_gpu:
                logger.info(
                    "النموذج '%s' بالفعل على المعالج — "
                    "Model '%s' is already on CPU",
                    model_key,
                    model_key,
                )
                return True

        self._move_entry_to_cpu(model_key, entry)
        return True

    # -----------------------------------------------------------------
    # إعادة تحميل إلى كرت الشاشة — Reload to GPU
    # -----------------------------------------------------------------

    def reload_to_gpu(
        self,
        model_key: Optional[str] = None,
    ) -> bool:
        """
        إعادة تحميل نموذج (أو جميع النماذج) إلى كرت الشاشة.
        Reload a model (or all models) to GPU.

        Args:
            model_key: مفتاح النموذج (لا شيء = إعادة تحميل الكل)

        Returns:
            True إذا نجحت العملية، False غير ذلك

        Example:
            >>> cache = ModelCache.instance()
            >>> cache.reload_to_gpu("ocr_model")
        """
        if not self._torch_available:
            logger.warning(
                "كرت الشاشة غير متاح، لا يمكن إعادة التحميل — "
                "CUDA not available, cannot reload to GPU"
            )
            return False

        with self._cache_lock:
            if model_key is None:
                # إعادة تحميل جميع النماذج
                logger.info(
                    "إعادة تحميل جميع النماذج إلى كرت الشاشة — "
                    "Reloading all models to GPU (%d models)",
                    len(self._cache),
                )
                success = True
                for key, entry in list(self._cache.items()):
                    if not entry.is_on_gpu:
                        self._move_entry_to_gpu(key, entry)
                return success

            if model_key not in self._cache:
                logger.warning(
                    "النموذج '%s' غير موجود — Model '%s' not found",
                    model_key,
                    model_key,
                )
                return False

            entry = self._cache[model_key]
            if entry.is_on_gpu:
                logger.info(
                    "النموذج '%s' بالفعل على كرت الشاشة — "
                    "Model '%s' is already on GPU",
                    model_key,
                    model_key,
                )
                return True

        self._move_entry_to_gpu(model_key, entry)
        return True

    # -----------------------------------------------------------------
    # تفريغ نموذج — Unload Model
    # -----------------------------------------------------------------

    def unload_model(self, model_key: str) -> bool:
        """
        تفريغ نموذج من المخزن المؤقت وتحرير الذاكرة.
        Unload a model from cache and free its memory.

        Args:
            model_key: مفتاح النموذج المراد تفريغه

        Returns:
            True إذا تم التفريغ بنجاح، False إذا لم يكن النموذج موجودًا

        Example:
            >>> cache = ModelCache.instance()
            >>> cache.unload_model("unused_model")
        """
        with self._cache_lock:
            if model_key not in self._cache:
                logger.warning(
                    "النموذج '%s' غير موجود في المخزن المؤقت — "
                    "Model '%s' not in cache",
                    model_key,
                    model_key,
                )
                return False

            entry = self._cache.pop(model_key)
            self._total_memory_used_mb -= entry.memory_mb
            self._reload_fns.pop(model_key, None)

        logger.info(
            "تم تفريغ النموذج '%s' — تم تحرير %.1f ميجابايت — "
            "Unloaded model '%s' — freed %.1f MB",
            model_key,
            entry.memory_mb,
            model_key,
            entry.memory_mb,
        )

        # تنظيف ذاكرة كرت الشاشة
        if self._torch_available:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        # حذف المرجع لتمكين جامع القمامة
        del entry

        return True

    # -----------------------------------------------------------------
    # تفريغ كامل — Clear Cache
    # -----------------------------------------------------------------

    def clear_cache(self) -> int:
        """
        تفريغ جميع النماذج من المخزن المؤقت.
        Clear all models from the cache.

        Returns:
            عدد النماذج التي تم تفريغها

        Example:
            >>> cache = ModelCache.instance()
            >>> count = cache.clear_cache()
            >>> print(f"Freed {count} models")
        """
        with self._cache_lock:
            count = len(self._cache)
            freed_mb = self._total_memory_used_mb

            # إزالة جميع النماذج على كرت الشاشة أولًا
            for key, entry in list(self._cache.items()):
                if entry.is_on_gpu:
                    self._move_entry_to_cpu(key, entry)

            self._cache.clear()
            self._reload_fns.clear()
            self._total_memory_used_mb = 0.0

        logger.info(
            "تم تفريغ %d نموذج — تم تحرير %.1f ميجابايت — "
            "Cleared %d models — freed %.1f MB",
            count,
            freed_mb,
            count,
            freed_mb,
        )

        # تنظيف ذاكرة كرت الشاشة
        if self._torch_available:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        return count

    # -----------------------------------------------------------------
    # تقرير الذاكرة — Memory Report
    # -----------------------------------------------------------------

    def get_memory_report(self) -> Dict[str, Any]:
        """
        الحصول على تقرير شامل باستخدام الذاكرة.
        Get a comprehensive memory usage report.

        Returns:
            قاموس يحتوي على تفاصيل استخدام الذاكرة

        Example:
            >>> cache = ModelCache.instance()
            >>> report = cache.get_memory_report()
            >>> print(report)
            {
                'total_models': 3,
                'total_memory_mb': 2048.5,
                'max_memory_gb': 8.0,
                'cache_hit_rate': 0.85,
                'gpu_allocated_mb': 1024.0,
                'gpu_reserved_mb': 1536.0,
                'models': [
                    {'key': 'ocr_model', 'memory_mb': 512.0, ...},
                    ...
                ]
            }
        """
        with self._cache_lock:
            models_info: List[Dict[str, Any]] = []
            for key, entry in self._cache.items():
                models_info.append({
                    "key": key,
                    "device": entry.device,
                    "is_on_gpu": entry.is_on_gpu,
                    "memory_mb": round(entry.memory_mb, 2),
                    "load_time_ms": round(entry.load_time_ms, 2),
                    "loaded_at": entry.loaded_at,
                    "last_accessed": entry.last_accessed,
                })

            report: Dict[str, Any] = {
                "total_models": len(self._cache),
                "total_memory_mb": round(self._total_memory_used_mb, 2),
                "total_memory_gb": round(self._total_memory_used_mb / 1024, 2),
                "max_memory_gb": self._max_memory_gb,
                "memory_usage_percent": round(
                    (self._total_memory_used_mb / (self._max_memory_gb * 1024)) * 100,
                    2,
                ),
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": round(self.cache_hit_rate, 4),
                "gpu_allocated_mb": round(self._get_cuda_memory_allocated_mb(), 2),
                "gpu_reserved_mb": round(self._get_cuda_memory_reserved_mb(), 2),
                "torch_available": self._torch_available,
                "models": models_info,
            }

        return report

    # -----------------------------------------------------------------
    # Singleton helper
    # -----------------------------------------------------------------

    @classmethod
    def instance(
        cls,
        max_memory_gb: float = DEFAULT_MAX_MEMORY_GB,
    ) -> "ModelCache":
        """
        الحصول على النسخة الوحيدة من مخزن النماذج.
        Get the singleton instance of the model cache.

        Args:
            max_memory_gb: الحد الأقصى للذاكرة (يُستخدم فقط عند الإنشاء الأول)

        Returns:
            النسخة الوحيدة من ModelCache
        """
        if cls._instance is None:
            cls._instance = cls(max_memory_gb=max_memory_gb)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        إعادة تعيين النسخة الوحيدة (للاختبار فقط).
        Reset the singleton instance (for testing purposes only).
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.clear_cache()
            cls._instance = None
            logger.info("تم إعادة تعيين مخزن النماذج — ModelCache reset")

    # -----------------------------------------------------------------
    # التمثيل النصي — String Representation
    # -----------------------------------------------------------------

    def __repr__(self) -> str:
        """تمثيل نصي لمخزن النماذج."""
        return (
            f"ModelCache("
            f"models={self.model_count}, "
            f"memory={self.total_memory_used_mb:.1f}MB/"
            f"{self._max_memory_gb * 1024:.0f}MB, "
            f"hit_rate={self.cache_hit_rate:.2%})"
        )

    def __len__(self) -> int:
        """عدد النماذج المخزنة."""
        return self.model_count

    def __contains__(self, model_key: str) -> bool:
        """التحقق من وجود نموذج في المخزن."""
        with self._cache_lock:
            return model_key in self._cache
