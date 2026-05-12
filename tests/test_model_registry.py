"""Tests for modules.core.model_registry.ModelRegistry"""
import pytest

class TestModelRegistry:
    """Test ModelRegistry singleton (without actually loading models)."""
    
    def setup_method(self):
        from modules.core.model_registry import ModelRegistry
        ModelRegistry.reset()
    
    def teardown_method(self):
        from modules.core.model_registry import ModelRegistry
        ModelRegistry.reset()
    
    def test_singleton(self):
        from modules.core.model_registry import ModelRegistry
        r1 = ModelRegistry()
        r2 = ModelRegistry()
        assert r1 is r2
    
    def test_get_instance(self):
        from modules.core.model_registry import ModelRegistry
        inst = ModelRegistry.get_instance()
        assert inst is not None
    
    def test_list_cached_empty(self):
        from modules.core.model_registry import ModelRegistry
        registry = ModelRegistry()
        assert registry.list_cached() == []
    
    def test_stats_empty(self):
        from modules.core.model_registry import ModelRegistry
        registry = ModelRegistry()
        stats = registry.stats()
        assert stats["cached_models"] == 0
    
    def test_clear_all(self):
        from modules.core.model_registry import ModelRegistry
        registry = ModelRegistry()
        registry._cache["test"] = "value"
        registry.clear()
        assert registry.list_cached() == []
    
    def test_clear_specific(self):
        from modules.core.model_registry import ModelRegistry
        registry = ModelRegistry()
        registry._cache["key1"] = "v1"
        registry._cache["key2"] = "v2"
        registry.clear("key1")
        assert "key1" not in registry.list_cached()
        assert "key2" in registry.list_cached()
    
    def test_reset(self):
        from modules.core.model_registry import ModelRegistry
        r1 = ModelRegistry()
        ModelRegistry.reset()
        r2 = ModelRegistry()
        assert r1 is not r2
