#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_api_performance.py
=============================

اختبارات أداء API.
"""

import time

import pytest


class TestAPIPerformance:
    """اختبارات الأداء."""

    @pytest.mark.benchmark
    def test_ocr_latency(self, benchmark, client, auth_headers, sample_image):
        """قياس زمن استجابة OCR."""
        def ocr_request():
            with open(sample_image, "rb") as f:
                return client.post(
                    "/v2/ocr",
                    headers=auth_headers,
                    files={"file": ("test.jpg", f, "image/jpeg")}
                )

        result = benchmark(ocr_request)
        assert result.status_code == 200

        # التحقق من الأداء
        stats = benchmark.stats
        assert stats["mean"] < 1.0  # أقل من ثانية واحدة

    @pytest.mark.benchmark
    def test_concurrent_requests(self, client, auth_headers, sample_image):
        """اختبار الطلبات المتزامنة."""
        import concurrent.futures

        def make_request():
            with open(sample_image, "rb") as f:
                return client.post(
                    "/v2/ocr",
                    headers=auth_headers,
                    files={"file": ("test.jpg", f, "image/jpeg")}
                )

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start

        # التحقق من النتائج
        assert all(r.status_code == 200 for r in results)
        assert duration < 30  # 50 طلب في أقل من 30 ثانية

    def test_memory_usage(self, client, auth_headers, sample_image):
        """اختبار استخدام الذاكرة."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # معالجة 100 صورة
        for _ in range(100):
            with open(sample_image, "rb") as f:
                client.post(
                    "/v2/ocr",
                    headers=auth_headers,
                    files={"file": ("test.jpg", f, "image/jpeg")}
                )

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_increase = mem_after - mem_before

        # التحقق من عدم وجود تسرب ذاكرة
        assert mem_increase < 500  # أقل من 500 MB زيادة
