"""
اختبارات فاحص البيانات الحساسة
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestSensitiveDataScanner:
    """اختبارات فاحص البيانات الحساسة."""

    def test_import(self):
        """اختبار استيراد الفاحص."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        assert SensitiveDataScanner is not None

    def test_initialization(self):
        """اختبار التهيئة."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner()
        assert scanner is not None

    def test_scan_clean_text(self):
        """اختبار فحص نص نظيف."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("Hello World, this is a clean text.")
        assert result["sensitive_data_found"] is False
        assert result["total_entities"] == 0
        assert result["risk_level"] == "none"

    def test_scan_email(self):
        """اختبار كشف البريد الإلكتروني."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("Contact me at test@example.com please.")
        assert result["sensitive_data_found"] is True
        assert result["total_entities"] >= 1

        entity_types = [e["type"] for e in result["entities"]]
        assert "EMAIL_ADDRESS" in entity_types

    def test_scan_credit_card(self):
        """اختبار كشف بطاقة الائتمانية."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("Card: 4111-1111-1111-1111")
        assert result["sensitive_data_found"] is True

    def test_scan_phone(self):
        """اختبار كشف رقم الهاتف."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("Call me at +1-234-567-8900")
        assert result["sensitive_data_found"] is True

    def test_scan_ip_address(self):
        """اختبار كشف عنوان IP."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("Server at 192.168.1.1")
        assert result["sensitive_data_found"] is True

    def test_scan_api_key(self):
        """اختبار كشف مفتاح API."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text('api_key = "sk-1234567890abcdefghij"')
        assert result["sensitive_data_found"] is True

    def test_scan_multiple_entities(self, sensitive_text):
        """اختبار كشف كيانات متعددة."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text(sensitive_text)
        assert result["sensitive_data_found"] is True
        assert result["total_entities"] >= 3

    def test_risk_level_critical(self):
        """اختبار مستوى خطورة حرج."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("-----BEGIN RSA PRIVATE KEY-----")
        assert result["risk_level"] in ("critical", "high")

    def test_anonymize_text(self):
        """اختبار إخفاء البيانات الحساسة."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        text = "Email: test@example.com"
        anonymized = scanner.anonymize_text(text, mask_char="[HIDDEN]")
        assert "test@example.com" not in anonymized
        assert "[HIDDEN]" in anonymized

    def test_anonymize_empty(self):
        """اختبار إخفاء نص فارغ."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        assert scanner.anonymize_text("") == ""

    def test_add_custom_pattern(self):
        """اختبار إضافة نمط مخصص."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        scanner.add_custom_pattern(
            name="SYRIAN_PHONE",
            label="هاتف سوري",
            regex=r"09\d{8}",
            risk="medium",
        )

        result = scanner.scan_text("Call 0912345678")
        assert result["sensitive_data_found"] is True

    def test_is_available(self):
        """اختبار فحص التوفر."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner()

        available = scanner.is_available()
        assert isinstance(available, dict)
        assert "presidio" in available
        assert "regex" in available

    def test_scan_empty_text(self):
        """اختبار فحص نص فارغ."""
        from modules.security.sensitive_data_scanner import SensitiveDataScanner
        scanner = SensitiveDataScanner(use_presidio=False)

        result = scanner.scan_text("")
        assert result["sensitive_data_found"] is False
