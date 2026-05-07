# format_parser.py - Format parser module (updated)
import re
from typing import List, Dict, Tuple

class FormatParser:
    """محلل للتنسيق في النصوص."""

    @staticmethod
    def parse_tables(text: str) -> List[List[List[str]]]:
        """
        تحليل الجداول من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[List[List[str]]]: قائمة الجداول (كل جدول هو قائمة صفوف، كل صف هو قائمة خلايا).
        """
        tables = []
        lines = text.split('\n')
        current_table = []
        in_table = False

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('|') and stripped_line.endswith('|'):
                if not in_table:
                    current_table = []
                    in_table = True

                # تحليل السطر
                cells = [cell.strip() for cell in stripped_line.split('|') if cell.strip()]
                current_table.append(cells)
            else:
                if in_table and current_table:
                    # تأكد من أن الجدول يحتوي على أكثر من سطر (رأس + بيانات)
                    if len(current_table) > 1:
                        tables.append(current_table)
                    current_table = []
                    in_table = False

        # إضافة الجدول الأخير إذا كان هناك جدول غير مكتمل
        if in_table and current_table and len(current_table) > 1:
            tables.append(current_table)

        return tables

    @staticmethod
    def parse_images(text: str) -> List[Dict[str, str]]:
        """
        تحليل الصور من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Dict[str, str]]: قائمة الصور (كل صورة تحتوي على alt و url).
        """
        images = []
        # نمط الصورة: ![alt](url)
        image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

        for match in image_pattern.finditer(text):
            images.append({
                'alt': match.group(1),
                'url': match.group(2)
            })

        return images

    @staticmethod
    def parse_code_blocks(text: str) -> List[Dict[str, str]]:
        """
        تحليل كتل الكود من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Dict[str, str]]: قائمة كتل الكود (كل كتلة تحتوي على language و code).
        """
        code_blocks = []
        # نمط كتل الكود: ```language\ncode\n```
        code_pattern = re.compile(r'```(\w*)\n([\s\S+?])```')

        for match in code_pattern.finditer(text):
            code_blocks.append({
                'language': match.group(1),
                'code': match.group(2).strip()
            })

        return code_blocks

    @staticmethod
    def parse_headings(text: str) -> List[Tuple[str, str]]:
        """
        تحليل العناوين من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str]]: قائمة العناوين (كل عنوان هو (tag, text)).
        """
        headings = []
        for i in range(1, 7):
            pattern = re.compile(rf'^{"#" * i}\s+(.*?)$', re.MULTILINE)
            for match in pattern.finditer(text):
                headings.append((f'h{i}', match.group(1).strip()))

        return headings

    @staticmethod
    def parse_emphasis(text: str) -> List[Tuple[str, str, str]]:
        """
        تحليل الخط المائل والغليظ من النص.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str, str]]: قائمة التنسيقات (type, start, end).
        """
        emphasis = []

        # غليظ: **text**
        for match in re.finditer(r'\*\*(.*?)\*\*', text):
            emphasis.append(('strong', match.start(), match.end()))

        # مائل: *text*
        for match in re.finditer(r'\*(.*?)\*', text):
            emphasis.append(('em', match.start(), match.end()))

        # مسطّر: ~~text~~
        for match in re.finditer(r'~~(.*?)~~', text):
            emphasis.append(('s', match.start(), match.end()))

        return emphasis

    @staticmethod
    def parse_links(text: str) -> List[Tuple[str, str, str]]:
        """
        تحليل الروابط من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str, str]]: قائمة الروابط (text, url, placeholder).
        """
        links = []
        # نمط الروابط: [text](url)
        link_pattern = re.compile(r'\[(.*?)\]\((.*?)\)')

        # استبدال الروابط بمؤقتات
        temp_text = text
        for match in link_pattern.finditer(text):
            placeholder = f'<!-- LINK:{len(links)} -->'
            temp_text = temp_text.replace(match.group(0), placeholder, 1)
            links.append((match.group(1), match.group(2), placeholder))

        return links

    @staticmethod
    def parse_blockquotes(text: str) -> List[Tuple[str, str]]:
        """
        تحليل الاقتباسات من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str]]: قائمة الاقتباسات (text, placeholder).
        """
        blockquotes = []
        # نمط الاقتباسات: > text
        blockquote_pattern = re.compile(r'^>\s*(.*?)$', re.MULTILINE)

        # استبدال الاقتباسات بمؤقتات
        temp_text = text
        for match in blockquote_pattern.finditer(text):
            placeholder = f'<!-- BLOCKQUOTE:{len(blockquotes)} -->'
            temp_text = temp_text.replace(match.group(0), placeholder, 1)
            blockquotes.append((match.group(1).strip(), placeholder))

        return blockquotes
