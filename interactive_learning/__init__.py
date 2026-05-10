"""
interactive_learning - Interactive Learning System for Arabic OCR/HTR

Provides end-to-end interactive learning capabilities:
- Smart segmentation (text lines, tables, graphics)
- Online learning from user corrections
- Layout preservation and rendering
- Quality assurance and monitoring
- Security: encrypted storage, audit logging, rate limiting
- Model management with verified registry
- Memory-efficient training with disk offloading

Uses lazy imports to avoid circular dependencies.
"""

__version__ = "3.0.0"

__all__ = [
    "InteractiveLearningSystem",
    "SecureCorrectionStorage",
    "AuditLogger",
    "RateLimiter",
    "InputSanitizer",
    "ModelManager",
    "FastSegmenter",
    "MemoryEfficientLearner",
    "MetricsCollector",
    "PerformanceMonitor",
    "QualityAssurance",
]


def __getattr__(name: str):
    """Lazy imports to avoid circular dependencies."""
    _lazy_map = {
        "InteractiveLearningSystem": "._system",
        "SecureCorrectionStorage": ".core.security",
        "AuditLogger": ".core.security",
        "RateLimiter": ".core.security",
        "InputSanitizer": ".core.security",
        "ModelManager": ".core.model_manager",
        "FastSegmenter": ".core.fast_segmenter",
        "MemoryEfficientLearner": ".learning.efficient_learner",
        "MetricsCollector": ".core.monitoring",
        "PerformanceMonitor": ".core.monitoring",
        "QualityAssurance": ".core.monitoring",
    }

    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name], __package__)
        return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
