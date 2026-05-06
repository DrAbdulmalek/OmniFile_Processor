# exporter.py - Updated export module

from pathlib import Path
from typing import Optional, Dict, Union, List
from .html_exporter import HTMLExporter
from .pdf_exporter import PDFExporter
from .docx_exporter import DOCXExporter
from .excel_exporter import ExcelExporter
import logging
import os

logger = logging.getLogger(__name__)

class TextExporter:
    """مصدّر للنصوص إلى صيغ مختلفة مع حفظ التنسيق."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.html_exporter = HTMLExporter(language)
        self.pdf_exporter = PDFExporter()
        self.docx_exporter = DOCXExporter(language)
        self.excel_exporter = ExcelExporter(language)

    def export(
        self,
        text: str,
        output_path: Union[str, Path],
        format: str = "html",
        title: str = "OmniFile Export",
        metadata: Optional[Dict] = None,
        **options
    ) -> Path:
        """
        تصدير النص إلى الصيغة المحددة.

        Args:
            text: النص المراد تصديره.
            output_path: مسار الملف المخرج.
            format: الصيغة (html, pdf, docx, excel).
            title: عنوان الصفحة (لHTML/PDF).
            metadata: بيانات وصفية (اختياري).
            options: خيارات إضافية.

        Returns:
            Path: مسار الملف المصدّر.
        """
        output_path = Path(output_path)

        if format == "html":
            return self.html_exporter.export(
                text=text,
                output_path=output_path,
                title=title,
                metadata=metadata
            )
        elif format == "pdf":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.pdf_exporter.export(
                html_path=html_path,
                output_path=output_path,
                **options
            )
        elif format == "docx":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.docx_exporter.export(
                html_path=html_path,
                output_path=output_path
            )
        elif format == "excel":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.excel_exporter.export(
                html_path=html_path,
                output_path=output_path
            )
        else:
            raise ValueError(f"الصيغة {format} غير مدعومة. الصيغ المدعومة: html, pdf, docx, excel")

    def export_to_all_formats(
        self,
        text: str,
        output_dir: Union[str, Path],
        base_name: str,
        title: str = "OmniFile Export",
        metadata: Optional[Dict] = None,
        **options
    ) -> Dict[str, Path]:
        """
        تصدير النص إلى جميع الصيغ المدعومة.

        Args:
            text: النص المراد تصديره.
            output_dir: مجلد المخرجات.
            base_name: اسم الملف الأساسي (بدون امتداد).
            title: عنوان الصفحة.
            metadata: بيانات وصفية (اختياري).
            options: خيارات إضافية.

        Returns:
            Dict[str, Path]: قاموس بالصيغ ومسارات الملفات.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        for format in ["html", "pdf", "docx", "excel"]:
            output_path = output_dir / f"{base_name}.{format}"
            try:
                results[format] = self.export(
                    text=text,
                    output_path=output_path,
                    format=format,
                    title=title,
                    metadata=metadata,
                    **options
                )
                logger.info(f"تم تصدير الملف إلى {format}: {output_path}")
            except Exception as e:
                logger.error(f"فشل تصدير الملف إلى {format}: {e}")
                results[format] = None

        return results
