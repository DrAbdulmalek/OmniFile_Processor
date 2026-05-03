"""
OmniFile AI Processor — Secure File Handler
============================================
Source: advanced-ocr/utils/file_handler.py

Handles file uploads safely, preventing path traversal and other attacks.
Uses tempfile for secure temporary file storage.

Security Features:
1. Uses tempfile.NamedTemporaryFile instead of user-provided paths
2. Validates file extensions against an allowlist
3. Validates file sizes
4. Restricts file operations to designated directories
5. Sanitizes filenames
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default allowed extensions for OCR processing
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".tiff", ".tif",
    ".bmp", ".webp", ".pdf", ".gif",
}


class SecureFileHandler:
    """Handles file operations securely for file processing.

    SECURITY FEATURES:
    1. Uses tempfile.NamedTemporaryFile instead of user-provided paths
    2. Validates file extensions
    3. Validates file sizes
    4. Restricts file operations to designated directories
    5. Sanitizes filenames
    """

    def __init__(
        self,
        upload_dir: Optional[str] = None,
        max_size_mb: int = 50,
        allowed_extensions: Optional[set] = None,
    ) -> None:
        """Initialize the secure file handler.

        Args:
            upload_dir: Directory for storing uploaded files.
                        Defaults to a temp directory.
            max_size_mb: Maximum file size in megabytes.
            allowed_extensions: Set of allowed file extensions.
        """
        self.upload_dir = (
            Path(upload_dir)
            if upload_dir
            else Path(tempfile.gettempdir()) / "ocr_uploads"
        )
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS

        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(
        self,
        file_content: bytes,
        filename: str,
    ) -> str:
        """Save an uploaded file securely.

        **NEVER** uses user-provided filename directly as a path.
        Always uses tempfile and validates extensions.

        Args:
            file_content: Raw file bytes.
            filename: Original filename (used ONLY for extension).

        Returns:
            Path to the saved file.

        Raises:
            ValueError: If file extension is not allowed or size exceeds
                        the configured limit.
        """
        # Validate extension
        ext = Path(filename).suffix.lower()
        if ext not in self.allowed_extensions:
            raise ValueError(
                f"File extension '{ext}' is not allowed. "
                f"Allowed: {', '.join(sorted(self.allowed_extensions))}"
            )

        # Validate size
        if len(file_content) > self.max_size_bytes:
            raise ValueError(
                f"File size ({len(file_content) / 1024 / 1024:.1f} MB) "
                f"exceeds maximum "
                f"({self.max_size_bytes / 1024 / 1024:.0f} MB)"
            )

        # SECURE: Use tempfile — NEVER construct path from user input
        with tempfile.NamedTemporaryFile(
            dir=str(self.upload_dir),
            suffix=ext,
            delete=False,
            prefix="ocr_",
        ) as tmp:
            tmp.write(file_content)
            saved_path = tmp.name

        logger.info(
            f"Securely saved upload: {saved_path} "
            f"({len(file_content)} bytes)"
        )
        return saved_path

    def cleanup(self, file_path: str) -> None:
        """Remove a temporary file after processing.

        Only deletes files that are within the upload directory
        to prevent accidental deletion of unrelated files.

        Args:
            file_path: Path to the file to remove.
        """
        try:
            path = Path(file_path)
            if path.exists() and str(path.parent).startswith(
                str(self.upload_dir)
            ):
                path.unlink()
                logger.debug(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")

    def validate_file(self, file_path: str) -> bool:
        """Validate that a file is within the allowed directory.

        Prevents path traversal attacks by checking that the resolved
        file path starts with the upload directory path.

        Args:
            file_path: Path to validate.

        Returns:
            True if the file is within the allowed directory.
        """
        try:
            path = Path(file_path).resolve()
            upload = self.upload_dir.resolve()
            return str(path).startswith(str(upload))
        except Exception:
            return False

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to prevent directory traversal.

        .. note::
            This alone is **NOT** sufficient for security.
            Always use tempfile for actual file operations.

        Args:
            filename: Raw filename to sanitize.

        Returns:
            Sanitized filename (basename only, max 255 chars, no null bytes).
        """
        # Remove path components
        name = Path(filename).name
        # Remove null bytes
        name = name.replace("\x00", "")
        # Limit length
        name = name[:255]
        return name
