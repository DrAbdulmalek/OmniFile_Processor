"""Ollama provider package."""

from ..defaults import OLLAMA_DEFAULT_BASE

from .client import OllamaProvider

__all__ = ["OLLAMA_DEFAULT_BASE", "OllamaProvider"]
