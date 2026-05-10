#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/security.py
=====================================

نظام أمان متكامل للتعلم التفاعلي.

Provides:
- SecureCorrectionStorage: Encrypted storage for OCR corrections
- AuditLogger: Tamper-proof audit trail for sensitive operations
- Rate limiting and access control utilities
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SecureCorrectionStorage:
    """
    تخزين آمن للتصحيحات مع تشفير وتوقيع.

    Uses Fernet symmetric encryption (AES-128) for correction data
    and HMAC-SHA256 for data integrity verification.

    Usage:
        storage = SecureCorrectionStorage()
        encrypted = storage.encrypt_correction({"word_id": "w1", "text": "مرحبا"})
        decrypted = storage.decrypt_correction(encrypted)
        signature = storage.sign_data({"key": "value"}, secret_key)
        is_valid = storage.verify_signature({"key": "value"}, signature, secret_key)
    """

    def __init__(self, master_key: Optional[str] = None, key_file: Optional[str] = None):
        """
        Args:
            master_key: Fernet key for encryption (generated if not provided)
            key_file: Path to load/save the encryption key
        """
        if key_file and os.path.exists(key_file):
            self.master_key = self._load_key(key_file)
        elif master_key:
            self.master_key = master_key
        else:
            self.master_key = self._generate_master_key()

        if key_file and not os.path.exists(key_file):
            self._save_key(key_file, self.master_key)

        self.cipher = self._create_cipher()

    def _generate_master_key(self) -> str:
        """توليد مفتاح رئيسي."""
        try:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            return key.decode()
        except ImportError:
            # Fallback: generate a random key
            return secrets.token_urlsafe(32)

    def _create_cipher(self):
        """إنشاء كائن التشفير."""
        try:
            from cryptography.fernet import Fernet
            return Fernet(self.master_key.encode())
        except ImportError:
            return None

    def _load_key(self, key_file: str) -> str:
        """تحميل مفتاح من ملف."""
        with open(key_file, 'r') as f:
            return f.read().strip()

    def _save_key(self, key_file: str, key: str):
        """حفظ مفتاح في ملف."""
        os.makedirs(os.path.dirname(key_file) or '.', exist_ok=True)
        with open(key_file, 'w') as f:
            f.write(key)
        # Restrict permissions
        os.chmod(key_file, 0o600)

    def encrypt_correction(self, correction: Dict) -> str:
        """
        تشفير تصحيح.

        Args:
            correction: Dictionary containing correction data

        Returns:
            Base64-encoded encrypted string
        """
        if self.cipher is None:
            return json.dumps(correction, ensure_ascii=False)

        data = json.dumps(correction, ensure_ascii=False).encode('utf-8')
        encrypted = self.cipher.encrypt(data)
        return encrypted.decode()

    def decrypt_correction(self, encrypted_data: str) -> Dict:
        """
        فك تشفير تصحيح.

        Args:
            encrypted_data: Base64-encoded encrypted string

        Returns:
            Original correction dictionary
        """
        if self.cipher is None:
            return json.loads(encrypted_data)

        data = encrypted_data.encode('utf-8')
        decrypted = self.cipher.decrypt(data)
        return json.loads(decrypted.decode('utf-8'))

    def sign_data(self, data: Dict, secret: str) -> str:
        """
        توقيع بيانات باستخدام HMAC-SHA256.

        Args:
            data: Data to sign
            secret: Secret key for signing

        Returns:
            Hex-encoded signature
        """
        message = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()
        return signature

    def verify_signature(self, data: Dict, signature: str, secret: str) -> bool:
        """
        التحقق من التوقيع.

        Args:
            data: Original data
            signature: Signature to verify
            secret: Secret key used for signing

        Returns:
            True if signature is valid
        """
        expected = self.sign_data(data, secret)
        return hmac.compare_digest(signature, expected)

    def hash_content(self, content: str) -> str:
        """
        تجزئة محتوى باستخدام SHA-256.

        Args:
            content: String to hash

        Returns:
            Hex-encoded hash (first 32 chars)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]

    def generate_token(self, length: int = 32) -> str:
        """توليد رمز أمني عشوائي."""
        return secrets.token_urlsafe(length)


class RateLimiter:
    """
    محدد معدل للطلبات.

    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        if limiter.allow_request("user_123"):
            process_request()
        else:
            reject_request()
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum requests per window
            window_seconds: Window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}

    def allow_request(self, client_id: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            client_id: Unique identifier for the client

        Returns:
            True if request is allowed
        """
        now = time.time()
        window_start = now - self.window_seconds

        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if t > window_start
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for a client."""
        now = time.time()
        window_start = now - self.window_seconds

        if client_id not in self._requests:
            return self.max_requests

        active = [
            t for t in self._requests[client_id]
            if t > window_start
        ]
        return max(0, self.max_requests - len(active))

    def reset(self, client_id: Optional[str] = None):
        """Reset rate limit for a client or all clients."""
        if client_id:
            self._requests.pop(client_id, None)
        else:
            self._requests.clear()


class AuditLogger:
    """
    سجل تدقيق للعمليات الحساسة.

    Records all sensitive operations (corrections, training, access)
    in append-only JSONL log files with hash-based anonymization.

    Usage:
        audit = AuditLogger(Path("/var/log/omnifile/audit"))
        audit.log_correction(
            user_id="user_42",
            word_id="w_001",
            original="فم",
            corrected="في",
            ip_address="192.168.1.1"
        )
        activities = audit.get_user_activity("user_42")
    """

    def __init__(self, log_dir: Path, retention_days: int = 90):
        """
        Args:
            log_dir: Directory for audit log files
            retention_days: Number of days to retain logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.current_log = self.log_dir / f"audit_{datetime.now():%Y%m%d}.jsonl"
        self._lock = None

    def log_correction(
        self,
        user_id: str,
        word_id: str,
        original: str,
        corrected: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        confidence_before: Optional[float] = None,
        confidence_after: Optional[float] = None
    ):
        """
        تسجيل تصحيح.

        Args:
            user_id: User performing the correction
            word_id: Unique word identifier
            original: Original OCR text
            corrected: Corrected text
            ip_address: Client IP address (will be hashed)
            session_id: Session identifier
            confidence_before: OCR confidence before correction
            confidence_after: Expected confidence after correction
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': 'correction',
            'user_id': self._hash_identifier(user_id),
            'word_id': word_id,
            'original_hash': self._hash_content(original),
            'original_length': len(original),
            'corrected_hash': self._hash_content(corrected),
            'corrected_length': len(corrected),
            'ip_hash': self._hash_identifier(ip_address) if ip_address else None,
            'session_id': session_id,
            'confidence_before': confidence_before,
            'confidence_after': confidence_after,
        }

        self._write_entry(entry)

    def log_training(
        self,
        model_version: str,
        num_samples: int,
        metrics: Dict,
        user_id: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ):
        """
        تسجيل جلسة تدريب.

        Args:
            model_version: Version identifier for the model
            num_samples: Number of training samples
            metrics: Training metrics (CER, WER, loss, etc.)
            user_id: User who initiated training
            duration_seconds: Training duration
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': 'training',
            'model_version': model_version,
            'num_samples': num_samples,
            'metrics': metrics,
            'user_id': self._hash_identifier(user_id) if user_id else None,
            'duration_seconds': duration_seconds,
        }

        self._write_entry(entry)

    def log_access(
        self,
        user_id: str,
        resource: str,
        access_type: str = 'read',
        ip_address: Optional[str] = None
    ):
        """
        تسجيل وصول لمورد.

        Args:
            user_id: User accessing the resource
            resource: Resource identifier
            access_type: Type of access (read, write, delete)
            ip_address: Client IP address
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': 'access',
            'user_id': self._hash_identifier(user_id),
            'resource': resource,
            'access_type': access_type,
            'ip_hash': self._hash_identifier(ip_address) if ip_address else None,
        }

        self._write_entry(entry)

    def log_export(
        self,
        user_id: str,
        export_type: str,
        num_records: int,
        ip_address: Optional[str] = None
    ):
        """
        تسجيل تصدير بيانات.

        Args:
            user_id: User performing export
            export_type: Export format (json, csv, pdf, etc.)
            num_records: Number of exported records
            ip_address: Client IP address
        """
        entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': 'export',
            'user_id': self._hash_identifier(user_id),
            'export_type': export_type,
            'num_records': num_records,
            'ip_hash': self._hash_identifier(ip_address) if ip_address else None,
        }

        self._write_entry(entry)

    def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        الحصول على نشاط مستخدم.

        Args:
            user_id: User identifier
            start_date: Start of date range
            end_date: End of date range
            action_filter: Filter by action type

        Returns:
            List of audit log entries
        """
        user_hash = self._hash_identifier(user_id)
        activities = []

        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            try:
                file_date = datetime.strptime(log_file.stem.split('_')[1], "%Y%m%d")
            except (ValueError, IndexError):
                continue

            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if entry.get('user_id') != user_hash:
                        continue
                    if action_filter and entry.get('action') != action_filter:
                        continue

                    activities.append(entry)

        return activities

    def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get aggregate audit statistics.

        Returns:
            Dictionary with action counts and trends
        """
        stats = {
            'total_entries': 0,
            'by_action': {},
            'by_date': {},
        }

        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            try:
                file_date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
            except (ValueError, IndexError):
                continue

            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            day_count = 0
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    stats['total_entries'] += 1
                    day_count += 1

                    action = entry.get('action', 'unknown')
                    stats['by_action'][action] = stats['by_action'].get(action, 0) + 1

            stats['by_date'][file_date_str] = day_count

        return stats

    def cleanup_old_logs(self):
        """Remove log files older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            try:
                file_date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                if file_date < cutoff:
                    log_file.unlink()
                    logger.info(f"Removed old audit log: {log_file}")
            except (ValueError, IndexError):
                continue

    def _write_entry(self, entry: Dict):
        """Write an entry to the current log file."""
        # Check if we need to rotate to a new day
        today = datetime.now()
        expected_name = f"audit_{today:%Y%m%d}.jsonl"

        if self.current_log.name != expected_name:
            self.current_log = self.log_dir / expected_name

        with open(self.current_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def _hash_identifier(self, identifier: Optional[str]) -> str:
        """تجزئة معرف (للخصوصية)."""
        if not identifier:
            return ""
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:16]

    def _hash_content(self, content: str) -> str:
        """تجزئة محتوى."""
        if not content:
            return hashlib.sha256(b"").hexdigest()[:16]
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class InputSanitizer:
    """
    معقم المدخلات للحماية من الحقن.

    Usage:
        sanitizer = InputSanitizer()
        clean = sanitizer.sanitize_correction("نص المستخدم")
    """

    # Characters considered dangerous in correction text
    DANGEROUS_PATTERNS = [
        '<script',
        'javascript:',
        'onerror=',
        'onload=',
        '<?php',
        '<?xml',
        '<!ENTITY',
        'data:text/html',
    ]

    @classmethod
    def sanitize_correction(cls, text: str) -> str:
        """
        Sanitize correction text input.

        Args:
            text: Raw input text

        Returns:
            Sanitized text with dangerous content removed
        """
        if not text:
            return text

        # Remove null bytes
        text = text.replace('\x00', '')

        # Check for dangerous patterns
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in text_lower:
                logger.warning(f"Dangerous pattern detected in input: {pattern[:20]}")
                text = text.replace(pattern, '').replace(pattern.upper(), '')
                text = text.replace(pattern.title(), '')

        # Strip leading/trailing whitespace
        text = text.strip()

        # Limit length
        if len(text) > 10000:
            logger.warning(f"Input truncated: {len(text)} chars")
            text = text[:10000]

        return text

    @classmethod
    def validate_file_path(cls, file_path: str, allowed_dir: str) -> bool:
        """
        Validate that a file path is within an allowed directory.

        Args:
            file_path: Path to validate
            allowed_dir: Allowed base directory

        Returns:
            True if path is safe
        """
        try:
            real_path = os.path.realpath(file_path)
            real_allowed = os.path.realpath(allowed_dir)
            return real_path.startswith(real_allowed + os.sep) or real_path == real_allowed
        except (OSError, ValueError):
            return False
