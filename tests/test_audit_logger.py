"""Tests for modules.audit.audit_logger.AuditLogger"""
import pytest
import json

class TestAuditLogger:
    """Test AuditLogger with temp directory."""
    
    def _make_logger(self, tmp_path):
        from modules.audit.audit_logger import AuditLogger
        log_dir = str(tmp_path / "audit_logs")
        return AuditLogger(log_dir=log_dir, reviewer_id="TestUser")
    
    def test_log_decision(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_decision(
            page_id="p1", line_idx=0,
            trocr_text="مرحبا", easyocr_text="مرحبا",
            similarity=0.95,
            recommendation="AUTO_ACCEPT",
            critical_alerts=[],
            final_text="مرحبا",
            action="AUTO_ACCEPT",
            confidence="HIGH",
            model_version="v5.1"
        )
        logs = logger.read_logs()
        assert len(logs) == 1
        assert logs[0]["page_id"] == "p1"
    
    def test_read_logs_limit(self, tmp_path):
        logger = self._make_logger(tmp_path)
        for i in range(5):
            logger.log_decision(
                page_id=f"p{i}", line_idx=0,
                trocr_text="test", easyocr_text="test",
                similarity=0.9, recommendation="AUTO_ACCEPT",
                critical_alerts=[], final_text="test",
                action="AUTO_ACCEPT", confidence="HIGH",
                model_version="v5.1"
            )
        logs = logger.read_logs(limit=3)
        assert len(logs) == 3
    
    def test_get_stats(self, tmp_path):
        logger = self._make_logger(tmp_path)
        logger.log_decision(
            page_id="p1", line_idx=0, trocr_text="a", easyocr_text="a",
            similarity=0.95, recommendation="AUTO_ACCEPT",
            critical_alerts=[], final_text="a",
            action="AUTO_ACCEPT", confidence="HIGH", model_version="v5.1"
        )
        logger.log_decision(
            page_id="p2", line_idx=0, trocr_text="b", easyocr_text="c",
            similarity=0.3, recommendation="MANUAL_REVIEW_REQUIRED",
            critical_alerts=["dosage"], final_text="b",
            action="USER_OVERRIDE", confidence="LOW", model_version="v5.1"
        )
        stats = logger.get_stats()
        assert stats["total"] == 2
        assert "auto_rate" in stats
