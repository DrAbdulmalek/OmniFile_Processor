"""
OmniFile AI Processor — Export Module
=======================================
القدرات:
- تصدير إلى TXT مع دعم RTL (UTF-8 BOM)
- تصدير إلى JSON مع البيانات الهيكلية
- تصدير إلى DOCX مع دعم الفقرات RTL
- تصدير إلى HTML مع الحفاظ على التنسيق
- تصدير إلى PDF قابل للبحث (صورة + نص مخفي)
"""
from modules.export.exporter import DocumentExporter

__all__ = ["DocumentExporter"]
