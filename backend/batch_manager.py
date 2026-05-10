#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/batch_manager.py
=========================

Batch processing manager for OmniFile Processor.

Features:
- Background task processing via Celery
- Real-time progress tracking via WebSocket
- Retry logic for failed files
- Batch-level configuration (OCR engine, language, quality)
- Result export in multiple formats
- Role-based access control (viewer, reviewer, operator, admin)
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class UserRole(str, Enum):
    VIEWER = "viewer"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    ADMIN = "admin"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BatchFile:
    """Single file within a batch."""
    file_id: str
    filename: str
    filepath: str
    status: str = FileStatus.PENDING.value
    progress: int = 0
    confidence: float = 0.0
    error: str = ""
    result_text: str = ""
    processing_time: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class BatchConfig:
    """Configuration for a batch processing run."""
    ocr_engine: str = "trocr"
    language: str = "ar"
    quality: str = "medium"  # fast, medium, high
    auto_correct: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["txt", "json"])
    dpi: int = 300
    max_file_size_mb: int = 50


@dataclass
class Batch:
    """A batch of files to process."""
    batch_id: str = ""
    name: str = ""
    config: Dict = field(default_factory=dict)
    files: List[Dict] = field(default_factory=list)
    status: str = "pending"
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.batch_id:
            self.batch_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.updated_at:
            self.updated_at = self.created_at

    def get_stats(self) -> Dict:
        total = len(self.files)
        completed = sum(1 for f in self.files if f["status"] == FileStatus.COMPLETED.value)
        failed = sum(1 for f in self.files if f["status"] == FileStatus.FAILED.value)
        processing = sum(1 for f in self.files if f["status"] == FileStatus.PROCESSING.value)
        pending = sum(1 for f in self.files if f["status"] == FileStatus.PENDING.value)

        confidences = [f["confidence"] for f in self.files if f["confidence"] > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "pending": pending,
            "avg_confidence": round(avg_confidence, 4),
            "progress": int(100 * completed / max(total, 1)),
        }

    def to_dict(self) -> Dict:
        return {
            "batch_id": self.batch_id,
            "name": self.name,
            "config": self.config,
            "files": self.files,
            "status": self.status,
            "stats": self.get_stats(),
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ============================================================================
# Role Permissions
# ============================================================================

ROLE_PERMISSIONS = {
    UserRole.VIEWER: {"view_results", "export"},
    UserRole.REVIEWER: {"view_results", "export", "retry_failed", "correct_text"},
    UserRole.OPERATOR: {"view_results", "export", "retry_failed", "correct_text", "upload_batch", "update_config"},
    UserRole.ADMIN: {"view_results", "export", "retry_failed", "correct_text", "upload_batch", "update_config", "manage_users", "view_logs"},
}


def check_permission(role: str, action: str) -> bool:
    """Check if a role has permission for an action."""
    permissions = ROLE_PERMISSIONS.get(role, set())
    return action in permissions


# ============================================================================
# Batch Manager
# ============================================================================

class BatchManager:
    """
    Manages batch processing of files.

    Usage:
        manager = BatchManager(storage_dir="./batch_data")

        # Create a new batch
        batch = manager.create_batch(
            name="Invoice Batch 001",
            config=BatchConfig(ocr_engine="trocr", language="ar")
        )

        # Add files
        manager.add_files(batch.batch_id, ["/path/to/file1.pdf", "/path/to/file2.png"])

        # Process (with progress callback)
        def on_progress(file_id, progress, message):
            print(f"  {file_id}: {progress}% - {message}")

        manager.process_batch(batch.batch_id, progress_callback=on_progress)

        # Get results
        results = manager.get_batch_results(batch.batch_id)
    """

    def __init__(self, storage_dir: str = "./batch_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._batches: Dict[str, Batch] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._load_existing_batches()

    def _load_existing_batches(self):
        """Load existing batches from disk."""
        batches_dir = self.storage_dir / "batches"
        if batches_dir.exists():
            for batch_file in batches_dir.glob("*.json"):
                try:
                    data = json.loads(batch_file.read_text(encoding="utf-8"))
                    batch = Batch(**data)
                    self._batches[batch.batch_id] = batch
                except Exception as e:
                    logger.error(f"Failed to load batch {batch_file}: {e}")

    def _save_batch(self, batch: Batch):
        """Persist batch to disk."""
        batches_dir = self.storage_dir / "batches"
        batches_dir.mkdir(parents=True, exist_ok=True)
        batch_file = batches_dir / f"{batch.batch_id}.json"
        batch_file.write_text(json.dumps(asdict(batch), ensure_ascii=False, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def create_batch(
        self,
        name: str,
        config: Optional[BatchConfig] = None,
        created_by: str = "anonymous"
    ) -> Batch:
        """Create a new batch."""
        batch = Batch(
            name=name,
            config=config.__dict__ if config else BatchConfig().__dict__,
            created_by=created_by
        )
        self._batches[batch.batch_id] = batch
        self._save_batch(batch)
        logger.info(f"Created batch {batch.batch_id}: {name}")
        return batch

    def get_batch(self, batch_id: str) -> Optional[Batch]:
        """Get a batch by ID."""
        return self._batches.get(batch_id)

    def list_batches(self, status: Optional[str] = None) -> List[Dict]:
        """List all batches, optionally filtered by status."""
        batches = []
        for batch in self._batches.values():
            if status and batch.status != status:
                continue
            batches.append(batch.to_dict())
        return sorted(batches, key=lambda x: x["created_at"], reverse=True)

    def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch and its files."""
        if batch_id not in self._batches:
            return False

        del self._batches[batch_id]
        batch_file = self.storage_dir / "batches" / f"{batch_id}.json"
        if batch_file.exists():
            batch_file.unlink()
        logger.info(f"Deleted batch {batch_id}")
        return True

    # -------------------------------------------------------------------------
    # File Management
    # -------------------------------------------------------------------------

    def add_files(self, batch_id: str, filepaths: List[str]) -> int:
        """Add files to a batch."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        added = 0
        for filepath in filepaths:
            path = Path(filepath)
            if not path.exists():
                logger.warning(f"File not found: {filepath}")
                continue

            if path.stat().st_size > 50 * 1024 * 1024:
                logger.warning(f"File too large (>50MB): {filepath}")
                continue

            batch_file = BatchFile(
                file_id=str(uuid.uuid4())[:8],
                filename=path.name,
                filepath=str(path.absolute()),
            )
            batch.files.append(batch_file.to_dict())
            added += 1

        batch.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_batch(batch)
        logger.info(f"Added {added} files to batch {batch_id}")
        return added

    def remove_files(self, batch_id: str, file_ids: List[str]) -> int:
        """Remove files from a batch."""
        batch = self._batches.get(batch_id)
        if not batch:
            return 0

        before = len(batch.files)
        batch.files = [f for f in batch.files if f["file_id"] not in file_ids]
        removed = before - len(batch.files)

        batch.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_batch(batch)
        return removed

    # -------------------------------------------------------------------------
    # Processing
    # -------------------------------------------------------------------------

    def register_progress_callback(self, batch_id: str, callback: Callable):
        """Register a progress callback for a batch."""
        if batch_id not in self._progress_callbacks:
            self._progress_callbacks[batch_id] = []
        self._progress_callbacks[batch_id].append(callback)

    def _notify_progress(self, batch_id: str, file_id: str, progress: int, message: str):
        """Notify all registered callbacks."""
        for callback in self._progress_callbacks.get(batch_id, []):
            try:
                callback(file_id, progress, message)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def process_batch(
        self,
        batch_id: str,
        progress_callback: Optional[Callable] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        Process all pending files in a batch.

        Args:
            batch_id: Batch identifier
            progress_callback: Optional callback(file_id, progress, message)
            max_retries: Maximum retry attempts for failed files

        Returns:
            Processing summary
        """
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        if progress_callback:
            self.register_progress_callback(batch_id, progress_callback)

        batch.status = "processing"
        self._save_batch(batch)

        config = BatchConfig(**batch["config"]) if isinstance(batch.config, dict) else batch.config
        summary = {"processed": 0, "succeeded": 0, "failed": 0, "total_time": 0.0}
        start_time = time.time()

        for file_data in batch.files:
            if file_data["status"] in (FileStatus.COMPLETED.value, FileStatus.PROCESSING.value):
                continue

            file_id = file_data["file_id"]
            file_data["status"] = FileStatus.PROCESSING.value
            file_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._save_batch(batch)

            self._notify_progress(batch_id, file_id, 0, "Starting...")

            try:
                result = self._process_single_file(
                    file_data=file_data,
                    config=config,
                    batch_id=batch_id,
                    file_id=file_id,
                )

                file_data["status"] = FileStatus.COMPLETED.value
                file_data["confidence"] = result.get("confidence", 0.0)
                file_data["result_text"] = result.get("text", "")
                file_data["progress"] = 100
                summary["succeeded"] += 1

                self._notify_progress(batch_id, file_id, 100, "Completed")

            except Exception as e:
                retry_count = file_data.get("retry_count", 0)

                if retry_count < max_retries:
                    file_data["retry_count"] = retry_count + 1
                    file_data["status"] = FileStatus.RETRYING.value
                    file_data["error"] = str(e)
                    logger.warning(f"Retry {retry_count + 1}/{max_retries} for {file_id}: {e}")

                    # Try again
                    try:
                        result = self._process_single_file(
                            file_data=file_data,
                            config=config,
                            batch_id=batch_id,
                            file_id=file_id,
                        )
                        file_data["status"] = FileStatus.COMPLETED.value
                        file_data["confidence"] = result.get("confidence", 0.0)
                        file_data["result_text"] = result.get("text", "")
                        file_data["progress"] = 100
                        summary["succeeded"] += 1
                        self._notify_progress(batch_id, file_id, 100, "Completed (retry)")
                    except Exception as e2:
                        file_data["status"] = FileStatus.FAILED.value
                        file_data["error"] = f"{e} | Retry failed: {e2}"
                        summary["failed"] += 1
                        self._notify_progress(batch_id, file_id, -1, f"Failed: {e2}")
                else:
                    file_data["status"] = FileStatus.FAILED.value
                    file_data["error"] = str(e)
                    summary["failed"] += 1
                    self._notify_progress(batch_id, file_id, -1, f"Failed: {e}")

            file_data["processing_time"] = round(time.time() - start_time, 2)
            file_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            summary["processed"] += 1
            self._save_batch(batch)

        batch.status = "completed"
        batch.updated_at = datetime.utcnow().isoformat() + "Z"
        summary["total_time"] = round(time.time() - start_time, 2)
        self._save_batch(batch)

        logger.info(f"Batch {batch_id} completed: {summary}")
        return summary

    def _process_single_file(
        self,
        file_data: Dict,
        config: BatchConfig,
        batch_id: str,
        file_id: str,
    ) -> Dict:
        """Process a single file using the configured OCR engine."""
        filepath = file_data["filepath"]
        ext = Path(filepath).suffix.lower()

        # Determine processing method
        if ext in (".pdf",):
            return self._process_pdf(filepath, config, batch_id, file_id)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            return self._process_image(filepath, config, batch_id, file_id)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def _process_image(self, filepath: str, config: BatchConfig, batch_id: str, file_id: str) -> Dict:
        """Process a single image file."""
        try:
            from modules.vision.ocr_engine import OCREngine
        except ImportError:
            from src import OCREngine

        ocr = OCREngine(engine=config.ocr_engine)

        self._notify_progress(batch_id, file_id, 30, "Loading image...")

        from PIL import Image
        image = Image.open(filepath)

        self._notify_progress(batch_id, file_id, 60, "Running OCR...")

        result = ocr.recognize(image, language=config.language)

        # Auto-correct if enabled
        if config.auto_correct and result.text:
            try:
                from modules.core.spell_checker import HybridSpellChecker
                checker = HybridSpellChecker()
                result.text = checker.correct(result.text)
            except ImportError:
                pass

        self._notify_progress(batch_id, file_id, 90, "Saving results...")

        return {
            "text": result.text if hasattr(result, 'text') else str(result),
            "confidence": getattr(result, 'confidence', 0.0),
        }

    def _process_pdf(self, filepath: str, config: BatchConfig, batch_id: str, file_id: str) -> Dict:
        """Process a PDF file (extract text from all pages)."""
        try:
            from modules.vision.pdf_processor import PDFProcessor
        except ImportError:
            raise ImportError("PDF processing requires PyMuPDF. Install: pip install PyMuPDF")

        processor = PDFProcessor()

        self._notify_progress(batch_id, file_id, 20, "Loading PDF...")

        pages = processor.extract_text(filepath, language=config.language)

        all_text = []
        total_confidence = 0.0

        for i, page in enumerate(pages):
            progress = 20 + int(60 * (i + 1) / max(len(pages), 1))
            self._notify_progress(batch_id, file_id, progress, f"Processing page {i+1}/{len(pages)}...")

            text = page.text if hasattr(page, 'text') else str(page)
            conf = page.confidence if hasattr(page, 'confidence') else 0.0
            all_text.append(text)
            total_confidence += conf

        combined_text = "\n\n".join(all_text)
        avg_confidence = total_confidence / max(len(pages), 1)

        return {
            "text": combined_text,
            "confidence": avg_confidence,
        }

    # -------------------------------------------------------------------------
    # Retry & Export
    # -------------------------------------------------------------------------

    def retry_failed(self, batch_id: str) -> Dict:
        """Retry all failed files in a batch."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        failed_count = 0
        for file_data in batch.files:
            if file_data["status"] == FileStatus.FAILED.value:
                file_data["status"] = FileStatus.PENDING.value
                file_data["error"] = ""
                file_data["retry_count"] = 0
                failed_count += 1

        batch.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_batch(batch)

        if failed_count > 0:
            return self.process_batch(batch_id)

        return {"message": "No failed files to retry"}

    def get_batch_results(self, batch_id: str, file_id: Optional[str] = None) -> Dict:
        """Get results for a batch or specific file."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        if file_id:
            for f in batch.files:
                if f["file_id"] == file_id:
                    return f
            return {}

        return batch.to_dict()

    def export_results(
        self,
        batch_id: str,
        output_format: str = "json",
        output_dir: Optional[str] = None
    ) -> str:
        """Export batch results to a file."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        output_dir = Path(output_dir or self.storage_dir / "exports")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{batch.name.replace(' ', '_')}_{timestamp}.{output_format}"
        filepath = output_dir / filename

        if output_format == "json":
            data = json.dumps(batch.to_dict(), ensure_ascii=False, indent=2)
            filepath.write_text(data, encoding="utf-8")

        elif output_format == "txt":
            lines = [f"Batch: {batch.name}", f"Date: {batch.created_at}", "=" * 50, ""]
            for f in batch.files:
                lines.append(f"--- {f['filename']} ({f['status']}) ---")
                if f.get("result_text"):
                    lines.append(f["result_text"])
                if f.get("error"):
                    lines.append(f"ERROR: {f['error']}")
                lines.append("")
            filepath.write_text("\n".join(lines), encoding="utf-8")

        elif output_format == "csv":
            import csv
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["filename", "status", "confidence", "text", "error"])
                writer.writeheader()
                for file_data in batch.files:
                    writer.writerow({
                        "filename": file_data["filename"],
                        "status": file_data["status"],
                        "confidence": file_data.get("confidence", 0),
                        "text": file_data.get("result_text", "")[:200],
                        "error": file_data.get("error", ""),
                    })

        else:
            raise ValueError(f"Unsupported export format: {output_format}")

        return str(filepath)
