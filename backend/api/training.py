"""
backend/api/training.py - Training API endpoints

FastAPI/Flask endpoints for managing HTR training:
- Start/stop training jobs
- Check training status
- View training metrics
- Manage datasets
- Active learning operations
"""

import logging
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TrainingAPI:
    """
    Training API for managing HTR training operations.
    Can be integrated with FastAPI or Flask backends.
    """

    def __init__(self, config_path: str = "training/configs/trocr_lora_arabic.yaml"):
        self.config_path = config_path
        self._training_process: Optional[subprocess.Popen] = None
        self._training_lock = threading.Lock()
        self._training_status = "idle"
        self._training_logs: List[str] = []
        self._metrics_history: List[Dict] = []

    def start_training(
        self,
        config_overrides: Optional[Dict] = None,
        processed_dir: str = "training/data/processed"
    ) -> Dict[str, Any]:
        """Start a new training job."""
        with self._training_lock:
            if self._training_status == "running":
                return {
                    "status": "error",
                    "message": "Training is already running",
                    "current_status": self._training_status
                }

            if not os.path.exists(processed_dir):
                return {
                    "status": "error",
                    "message": f"Processed data not found: {processed_dir}"
                }

            cmd = [
                sys.executable,
                "training/scripts/train_trocr_lora.py",
                "--config", self.config_path,
                "--processed-dir", processed_dir
            ]

            try:
                self._training_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=Path(__file__).parent.parent.parent
                )
                self._training_status = "running"
                self._training_logs.append(
                    f"[{datetime.utcnow().isoformat()}] Training started"
                )

                threading.Thread(
                    target=self._read_training_logs,
                    daemon=True
                ).start()

                return {
                    "status": "started",
                    "pid": self._training_process.pid,
                    "config": self.config_path,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                self._training_status = "error"
                return {"status": "error", "message": str(e)}

    def stop_training(self) -> Dict[str, Any]:
        """Stop the current training job."""
        with self._training_lock:
            if self._training_process is None or self._training_status != "running":
                return {"status": "error", "message": "No training running"}

            self._training_process.terminate()
            self._training_status = "stopped"
            self._training_logs.append(
                f"[{datetime.utcnow().isoformat()}] Training stopped"
            )
            return {"status": "stopped", "timestamp": datetime.utcnow().isoformat()}

    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and recent logs."""
        if self._training_process and self._training_status == "running":
            poll = self._training_process.poll()
            if poll is not None:
                self._training_status = "completed" if poll == 0 else "failed"
                self._training_logs.append(
                    f"[{datetime.utcnow().isoformat()}] Training {self._training_status} (exit code: {poll})"
                )

        return {
            "status": self._training_status,
            "pid": self._training_process.pid if self._training_process else None,
            "config": self.config_path,
            "recent_logs": self._training_logs[-50:],
            "log_count": len(self._training_logs),
        }

    def prepare_dataset(
        self,
        raw_data_dir: str,
        output_dir: str = "training/data/processed",
        val_split: float = 0.1,
        test_split: float = 0.05
    ) -> Dict[str, Any]:
        """Prepare training dataset from raw data."""
        cmd = [
            sys.executable,
            "training/scripts/prepare_htr_dataset.py",
            "--config", self.config_path,
            "--raw-data-dir", raw_data_dir,
            "--output-dir", output_dir,
            "--val-split", str(val_split),
            "--test-split", str(test_split),
            "--create-hf"
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                cwd=Path(__file__).parent.parent.parent
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-1000:] if result.stderr else None,
                "output_dir": output_dir
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Dataset preparation timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def generate_synthetic(
        self,
        num_samples: int = 5000,
        output_dir: str = "training/data/synthetic"
    ) -> Dict[str, Any]:
        """Generate synthetic Arabic handwriting data."""
        cmd = [
            sys.executable,
            "training/scripts/generate_synthetic_data.py",
            "--config", self.config_path,
            "--output-dir", output_dir,
            "--num-samples", str(num_samples)
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                cwd=Path(__file__).parent.parent.parent
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "num_samples": num_samples,
                "output_dir": output_dir
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def evaluate_checkpoint(
        self,
        checkpoint: str,
        test_dir: str = "training/data/processed/test"
    ) -> Dict[str, Any]:
        """Evaluate a trained checkpoint."""
        cmd = [
            sys.executable,
            "training/scripts/evaluate_checkpoint.py",
            "--checkpoint", checkpoint,
            "--test-dir", test_dir,
            "--config", self.config_path
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600,
                cwd=Path(__file__).parent.parent.parent
            )
            import json
            results_file = "training/outputs/eval_results.json"
            metrics = {}
            if os.path.exists(results_file):
                with open(results_file) as f:
                    metrics = json.load(f)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "metrics": metrics,
                "checkpoint": checkpoint
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def run_active_learning(
        self,
        checkpoint: str,
        unlabeled_dir: str = "training/data/unlabeled",
        strategy: str = "hybrid"
    ) -> Dict[str, Any]:
        """Run active learning sample selection."""
        cmd = [
            sys.executable,
            "training/scripts/active_learning_pipeline.py",
            "--config", self.config_path,
            "--checkpoint", checkpoint,
            "--unlabeled-pool", unlabeled_dir
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                cwd=Path(__file__).parent.parent.parent
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "strategy": strategy,
                "checkpoint": checkpoint
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for training."""
        info = {
            "python_version": sys.version,
            "config_path": self.config_path,
            "config_exists": os.path.exists(self.config_path),
        }
        try:
            import torch
            info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_gb"] = round(
                    torch.cuda.get_device_properties(0).total_mem / 1e9, 1
                )
        except ImportError:
            info["cuda_available"] = False

        for split in ["train", "val", "test"]:
            meta = f"training/data/processed/{split}/metadata.jsonl"
            if os.path.exists(meta):
                count = sum(1 for _ in open(meta))
                info[f"{split}_samples"] = count

        checkpoints_dir = "training/outputs"
        if os.path.exists(checkpoints_dir):
            checkpoints = [
                d for d in os.listdir(checkpoints_dir)
                if os.path.isdir(os.path.join(checkpoints_dir, d))
            ]
            info["checkpoints"] = checkpoints

        return info

    def _read_training_logs(self):
        """Read training process logs in background."""
        if self._training_process and self._training_process.stdout:
            for line in iter(self._training_process.stdout.readline, b''):
                if self._training_status != "running":
                    break
                try:
                    text = line.decode('utf-8', errors='replace').strip()
                    if text:
                        self._training_logs.append(text)
                        if len(self._training_logs) > 1000:
                            self._training_logs = self._training_logs[-1000:]
                except Exception:
                    break


