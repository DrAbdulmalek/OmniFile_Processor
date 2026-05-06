# modules/export/pdf_exporter.py
from pathlib import Path
from typing import Optional, Dict
import pdfkit
import os

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
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # إعداد خيارات pdfkit
        default_options = {
            'encoding': 'UTF-8',
            'quiet': '',
            'enable-local-file-access': None,  # السماح بالوصول إلى الملفات المحلية
        }
        options = {**default_options, **options}

        # إعداد التكوين
        config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)

        # تحويل HTML إلى PDF
        pdfkit.from_file(str(html_path), str(output_path), configuration=config, options=options)

        return output_path
