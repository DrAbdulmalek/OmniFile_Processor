"""
modules/core/model_registry.py
================================
Centralized model caching singleton for HuggingFace models.
Prevents redundant from_pretrained() calls across the project.

Usage:
    from modules.core.model_registry import ModelRegistry
    
    registry = ModelRegistry.get_instance()
    processor, model = registry.get_trocr("ar")
    tokenizer, mt_model = registry.get_translator("ar", "en")
"""

import logging
import threading
from functools import lru_cache
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Singleton registry for caching HuggingFace models.
    Models are loaded once and reused across all modules.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._cache: Dict[str, object] = {}
        self._initialized = True
        logger.info("[ModelRegistry] Singleton initialized")
    
    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get the singleton instance."""
        return cls()
    
    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        with cls._lock:
            cls._instance = None
    
    def get_trocr(self, lang: str = "ar") -> Tuple:
        """
        Get cached TrOCR processor + model.
        
        Args:
            lang: Language code ("ar" for Arabic handwriting)
            
        Returns:
            (processor, model) tuple
        """
        cache_key = f"trocr_{lang}"
        if cache_key not in self._cache:
            logger.info("[ModelRegistry] Loading TrOCR model for lang=%s", lang)
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            
            if lang == "ar":
                model_name = "microsoft/trocr-base-handwritten"
            else:
                model_name = "microsoft/trocr-base-handwritten"
            
            processor = TrOCRProcessor.from_pretrained(model_name)
            model = VisionEncoderDecoderModel.from_pretrained(model_name)
            model.eval()
            
            self._cache[cache_key] = (processor, model)
            logger.info("[ModelRegistry] TrOCR loaded and cached")
        
        return self._cache[cache_key]
    
    def get_translator(self, src: str, tgt: str) -> Tuple:
        """
        Get cached MarianMT tokenizer + model.
        
        Args:
            src: Source language code
            tgt: Target language code
            
        Returns:
            (tokenizer, model) tuple
        """
        cache_key = f"marian_{src}_{tgt}"
        if cache_key not in self._cache:
            logger.info("[ModelRegistry] Loading MarianMT %s->%s", src, tgt)
            from transformers import MarianTokenizer, MarianMTModel
            
            model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            
            self._cache[cache_key] = (tokenizer, model)
            logger.info("[ModelRegistry] MarianMT loaded and cached")
        
        return self._cache[cache_key]
    
    def get_detector(self) -> Tuple:
        """Get cached table detection model (DETR)."""
        cache_key = "table_detection"
        if cache_key not in self._cache:
            logger.info("[ModelRegistry] Loading DETR for table detection")
            from transformers import AutoImageProcessor, AutoModelForObjectDetection
            
            processor = AutoImageProcessor.from_pretrained(
                "microsoft/dit-base-finetuned-publaynet"
            )
            model = AutoModelForObjectDetection.from_pretrained(
                "microsoft/dit-base-finetuned-publaynet"
            )
            model.eval()
            
            self._cache[cache_key] = (processor, model)
            logger.info("[ModelRegistry] DETR loaded and cached")
        
        return self._cache[cache_key]
    
    def get_custom(self, model_name: str, processor_name: str = None, **kwargs):
        """
        Get any cached model by name.
        
        Args:
            model_name: HuggingFace model identifier
            processor_name: Optional separate processor name
            **kwargs: Additional arguments for from_pretrained
            
        Returns:
            model or (processor, model) if processor_name is given
        """
        cache_key = f"custom_{model_name}"
        if cache_key not in self._cache:
            logger.info("[ModelRegistry] Loading model: %s", model_name)
            from transformers import AutoModel, AutoProcessor
            
            if processor_name:
                processor = AutoProcessor.from_pretrained(processor_name, **kwargs)
                model = AutoModel.from_pretrained(model_name, **kwargs)
                self._cache[cache_key] = (processor, model)
            else:
                model = AutoModel.from_pretrained(model_name, **kwargs)
                self._cache[cache_key] = model
            
            logger.info("[ModelRegistry] Model '%s' loaded and cached", model_name)
        
        return self._cache[cache_key]
    
    def clear(self, key: str = None):
        """Clear cache. If key is None, clears all."""
        if key:
            self._cache.pop(key, None)
            logger.info("[ModelRegistry] Cleared cache for: %s", key)
        else:
            self._cache.clear()
            logger.info("[ModelRegistry] Cleared all cache")
    
    def list_cached(self) -> list:
        """List all cached model keys."""
        return list(self._cache.keys())
    
    def stats(self) -> dict:
        """Registry statistics."""
        return {
            "cached_models": len(self._cache),
            "cache_keys": list(self._cache.keys()),
        }
