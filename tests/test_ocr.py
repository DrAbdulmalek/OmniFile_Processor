#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_ocr.py
=================

اختبارات التعرف الضوئي على الحروف.
"""

import pytest
from fastapi import status


class TestOCREndpoint:
    """اختبارات نقطة OCR."""

    def test_ocr_without_auth(self, client):
        """التحقق من رفض الطلب بدون مصادقة."""
        response = client.post("/v2/ocr")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_ocr_without_file(self, client, auth_headers):
        """التحقق من رفض الطلب بدون ملف."""
        response = client.post(
            "/v2/ocr",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_ocr_with_invalid_format(self, client, auth_headers):
        """التحقق من رفض الملفات غير الصالحة."""
        response = client.post(
            "/v2/ocr",
            headers=auth_headers,
            files={"file": ("test.txt", b"not an image", "text/plain")}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ocr_success(self, client, auth_headers, sample_image):
        """اختبار التعرف الناجح."""
        with open(sample_image, "rb") as f:
            response = client.post(
                "/v2/ocr",
                headers=auth_headers,
                files={"file": ("test.jpg", f, "image/jpeg")},
                data={"language": "ar", "enhance": "true"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "text" in data
        assert "confidence" in data
        assert "words" in data
        assert isinstance(data["confidence"], float)
        assert 0 <= data["confidence"] <= 1

    def test_ocr_arabic_text(self, client, auth_headers, sample_image):
        """التحقق من التعرف على النص العربي."""
        with open(sample_image, "rb") as f:
            response = client.post(
                "/v2/ocr",
                headers=auth_headers,
                files={"file": ("arabic.jpg", f, "image/jpeg")},
                data={"language": "ar"}
            )

        data = response.json()
        # التحقق من وجود حروف عربية
        assert any(
            '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
            for c in data["text"]
        )

    def test_ocr_batch(self, client, auth_headers):
        """اختبار المعالجة الدفعية."""
        # TODO: implement batch test
        pass


class TestHTREndpoint:
    """اختبارات التعرف على الخط اليدوي."""

    def test_htr_handwriting(self, client, auth_headers, sample_handwriting):
        """اختبار التعرف على خط يد."""
        with open(sample_handwriting, "rb") as f:
            response = client.post(
                "/v2/htr",
                headers=auth_headers,
                files={"file": ("handwriting.jpg", f, "image/jpeg")},
                data={"model": "trocr-large-handwritten-arabic"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "text" in data
        assert data["model_used"] == "trocr-large-handwritten-arabic"
