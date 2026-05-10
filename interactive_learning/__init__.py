"""
interactive_learning - Interactive Learning System for Arabic OCR/HTR

Provides end-to-end interactive learning capabilities:
- Smart segmentation (text lines, tables, graphics)
- Online learning from user corrections
- Layout preservation and rendering
- Quality assurance and monitoring
"""

from .core.security import SecureCorrectionStorage, AuditLogger
from .core.monitoring import (
    MetricsCollector,
    PerformanceMonitor,
    QualityAssurance,
)

__all__ = [
    "SecureCorrectionStorage",
    "AuditLogger",
    "MetricsCollector",
    "PerformanceMonitor",
    "QualityAssurance",
]

__version__ = "2.0.0"
