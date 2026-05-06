# pdf_exporter.py - PDF export module (updated)
from pathlib import Path
from typing import Optional, Dict
import pdfkit
import os
import logging

logger = logging.getLogger(__name__)

class PDFExporter:
    """مصدّر للنصوص إلى PDF."""

    def __init__(self, wkhtmltopdf_path: Optional[str] = None):
        self.wkhtmltopdf_path = wkhtmltopdf_path or '/usr/bin/wkhtmltopdf'

    def export(
        self,
        html_path: Path,
        output_path: Path,
        **options
    ) -> Path:
        """
        تصدير HTML إلى PDF.

        Args:
            html_path: مسار ملف HTML.
            output_path: مسار ملف PDF المخرج.
            options: خيارات إضافية (مثل حجم الورقة).

        Returns:
            Path: مسار ملف PDF.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # إعداد خيارات pdfkit
        default_options = {
            'encoding': 'UTF-8',
            'quiet': '',
            'enable-local-file-access': None,  # السماح بالوصول إلى الملفات المحلية
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'page-size': 'A4',
        }
        options = {**default_options, **options}

        # إعداد التكوين
        config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)

        try:
            # تحويل HTML إلى PDF
            pdfkit.from_file(str(html_path), str(output_path), configuration=config, options=options)
            logger.info(f"تم تصدير الملف إلى PDF: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"فشل تصدير الملف إلى PDF: {e}")
            raise
