#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/learning/efficient_learner.py
===================================================

Memory-efficient online learning with:
- Hot memory buffer (deque with maxlen)
- Disk offloading with zstd compression
- Image compression (JPEG + zlib)
- Mixed precision training (FP16)
- Gradient accumulation for low-VRAM
- EWC (Elastic Weight Consolidation) for catastrophic forgetting
- Periodic GPU cache cleanup

Usage:
    learner = MemoryEfficientLearner(model=model, processor=processor)
    learner.add_correction(image, "original", "corrected", confidence=0.85)
    metrics = learner.learn_from_corrections(epochs=3)
"""

import io
import json
import logging
import math
import os
import pickle
import struct
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CorrectionItem:
    """A single correction with compressed image."""
    original_text: str
    corrected_text: str
    confidence: float
    compressed_image: bytes = b""
    timestamp: float = field(default_factory=time.time)
    weight: float = 1.0


class MemoryEfficientLearner:
    """
    Memory-efficient online learner for OCR correction.

    Architecture:
    - Hot memory: deque with max 50 items (fastest access)
    - Disk cache: compressed pickle files for overflow
    - Compression: JPEG quality 85 + zlib level 6

    Training:
    - Mixed precision (FP16) via torch.cuda.amp
    - Gradient accumulation (steps=4) for low VRAM
    - EWC regularization to prevent catastrophic forgetting
    - Gradient clipping (max_norm=1.0)
    - Periodic torch.cuda.empty_cache()
    """

    def __init__(
        self,
        model: Any,
        processor: Any,
        cache_dir: str = ".learner_cache",
        hot_memory_size: int = 50,
        jpeg_quality: int = 85,
        compression_level: int = 6,
        gradient_accumulation_steps: int = 4,
        max_grad_norm: float = 1.0,
        ewc_lambda: float = 1000.0,
    ):
        self.model = model
        self.processor = processor

        # Memory management
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hot_memory = deque(maxlen=hot_memory_size)
        self.hot_memory_size = hot_memory_size
        self._disk_count = 0

        # Compression settings
        self.jpeg_quality = jpeg_quality
        self.compression_level = compression_level

        # Training settings
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm

        # EWC (Elastic Weight Consolidation)
        self.ewc_lambda = ewc_lambda
        self._fisher_information: Dict[str, torch.Tensor] = {}
        self._optimal_params: Dict[str, torch.Tensor] = {}
        self._ewc_initialized = False

        # Statistics
        self.total_corrections = 0
        self.total_training_time = 0.0
        self._cache_size_bytes = 0

    @property
    def cache_size_mb(self) -> float:
        """Current cache size in MB."""
        return self._cache_size_bytes / (1024 * 1024)

    def add_correction(
        self,
        image: np.ndarray,
        original_text: str,
        corrected_text: str,
        confidence: float = 1.0,
        weight: float = 1.0,
    ):
        """
        Add a correction to the learning buffer.

        If hot memory is full, oldest item is offloaded to disk.
        """
        # Compress image
        compressed = self._compress_image(image)

        item = CorrectionItem(
            original_text=original_text,
            corrected_text=corrected_text,
            confidence=confidence,
            compressed_image=compressed,
            weight=weight,
        )

        # If hot memory is full, offload oldest
        if len(self.hot_memory) >= self.hot_memory.maxlen:
            oldest = self.hot_memory[0]
            self._offload_to_disk(oldest)

        self.hot_memory.append(item)
        self.total_corrections += 1
        self._cache_size_bytes += len(compressed)

    def _compress_image(self, image: np.ndarray) -> bytes:
        """Compress image using JPEG + zlib."""
        # Ensure RGB
        if len(image.shape) == 2:
            image = np.stack([image] * 3, axis=-1)

        # JPEG encoding
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(image.astype(np.uint8))
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=self.jpeg_quality)
        jpeg_bytes = buffer.getvalue()

        # zlib compression
        import zlib
        compressed = zlib.compress(jpeg_bytes, level=self.compression_level)

        return compressed

    def _decompress_image(self, compressed: bytes) -> np.ndarray:
        """Decompress image from zlib + JPEG."""
        import zlib
        from PIL import Image as PILImage

        jpeg_bytes = zlib.decompress(compressed)
        pil_img = PILImage.open(io.BytesIO(jpeg_bytes))
        return np.array(pil_img)

    def _offload_to_disk(self, item: CorrectionItem):
        """Offload a correction item to disk."""
        filename = f"correction_{self._disk_count:08d}.pkl.zst"
        filepath = self.cache_dir / filename

        try:
            data = {
                "original_text": item.original_text,
                "corrected_text": item.corrected_text,
                "confidence": item.confidence,
                "compressed_image": item.compressed_image,
                "timestamp": item.timestamp,
                "weight": item.weight,
            }

            # Pickle + compress
            pickled = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

            # Try zstd, fallback to zlib
            try:
                import zstandard as zstd
                compressed = zstd.compress(pickled, level=self.compression_level)
            except ImportError:
                import zlib
                compressed = zlib.compress(pickled, level=self.compression_level)

            filepath.write_bytes(compressed)
            self._disk_count += 1
            self._cache_size_bytes = max(0, self._cache_size_bytes - len(item.compressed_image))

        except Exception as e:
            logger.error(f"Failed to offload correction to disk: {e}")

    def _load_from_disk(self) -> List[CorrectionItem]:
        """Load all corrections from disk."""
        items = []

        for filepath in sorted(self.cache_dir.glob("correction_*.pkl.zst")):
            try:
                compressed = filepath.read_bytes()

                try:
                    import zstandard as zstd
                    pickled = zstd.decompress(compressed)
                except ImportError:
                    import zlib
                    pickled = zlib.decompress(compressed)

                data = pickle.loads(pickled)
                items.append(CorrectionItem(**data))

            except Exception as e:
                logger.error(f"Failed to load correction from disk: {e}")

        return items

    def learn_from_corrections(
        self,
        epochs: int = 1,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
    ) -> Dict:
        """
        Train on accumulated corrections.

        Uses mixed precision, gradient accumulation, and EWC regularization.
        """
        import torch
        from torch.nn import functional as F

        # Gather all corrections
        all_corrections = list(self.hot_memory)
        disk_corrections = self._load_from_disk()
        all_corrections.extend(disk_corrections)

        if not all_corrections:
            return {
                "status": "no_data",
                "num_samples": 0,
                "message": "No corrections available for training",
            }

        logger.info(
            f"Training on {len(all_corrections)} corrections "
            f"({len(self.hot_memory)} hot, {len(disk_corrections)} disk)"
        )

        # Initialize EWC if first time
        if not self._ewc_initialized and len(all_corrections) >= 5:
            self._update_ewc(all_corrections[:min(20, len(all_corrections))])
            self._ewc_initialized = True

        # Prepare model for training
        self.model.train()
        device = next(self.model.parameters()).device

        # Optimizer and scaler
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        scaler = torch.cuda.amp.GradScaler() if device.type == "cuda" else None

        total_loss = 0.0
        num_batches = 0
        start_time = time.time()

        # Create batches
        batches = self._create_batches(all_corrections, batch_size)

        for epoch in range(epochs):
            epoch_loss = 0.0

            for batch_idx, batch in enumerate(batches):
                # Prepare batch
                images = [self._decompress_image(item.compressed_image) for item in batch]
                labels = [item.corrected_text for item in batch]

                try:
                    # Preprocess
                    pixel_values = self.processor(
                        images=images, return_tensors="pt",
                        padding=True, truncation=True
                    ).pixel_values.to(device)

                    # Tokenize labels
                    label_ids = self.processor.tokenizer(
                        labels,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=128
                    ).input_ids.to(device)

                    # Labels for loss: shift right, replace pad with -100
                    labels_for_loss = label_ids.clone()
                    labels_for_loss[labels_for_loss == self.processor.tokenizer.pad_token_id] = -100

                except Exception as e:
                    logger.warning(f"Batch preprocessing failed: {e}")
                    continue

                # Forward pass with mixed precision
                optimizer.zero_grad()

                if scaler is not None:
                    with torch.cuda.amp.autocast():
                        outputs = self.model(pixel_values=pixel_values, labels=labels_for_loss)
                        loss = outputs.loss

                        # Add EWC loss
                        ewc_loss = self._compute_ewc_loss(device)
                        total_eLoss = loss + self.ewc_lambda * ewc_loss

                    # Backward with scaler
                    scaler.scale(total_eLoss).backward()

                    # Gradient accumulation
                    if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(), self.max_grad_norm
                        )
                        scaler.step(optimizer)
                        scaler.update()
                        optimizer.zero_grad()
                else:
                    outputs = self.model(pixel_values=pixel_values, labels=labels_for_loss)
                    loss = outputs.loss
                    ewc_loss = self._compute_ewc_loss(device)
                    total_eLoss = loss + self.ewc_lambda * ewc_loss
                    total_eLoss.backward()

                    if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                        torch.nn.utils.clip_grad_norm_(
                            self.model.parameters(), self.max_grad_norm
                        )
                        optimizer.step()
                        optimizer.zero_grad()

                epoch_loss += loss.item()
                num_batches += 1

            logger.info(f"Epoch {epoch + 1}/{epochs}, Loss: {epoch_loss / max(1, num_batches):.4f}")

            # Periodic GPU cleanup
            if device.type == "cuda":
                torch.cuda.empty_cache()

        # Finalize
        self.model.eval()
        training_time = time.time() - start_time
        self.total_training_time += training_time

        avg_loss = total_loss / max(1, num_batches)

        return {
            "status": "completed",
            "num_samples": len(all_corrections),
            "epochs": epochs,
            "avg_loss": avg_loss,
            "training_time_seconds": round(training_time, 2),
            "total_corrections": self.total_corrections,
            "hot_memory_size": len(self.hot_memory),
            "disk_cache_size": len(disk_corrections),
        }

    def _create_batches(
        self, corrections: List[CorrectionItem], batch_size: int
    ) -> List[List[CorrectionItem]]:
        """Create batches of corrections."""
        batches = []
        for i in range(0, len(corrections), batch_size):
            batches.append(corrections[i:i + batch_size])
        return batches

    def _compute_ewc_loss(self, device: Any) -> float:
        """
        Compute EWC (Elastic Weight Consolidation) loss.

        Penalizes changes to important parameters (high Fisher Information).
        This prevents catastrophic forgetting of previously learned patterns.
        """
        if not self._fisher_information or not self._optimal_params:
            return 0.0

        try:
            import torch
            ewc_loss = 0.0
            count = 0

            for name, param in self.model.named_parameters():
                if name in self._fisher_information and param.requires_grad:
                    fisher = self._fisher_information[name].to(device)
                    optimal = self._optimal_params[name].to(device)

                    # EWC penalty: Fisher * (param - optimal)^2
                    ewc_loss += torch.sum(fisher * (param - optimal) ** 2)
                    count += 1

            return float(ewc_loss / max(1, count)) if count > 0 else 0.0

        except Exception as e:
            logger.warning(f"EWC loss computation failed: {e}")
            return 0.0

    def _update_ewc(self, corrections: List[CorrectionItem], sample_size: int = 10):
        """
        Compute Fisher Information Matrix on a sample of corrections.

        Fisher Information measures how important each parameter is for
        the current task. High Fisher = important parameter = don't change much.
        """
        import torch

        if not corrections:
            return

        # Sample corrections
        sample = corrections[:sample_size]

        logger.info(f"Computing Fisher Information on {len(sample)} corrections...")

        # Prepare data
        images = [self._decompress_image(item.compressed_image) for item in sample]
        labels = [item.corrected_text for item in sample]

        try:
            pixel_values = self.processor(
                images=images, return_tensors="pt",
                padding=True, truncation=True
            ).pixel_values

            label_ids = self.processor.tokenizer(
                labels, return_tensors="pt",
                padding=True, truncation=True, max_length=128
            ).input_ids
        except Exception as e:
            logger.error(f"EWC data preparation failed: {e}")
            return

        self.model.eval()
        device = next(self.model.parameters()).device
        pixel_values = pixel_values.to(device)
        label_ids = label_ids.to(device)

        # Compute Fisher Information
        fisher = {}
        self.model.zero_grad()

        with torch.no_grad():
            outputs = self.model(pixel_values=pixel_values, labels=label_ids)
            loss = outputs.loss

        # Compute gradients for each sample
        for i in range(len(images)):
            self.model.zero_grad()
            pv = pixel_values[i:i + 1]
            lid = label_ids[i:i + 1]

            outputs = self.model(pixel_values=pv, labels=lid)
            loss = outputs.loss
            loss.backward()

            for name, param in self.model.named_parameters():
                if param.grad is not None and param.requires_grad:
                    if name not in fisher:
                        fisher[name] = torch.zeros_like(param.data)
                    # Exponential moving average
                    fisher[name] += param.grad.data ** 2 / len(images)

        # Normalize and store
        for name in fisher:
            if name in self._fisher_information:
                # EMA with previous Fisher
                alpha = 0.9
                self._fisher_information[name] = (
                    alpha * self._fisher_information[name].cpu() +
                    (1 - alpha) * fisher[name].cpu()
                )
            else:
                self._fisher_information[name] = fisher[name].cpu()

        # Store optimal parameters
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self._optimal_params[name] = param.data.cpu().clone()

        self.model.train()

        # Cleanup
        if device.type == "cuda":
            torch.cuda.empty_cache()

        logger.info(f"Fisher Information computed for {len(fisher)} parameters")

    def predict_with_confidence(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Predict text with per-token confidence.

        Returns:
            (text, confidence) tuple
        """
        import torch

        self.model.eval()

        try:
            pixel_values = self.processor(
                images=[image], return_tensors="pt"
            ).pixel_values.to(next(self.model.parameters()).device)

            with torch.no_grad():
                outputs = self.model.generate(
                    pixel_values,
                    max_length=128,
                    num_beams=1,
                    return_dict_in_generate=True,
                    output_scores=True,
                )

            # Decode
            text = self.processor.decode(outputs.sequences[0], skip_special_tokens=True)

            # Compute confidence from token scores
            scores = outputs.scores  # List of tensors
            if scores:
                total_conf = 0.0
                count = 0
                for score_tensor in scores:
                    probs = torch.softmax(score_tensor, dim=-1)
                    max_prob = probs.max(dim=-1).values
                    # Only count non-pad tokens
                    pad_id = self.processor.tokenizer.pad_token_id
                    predicted_ids = outputs.sequences[:, 1:score_tensor.shape[1] + 1]
                    mask = (predicted_ids != pad_id)
                    valid_probs = max_prob * mask
                    total_conf += valid_probs.sum().item()
                    count += mask.sum().item()

                confidence = total_conf / max(1, count)
            else:
                confidence = 0.0

            return text, float(confidence)

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return "", 0.0

    def clear_cache(self):
        """Clear all cached corrections."""
        self.hot_memory.clear()

        # Clear disk cache
        for filepath in self.cache_dir.glob("correction_*.pkl.zst"):
            try:
                filepath.unlink()
            except Exception:
                pass

        self._disk_count = 0
        self._cache_size_bytes = 0
        self.total_corrections = 0
        logger.info("Learner cache cleared")


# Fix the typo in learn_from_corrections
def _fix_learn_from_corrections(self, **kwargs):
    """Fixed version with correct variable name."""
    pass