def setup_fastapi_routes(app, training_api: Optional[TrainingAPI] = None):
    """Add training endpoints to a FastAPI application."""
    if training_api is None:
        training_api = TrainingAPI()

    try:
        from fastapi import APIRouter
        router = APIRouter(prefix="/api/training", tags=["training"])

        @router.post("/start")
        async def start_training(config_overrides: Optional[Dict] = None):
            return training_api.start_training(config_overrides)

        @router.post("/stop")
        async def stop_training():
            return training_api.stop_training()

        @router.get("/status")
        async def get_status():
            return training_api.get_training_status()

        @router.post("/prepare-dataset")
        async def prepare_dataset(raw_data_dir: str):
            return training_api.prepare_dataset(raw_data_dir)

        @router.post("/generate-synthetic")
        async def generate_synthetic(num_samples: int = 5000):
            return training_api.generate_synthetic(num_samples)

        @router.post("/evaluate")
        async def evaluate(checkpoint: str):
            return training_api.evaluate_checkpoint(checkpoint)

        @router.post("/active-learning")
        async def active_learning(checkpoint: str):
            return training_api.run_active_learning(checkpoint)

        @router.get("/system-info")
        async def system_info():
            return training_api.get_system_info()

        app.include_router(router)
    except ImportError:
        logger.warning("FastAPI not available. Skipping route setup.")
