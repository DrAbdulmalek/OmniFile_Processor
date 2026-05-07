"""
نظام المزامنة بين الأجهزة
Multi-Device Synchronization System

المصدر: OmniFile-Previous-Versions/02-ocr-project-unified-v2/src/sync.py
الإصدار: 5.0.0 (مدمج من الأرشيف)
"""

from .sync import FileLock, SyncManager, sync_lock

__all__ = [
    "FileLock",
    "SyncManager",
    "sync_lock",
]
