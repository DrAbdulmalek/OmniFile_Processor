"""
Fixtures مشتركة للاختبارات
"""

import os
import sys
import pytest
from pathlib import Path

# إضافة المشروع للمسار
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root():
    """مسار جذر المشروع."""
    return PROJECT_ROOT


@pytest.fixture
def sample_text_en():
    """نص إنجليزي للاختبار."""
    return """
    Machine learning is a subset of artificial intelligence that provides systems
    the ability to automatically learn and improve from experience without being
    explicitly programmed. Machine learning focuses on the development of computer
    programs that can access data and use it to learn for themselves.
    """


@pytest.fixture
def sample_text_ar():
    """نص عربي للاختبار."""
    return """
    الذكاء الاصطناعي هو فرع من علوم الحاسوب يهتم بإنشاء أنظمة ذكية
    قادرة على أداء مهام تتطلب عادةً ذكاءً بشرياً. يشمل ذلك التعلم الآلي
    ومعالجة اللغة الطبيعية والرؤية الحاسوبية.
    """


@pytest.fixture
def sample_text_de():
    """نص ألماني للاختبار."""
    return """
    Maschinelles Lernen ist ein Teilgebiet der künstlichen Intelligenz, das sich
    mit der Entwicklung von Algorithmen befasst, die aus Daten lernen können.
    """


@pytest.fixture
def sample_text_with_errors():
    """نص إنجليزي بأخطاء إملائية."""
    return "I havv a speling mistake in thiss sentnce."


@pytest.fixture
def sample_image(tmp_path):
    """صورة اختبار بسيطة."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (200, 50), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Hello World", fill="black")

        img_path = tmp_path / "test_image.png"
        img.save(str(img_path))
        return str(img_path)
    except ImportError:
        return None


@pytest.fixture
def sample_pdf(tmp_path):
    """ملف PDF اختبار فارغ."""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        pdf.cell(200, 10, text="Test PDF Content", new_x="LMARGIN", new_y="NEXT")
        pdf_path = tmp_path / "test.pdf"
        pdf.output(str(pdf_path))
        return str(pdf_path)
    except ImportError:
        return None


@pytest.fixture
def sensitive_text():
    """نص يحتوي بيانات حساسة."""
    return """
    My credit card number is 4111-1111-1111-1111.
    Contact me at test@example.com or call +1-234-567-8900.
    My SSN is 123-45-6789.
    Server IP: 192.168.1.1
    API key: sk-1234567890abcdefghij
    """
