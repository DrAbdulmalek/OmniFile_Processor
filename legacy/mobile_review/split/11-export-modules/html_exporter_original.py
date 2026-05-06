# modules/export/html_exporter.py
from typing import Optional, Dict, List
from pathlib import Path
from .format_parser import FormatParser
import base64

class HTMLExporter:
    """مصدّر للنصوص إلى HTML مع حفظ التنسيق."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.is_rtl = language == "ar"

    def export(
        self,
        text: str,
        output_path: Path,
        title: str = "OmniFile Export",
        metadata: Optional[Dict] = None,
        include_styles: bool = True,
        include_fonts: bool = True
    ) -> Path:
        """
        تصدير النص إلى HTML.

        Args:
            text: النص المدخل.
            output_path: مسار ملف HTML المخرج.
            title: عنوان الصفحة.
            metadata: بيانات وصفية (اختياري).
            include_styles: تضمين أنماط CSS (افتراضي: True).
            include_fonts: تضمين خطوط Google Fonts (افتراضي: True).

        Returns:
            Path: مسار ملف HTML.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # تحليل النص
        tables = FormatParser.parse_tables(text)
        images = FormatParser.parse_images(text)
        code_blocks = FormatParser.parse_code_blocks(text)
        headings = FormatParser.parse_headings(text)
        emphasis_list = FormatParser.parse_emphasis(text)

        # إنشاء HTML
        html = self._generate_html(
            text=text,
            title=title,
            tables=tables,
            images=images,
            code_blocks=code_blocks,
            headings=headings,
            emphasis_list=emphasis_list,
            metadata=metadata,
            include_styles=include_styles,
            include_fonts=include_fonts
        )

        # كتابة الملف
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _generate_html(
        self,
        text: str,
        title: str,
        tables: List[List[List[str]]],
        images: List[Dict[str, str]],
        code_blocks: List[Dict[str, str]],
        headings: List[Tuple[str, str]],
        emphasis_list: List[Tuple[str, str, str]],
        metadata: Optional[Dict],
        include_styles: bool,
        include_fonts: bool
    ) -> str:
        """توليد HTML من المكونات."""
        # بداية HTML
        html = f'<!DOCTYPE html>\n<html lang="{self.language}" dir="{self._get_dir()}">\n<head>\n'

        # العنوان
        html += f'    <meta charset="UTF-8">\n'
        html += f'    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        html += f'    <title>{title}</title>\n'

        # أنماط CSS
        if include_styles:
            html += self._generate_styles()

        # خطوط Google Fonts
        if include_fonts and self.language == "ar":
            html += '    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri&display=swap">\n'

        html += '</head>\n<body>\n'

        # العنوان الرئيسي
        html += f'    <h1>{title}</h1>\n'

        # المعالجة الفورية للنص (للتنسيقات البسيطة)
        processed_text = text

        # استبدال الجداول
        for table in tables:
            table_html = self._generate_table_html(table)
            # استبدال الجدول في النص
            table_text = self._table_to_text(table)
            processed_text = processed_text.replace(table_text, f'<!-- TABLE:{len(tables)} -->')

        # استبدال الصور
        for i, image in enumerate(images):
            image_html = self._generate_image_html(image)
            image_text = f'![{image["alt"]}]({image["url"]})'
            processed_text = processed_text.replace(image_text, f'<!-- IMAGE:{i} -->')

        # استبدال كتل الكود
        for i, code_block in enumerate(code_blocks):
            code_html = self._generate_code_html(code_block)
            code_text = f'```{code_block["language"]}\n{code_block["code"]}\n```'
            processed_text = processed_text.replace(code_text, f'<!-- CODE:{i} -->')

        # استبدال العناوين
        for tag, heading_text in headings:
            processed_text = processed_text.replace(f'#{tag[1:]} {heading_text}', f'<{tag}>{heading_text}</{tag}>')

        # استبدال التنسيقات (غليظ، مائل، مسطّر)
        # يتم معالجتها في CSS

        # إضافة المحتوى
        html += f'    <div class="content">\n{processed_text}\n    </div>\n'

        # إضافة الجداول
        for i, table in enumerate(tables):
            html += self._generate_table_html(table)

        # إضافة الصور
        for i, image in enumerate(images):
            html += self._generate_image_html(image)

        # إضافة كتل الكود
        for i, code_block in enumerate(code_blocks):
            html += self._generate_code_html(code_block)

        # إضافة البيانات الوصفية
        if metadata:
            html += self._generate_metadata_html(metadata)

        html += '</body>\n</html>'

        return html

    def _get_dir(self) -> str:
        """الحصول على اتجاه النص."""
        return 'rtl' if self.is_rtl else 'ltr'

    def _generate_styles(self) -> str:
        """توليد أنماط CSS."""
        return f'''    <style>
        body {{
            font-family: {'"Amiri", serif' if self.language == 'ar' else '"Times New Roman", serif'};
            font-size: 14pt;
            line-height: 1.6;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            color: #333;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: #1E88E5;
            margin-top: 20px;
            margin-bottom: 10px;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        .content {{
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            direction: {self._get_dir()};
        }}

        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: {self._get_dir()};
        }}

        th {{
            background-color: #f2f2f2;
        }}

        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
        }}

        .figure {{
            text-align: center;
            margin: 20px 0;
        }}

        .figure-caption {{
            font-style: italic;
            font-size: 12pt;
            margin-top: 5px;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            direction: ltr;
            text-align: left;
        }}

        code {{
            font-family: "Courier New", monospace;
        }}

        strong {{
            font-weight: bold;
        }}

        em {{
            font-style: italic;
        }}

        s {{
            text-decoration: line-through;
        }}

        hr {{
            border: 0;
            height: 1px;
            background: #ddd;
            margin: 20px 0;
        }}

        blockquote {{
            border-{self._get_dir()}: 4px solid #1E88E5;
            padding: 10px 20px;
            margin: 20px 0;
            background-color: #f9f9f9;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}
    </style>'''

    def _generate_table_html(self, table: List[List[str]]) -> str:
        """توليد HTML للجدول."""
        html = '    <table>\n'

        # رأس الجدول
        if table.isNotEmpty:
            html += '      <thead>\n        <tr>\n'
            for cell in table[0]:
                html += f'          <th>{cell}</th>\n'
            html += '        </tr>\n      </thead>\n'

        # جسم الجدول
        html += '      <tbody>\n'
        for i, row in enumerate(table):
            if i == 0:
                continue  # تجاهل رأس الجدول (تم معالجته أعلاه)
            html += '        <tr>\n'
            for cell in row:
                html += f'          <td>{cell}</td>\n'
            html += '        </tr>\n'
        html += '      </tbody>\n    </table>\n'

        return html

    def _table_to_text(self, table: List[List[str]]) -> str:
        """تحويل الجدول إلى نص للبحث عنه في النص الأصلي."""
        lines = []
        for row in table:
            lines.append('| ' + ' | '.join(row) + ' |')
        return '\n'.join(lines)

    def _generate_image_html(self, image: Dict[str, str]) -> str:
        """توليد HTML للصورة."""
        alt = image.get('alt', '')
        url = image.get('url', '')

        if url.startswith('data:image/'):
            # صورة base64
            return f'    <div class="figure">\n      <img src="{url}" alt="{alt}">\n      <div class="figure-caption">{alt}</div>\n    </div>\n'
        else:
            # صورة من URL
            return f'    <div class="figure">\n      <img src="{url}" alt="{alt}">\n      <div class="figure-caption">{alt}</div>\n    </div>\n'

    def _generate_code_html(self, code_block: Dict[str, str]) -> str:
        """توليد HTML لكتل الكود."""
        language = code_block.get('language', '')
        code = code_block.get('code', '')

        return f'    <pre><code class="language-{language}">{code}</code></pre>\n'

    def _generate_metadata_html(self, metadata: Dict) -> str:
        """توليد HTML للبيانات الوصفية."""
        html = '\n    <div class="metadata">\n'
        html += '      <h2>معلومات التصدير</h2>\n'
        html += '      <table>\n'

        for key, value in metadata.items():
            html += f'        <tr><th>{key}</th><td>{value}</td></tr>\n'

        html += '      </table>\n'
        html += '    </div>\n'

        return html
