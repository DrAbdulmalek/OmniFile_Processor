"""
OmniFile AI Processor — Gemini API Refinement
===============================================
Source: arabic-ocr-pro/ai/gemini_refiner.py

Provides optional AI-powered text refinement using Google's Gemini API.
This module can be used to improve OCR output by leveraging large language
models for contextual understanding and correction of Arabic text.

The module is optional and requires a valid Gemini API key.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default system prompt for Arabic text refinement
DEFAULT_SYSTEM_PROMPT = """You are an expert Arabic language editor specializing in OCR post-processing.
Your task is to correct OCR errors in Arabic text while preserving the original meaning.

Rules:
1. Fix common OCR misrecognitions (e.g., confused characters, missing diacritics)
2. Preserve the original text structure and formatting
3. Do NOT add new content or change the meaning
4. Fix only clear OCR errors, not stylistic choices
5. Return only the corrected text without explanations
6. If the text looks correct, return it unchanged

Common Arabic OCR errors to watch for:
- Confusion between similar characters (e.g., د and ر, ح and خ)
- Missing or incorrect diacritics
- Extra spaces between connected letters
- Reversed text direction issues
- Broken word connections"""


class GeminiRefiner:
    """AI-powered text refinement using Google Gemini API.

    Sends OCR text to Gemini for contextual analysis and correction.
    Particularly useful for complex Arabic text where pattern-based
    correction is insufficient.

    Attributes:
        api_key: Gemini API key.
        model: Gemini model name.
        system_prompt: System prompt for the AI.
        enabled: Whether the refiner is active.
        max_retries: Maximum API call retries.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        system_prompt: Optional[str] = None,
        enabled: bool = True,
        max_retries: int = 3,
    ) -> None:
        """Initialize the Gemini refiner.

        Args:
            api_key: Google Gemini API key. If None, attempts to load
                     from environment.
            model: Gemini model to use.
            system_prompt: System prompt for refinement instructions.
            enabled: Whether the refiner is active.
            max_retries: Maximum number of API call retries.
        """
        self.api_key = api_key or self._load_api_key_from_env()
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.enabled = enabled and self.api_key is not None
        self.max_retries = max_retries
        self._client = None

        if self.enabled:
            logger.info(f"Gemini refiner initialized (model={self.model})")
        else:
            logger.info("Gemini refiner disabled (no API key provided)")

    @staticmethod
    def _load_api_key_from_env() -> Optional[str]:
        """Attempt to load the Gemini API key from environment variables.

        Checks ``GEMINI_API_KEY`` and ``GOOGLE_API_KEY`` environment variables.

        Returns:
            API key string, or None if not found.
        """
        import os
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def _init_client(self) -> bool:
        """Initialize the Gemini API client.

        Returns:
            True if client initialized successfully, False otherwise.
        """
        if self._client is not None:
            return True

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=self.system_prompt,
            )
            logger.debug("Gemini API client initialized")
            return True
        except ImportError:
            logger.error(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
            return False
        except Exception as exc:
            logger.error(f"Failed to initialize Gemini client: {exc}")
            return False

    def is_available(self) -> bool:
        """Check if the Gemini refiner is available and configured.

        Returns:
            True if API key is set and client can be initialized.
        """
        return self.enabled

    # ------------------------------------------------------------------
    # Refinement API
    # ------------------------------------------------------------------

    def refine_text(self, text: str) -> str:
        """Refine OCR text using the Gemini API.

        Sends the text to Gemini for contextual analysis and correction.

        Args:
            text: OCR text to refine.

        Returns:
            Refined/corrected text, or original text if refinement fails.
        """
        if not self.enabled:
            return text

        if not text.strip():
            return text

        if not self._init_client():
            return text

        for attempt in range(self.max_retries):
            try:
                response = self._client.generate_content(text)
                refined = response.text.strip()

                if refined:
                    logger.debug(
                        f"Gemini refinement applied (attempt {attempt + 1})"
                    )
                    return refined
                else:
                    logger.debug("Gemini returned empty response")
                    return text

            except Exception as exc:
                logger.warning(
                    f"Gemini API call failed (attempt {attempt + 1}): {exc}"
                )
                if attempt == self.max_retries - 1:
                    logger.error("All Gemini API retries exhausted")
                    return text

        return text

    def refine_block(self, text: str, block_type: str = "text") -> str:
        """Refine text within a specific block context.

        Adjusts the refinement prompt based on block type for better results.

        Args:
            text: OCR text to refine.
            block_type: Type of document block
                        (text, heading, table, header, footer, etc.).

        Returns:
            Refined text, or original if refinement fails.
        """
        if not self.enabled:
            return text

        block_prompts = {
            "heading": (
                "This is a document heading. "
                "Pay extra attention to word boundaries."
            ),
            "table": (
                "This is table cell content. "
                "Preserve exact formatting and numbers."
            ),
            "footer": (
                "This is a page footer. "
                "Usually contains page numbers or short text."
            ),
            "header": (
                "This is a page header. "
                "Usually contains short titles or dates."
            ),
        }

        context = block_prompts.get(block_type, "")
        prompt = (
            f"{context}\n\nText to correct:\n{text}" if context else text
        )

        return self.refine_text(prompt)

    def refine_document_text(self, full_text: str) -> str:
        """Refine a complete document's text.

        Processes the full document text, sending it in chunks if
        necessary due to API token limits.

        Args:
            full_text: Complete OCR text from a document.

        Returns:
            Refined document text.
        """
        if not self.enabled:
            return full_text

        # Gemini context window is large enough for most documents
        # but we chunk very long texts just in case
        max_chunk_size = 8000
        chunks: list[str] = []
        lines = full_text.split("\n")
        current_chunk: list[str] = []

        for line in lines:
            current_chunk.append(line)
            if len("\n".join(current_chunk)) >= max_chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = []

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        refined_chunks: list[str] = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"Refining chunk {i + 1}/{len(chunks)}")
            refined = self.refine_text(chunk)
            refined_chunks.append(refined)

        return "\n".join(refined_chunks)
