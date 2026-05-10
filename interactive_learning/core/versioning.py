#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/versioning.py
========================================

نظام إدارة الإصدارات للنماذج والبيانات.

Provides:
- VersionManager: Semantic versioning for models and datasets
- ModelRegistry: Track model versions, metrics, and lineage
- DatasetVersioning: Version control for training datasets
"""

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SemanticVersion:
    """Semantic version representation (MAJOR.MINOR.PATCH)."""

    def __init__(self, major: int = 0, minor: int = 0, patch: int = 0):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, version_str: str) -> 'SemanticVersion':
        """Parse version string like '1.2.3'."""
        parts = version_str.strip().lstrip('v').split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"SemanticVersion({self})"

    def bump_major(self) -> 'SemanticVersion':
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> 'SemanticVersion':
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> 'SemanticVersion':
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other.lstrip('v')
        if isinstance(other, SemanticVersion):
            return (self.major, self.minor, self.patch) == \
                   (other.major, other.minor, other.patch)
        return False

    def __lt__(self, other):
        if isinstance(other, str):
            other = SemanticVersion.parse(other)
        return (self.major, self.minor, self.patch) < \
               (other.major, other.minor, other.patch)

    def __gt__(self, other):
        return not self.__eq__(other) and not self.__lt__(other)

    def to_dict(self) -> Dict[str, int]:
        return {'major': self.major, 'minor': self.minor, 'patch': self.patch}

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> 'SemanticVersion':
        return cls(d.get('major', 0), d.get('minor', 0), d.get('patch', 0))


class ModelRegistry:
    """
    سجل النماذج المدربة.

    Tracks model versions, training metrics, and model lineage.

    Usage:
        registry = ModelRegistry(Path("models/registry"))
        registry.register_model("v1.0.0", "training/outputs/best_model",
                                metrics={"cer": 0.05, "wer": 0.12})
        best = registry.get_best_model(metric="cer")
        history = registry.get_history()
    """

    def __init__(self, registry_dir: Path):
        """
        Args:
            registry_dir: Directory to store registry data
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.registry_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> List[Dict]:
        """Load registry index from disk."""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_index(self):
        """Save registry index to disk."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)

    def register_model(
        self,
        version: str,
        checkpoint_path: str,
        metrics: Optional[Dict[str, float]] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        parent_version: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> Dict:
        """
        Register a new model version.

        Args:
            version: Semantic version string
            checkpoint_path: Path to model checkpoint
            metrics: Training/evaluation metrics
            description: Human-readable description
            tags: List of tags for categorization
            parent_version: Parent model version (for fine-tuning lineage)
            config: Training configuration used

        Returns:
            Registration record
        """
        # Check if version already exists
        for entry in self._index:
            if entry['version'] == version:
                raise ValueError(f"Version {version} already registered")

        # Copy checkpoint to registry
        version_dir = self.registry_dir / f"model_{version.replace('.', '_')}"
        version_dir.mkdir(exist_ok=True)

        checkpoint_src = Path(checkpoint_path)
        if checkpoint_src.exists():
            checkpoint_dst = version_dir / "checkpoint"
            if checkpoint_src.is_dir():
                if checkpoint_dst.exists():
                    shutil.rmtree(str(checkpoint_dst))
                shutil.copytree(str(checkpoint_src), str(checkpoint_dst))
            else:
                shutil.copy2(str(checkpoint_src), str(checkpoint_dst))

        # Calculate hash of the model files
        model_hash = self._hash_directory(checkpoint_dst) if checkpoint_dst.exists() else ""

        record = {
            'version': version,
            'checkpoint_path': str(checkpoint_dst),
            'original_path': checkpoint_path,
            'metrics': metrics or {},
            'description': description,
            'tags': tags or [],
            'parent_version': parent_version,
            'config': config,
            'model_hash': model_hash,
            'registered_at': datetime.utcnow().isoformat(),
            'status': 'registered',
        }

        self._index.append(record)
        self._save_index()

        logger.info(f"Registered model version {version}")
        return record

    def get_model(self, version: str) -> Optional[Dict]:
        """Get model record by version."""
        for entry in self._index:
            if entry['version'] == version:
                return entry
        return None

    def get_best_model(
        self,
        metric: str = "cer",
        higher_is_better: bool = False
    ) -> Optional[Dict]:
        """
        Get the best model by a specific metric.

        Args:
            metric: Metric name to compare
            higher_is_better: If True, higher values are better

        Returns:
            Best model record or None
        """
        candidates = []
        for entry in self._index:
            if metric in entry.get('metrics', {}):
                candidates.append(entry)

        if not candidates:
            return None

        if higher_is_better:
            return max(candidates, key=lambda x: x['metrics'][metric])
        else:
            return min(candidates, key=lambda x: x['metrics'][metric])

    def get_latest(self) -> Optional[Dict]:
        """Get the most recently registered model."""
        if not self._index:
            return None
        return max(self._index, key=lambda x: x['registered_at'])

    def get_history(self) -> List[Dict]:
        """Get full model history sorted by version."""
        return sorted(
            self._index,
            key=lambda x: SemanticVersion.parse(x['version'])
        )

    def get_lineage(self, version: str) -> List[Dict]:
        """Get model lineage (chain of parent versions)."""
        lineage = []
        current = self.get_model(version)

        while current:
            lineage.append(current)
            parent = current.get('parent_version')
            if not parent:
                break
            current = self.get_model(parent)

        return lineage

    def list_tags(self) -> Dict[str, List[str]]:
        """List all tags and their associated versions."""
        tag_map: Dict[str, List[str]] = {}
        for entry in self._index:
            for tag in entry.get('tags', []):
                tag_map.setdefault(tag, []).append(entry['version'])
        return tag_map

    def _hash_directory(self, dir_path: Path) -> str:
        """Calculate a hash for all files in a directory."""
        hasher = hashlib.sha256()
        for file_path in sorted(dir_path.rglob('*')):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
        return hasher.hexdigest()[:16]


class DatasetVersioning:
    """
    إصدارات مجموعة البيانات.

    Tracks dataset versions with content hashing for reproducibility.

    Usage:
        ds_versioning = DatasetVersioning(Path("training/data"))
        ds_versioning.snapshot("train", "v1.0.0")
        ds_versioning.list_versions("train")
    """

    def __init__(self, data_dir: Path):
        """
        Args:
            data_dir: Root data directory
        """
        self.data_dir = Path(data_dir)
        self.versions_file = self.data_dir / "dataset_versions.json"
        self._versions = self._load_versions()

    def _load_versions(self) -> Dict[str, List[Dict]]:
        """Load version records."""
        if self.versions_file.exists():
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_versions(self):
        """Save version records."""
        with open(self.versions_file, 'w', encoding='utf-8') as f:
            json.dump(self._versions, f, indent=2, ensure_ascii=False)

    def snapshot(
        self,
        split: str,
        version: str,
        data_path: Optional[str] = None,
        description: str = "",
        num_samples: Optional[int] = None
    ) -> Dict:
        """
        Create a snapshot of a dataset split.

        Args:
            split: Dataset split name (train, val, test)
            version: Version string
            data_path: Path to data (defaults to data_dir/split)
            description: Description of changes
            num_samples: Number of samples in this version

        Returns:
            Snapshot record
        """
        if split not in self._versions:
            self._versions[split] = []

        target_path = Path(data_path) if data_path else self.data_dir / split
        content_hash = self._hash_directory(target_path) if target_path.exists() else ""

        # Count files
        file_count = 0
        total_size = 0
        if target_path.exists():
            for f in target_path.rglob('*'):
                if f.is_file():
                    file_count += 1
                    total_size += f.stat().st_size

        record = {
            'version': version,
            'split': split,
            'path': str(target_path),
            'content_hash': content_hash,
            'file_count': file_count,
            'total_size_bytes': total_size,
            'num_samples': num_samples,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
        }

        self._versions[split].append(record)
        self._save_versions()

        logger.info(f"Dataset snapshot: {split}@{version} ({file_count} files)")
        return record

    def list_versions(self, split: str) -> List[Dict]:
        """List all versions for a dataset split."""
        return self._versions.get(split, [])

    def get_latest(self, split: str) -> Optional[Dict]:
        """Get latest version of a split."""
        versions = self.list_versions(split)
        return versions[-1] if versions else None

    def has_changed(self, split: str, since_version: str) -> bool:
        """Check if dataset has changed since a version."""
        current_hash = self._hash_directory(self.data_dir / split)

        for v in reversed(self.list_versions(split)):
            if v['version'] == since_version:
                return v['content_hash'] != current_hash

        return True  # Version not found, assume changed

    def _hash_directory(self, dir_path: Path) -> str:
        """Hash all files in a directory."""
        hasher = hashlib.sha256()
        if not dir_path.exists():
            return ""
        for file_path in sorted(dir_path.rglob('*')):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
        return hasher.hexdigest()[:16]


class VersionManager:
    """
    مدير إصدارات شامل.

    Combines model registry, dataset versioning, and
    semantic version management into a single interface.

    Usage:
        vm = VersionManager(
            model_registry_dir=Path("models/registry"),
            data_dir=Path("training/data")
        )
        vm.register_model("1.0.0", "outputs/model", {"cer": 0.05})
        vm.snapshot_dataset("train", "1.0.0")
        report = vm.get_status_report()
    """

    def __init__(
        self,
        model_registry_dir: Optional[Path] = None,
        data_dir: Optional[Path] = None
    ):
        self.model_registry = ModelRegistry(
            model_registry_dir or Path("models/registry")
        )
        self.dataset_versioning = DatasetVersioning(
            data_dir or Path("training/data")
        )
        self.system_version = SemanticVersion.parse("2.0.0")

    def register_model(
        self,
        version: str,
        checkpoint_path: str,
        **kwargs
    ) -> Dict:
        """Register a new model version."""
        return self.model_registry.register_model(version, checkpoint_path, **kwargs)

    def snapshot_dataset(self, split: str, version: str, **kwargs) -> Dict:
        """Create a dataset snapshot."""
        return self.dataset_versioning.snapshot(split, version, **kwargs)

    def get_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive version status report."""
        return {
            'system_version': str(self.system_version),
            'models': {
                'total': len(self.model_registry.get_history()),
                'latest': self.model_registry.get_latest(),
                'best_by_cer': self.model_registry.get_best_model('cer'),
            },
            'datasets': {
                split: {
                    'versions': len(self.dataset_versioning.list_versions(split)),
                    'latest': self.dataset_versioning.get_latest(split),
                }
                for split in ['train', 'val', 'test']
            },
            'generated_at': datetime.utcnow().isoformat(),
        }
