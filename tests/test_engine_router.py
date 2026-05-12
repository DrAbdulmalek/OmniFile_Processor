"""Tests for modules.core.engine_router.EngineRouter"""
import pytest

class TestEngineRouter:
    """Test EngineRouter - pure logic, no file I/O."""
    
    def test_default_init(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter()
        assert router.summary()["profile"] == "balanced"
    
    def test_low_profile(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter(profile="low")
        s = router.summary()
        assert s["profile"] == "low"
    
    def test_high_profile(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter(profile="high")
        engines, _ = router.select(image_quality=0.9, language="ar")
        assert len(engines) >= 2
    
    def test_select_returns_engines(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter()
        engines, reasons = router.select(language="ar")
        assert isinstance(engines, list)
        assert isinstance(reasons, list)
        assert len(engines) > 0
    
    def test_select_handwriting_block(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter()
        engines, _ = router.select(block_type="handwriting")
        assert len(engines) > 0
    
    def test_estimate_time(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter()
        time_est = router.estimate_time(["EasyOCR", "TrOCR"])
        assert isinstance(time_est, float)
        assert time_est > 0
    
    def test_filter_by_ram(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter(available_ram_gb=1.0)
        engines, _ = router.select()
        # Should not include heavy engines
        for e in engines:
            assert e in ["EasyOCR", "Tesseract"]
    
    def test_gpu_mode(self):
        from modules.core.engine_router import EngineRouter
        router = EngineRouter(use_gpu=True, profile="high")
        engines, _ = router.select(language="en")
        assert len(engines) > 0
