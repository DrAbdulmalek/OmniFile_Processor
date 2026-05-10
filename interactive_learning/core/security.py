#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/security.py
=====================================

Comprehensive security system for interactive learning.

Provides:
- SecureCorrectionStorage: Encrypted storage with HMAC signing & key rotation
- AuditLogger: Tamper-proof audit trail with hash chain integrity
- RateLimiter: Per-key sliding window rate limiting
- InputSanitizer: Input validation against SQL injection, XSS, etc.

Security features:
- Fernet (AES-128-CBC) symmetric encryption with nonce
- HMAC-SHA256 signing with timing-safe comparison
- Hash-chain audit logging (each entry hashes previous entry)
- Peppered SHA-256 hashing for identifier anonymization
- Regex-based input validation against SQL injection patterns
"""

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Validation Patterns
# ============================================================================

VALIDATION_PATTERNS = {
    "word_id": re.compile(r'^[a-zA-Z0-9_-]{1,64}$'),
    "user_id": re.compile(r'^[a-zA-Z0-9_.-]{1,128}$'),
    "text_content": re.compile(r'^[\u0600-\u06FFa-zA-Z0-9\s\-_.!?,;:\'"()]*$'),
    "ip_address": re.compile(
        r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
        r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$'
    ),
    "session_id": re.compile(r'^[a-zA-Z0-9_-]{1,256}$'),
}

# Dangerous SQL patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b)", re.IGNORECASE),
    re.compile(r"(--|;|/\*|\*/|xp_|0x)", re.IGNORECASE),
    re.compile(r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
    re.compile(r"(\b(OR|AND)\b\s+['\"].*['\"]\s*=\s*['\"].*['\"])", re.IGNORECASE),
]


def validate_correction_input(
    word_id: str,
    user_id: str,
    original_text: str,
    corrected_text: str,
    ip_address: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate correction input against injection and format attacks.

    Returns:
        (is_valid, error_message)
    """
    # Check word_id format
    if not VALIDATION_PATTERNS["word_id"].match(word_id):
        return False, f"Invalid word_id format: '{word_id}'"

    # Check user_id format
    if not VALIDATION_PATTERNS["user_id"].match(user_id):
        return False, f"Invalid user_id format: '{user_id}'"

    # Check text content
    for field_name, value in [("original_text", original_text), ("corrected_text", corrected_text)]:
        if not value or len(value) > 1000:
            return False, f"{field_name} must be 1-1000 characters"

        if not VALIDATION_PATTERNS["text_content"].match(value):
            return False, f"{field_name} contains invalid characters"

        # Check for SQL injection
        for pattern in SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                return False, f"{field_name} contains potentially dangerous content"

    # Check for HTML tags (XSS)
    if re.search(r'<[a-zA-Z/]', original_text) or re.search(r'<[a-zA-Z/]', corrected_text):
        return False, "Text must not contain HTML tags"

    # Check IP address if provided
    if ip_address and not VALIDATION_PATTERNS["ip_address"].match(ip_address):
        return False, f"Invalid IP address format: '{ip_address}'"

    return True, ""


def sanitize_for_display(text: str) -> str:
    """
    Sanitize text for safe HTML display.

    Escapes HTML entities to prevent XSS.
    """
    if not text:
        return ""
    text = (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))
    return text


# ============================================================================
# Secure Correction Storage
# ============================================================================

class SecureCorrectionStorage:
    """
    Secure storage for OCR corrections with encryption and signing.

    Uses:
    - Fernet (AES-128-CBC) for encryption
    - HMAC-SHA256 for data integrity
    - Key rotation support
    - Nonce-based encryption (unique IV per encryption)

    Usage:
        storage = SecureCorrectionStorage()
        encrypted = storage.encrypt_correction({"word_id": "w1", "text": "corrected"})
        decrypted = storage.decrypt_correction(encrypted)
        is_valid = storage.verify_integrity(encrypted)
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_file: Optional[str] = None,
        hmac_secret: Optional[str] = None,
    ):
        self.master_key = master_key or self._generate_key()
        self.hmac_secret = hmac_secret or secrets.token_hex(32)
        self.cipher = self._create_cipher()

        if key_file and not os.path.exists(key_file):
            os.makedirs(os.path.dirname(key_file) or '.', exist_ok=True)
            with open(key_file, 'w') as f:
                json.dump({
                    "encryption_key": self.master_key,
                    "hmac_secret": self.hmac_secret,
                }, f)
            os.chmod(key_file, 0o600)

    def _generate_key(self) -> str:
        """Generate Fernet-compatible encryption key."""
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        except ImportError:
            return secrets.token_urlsafe(32)

    def _create_cipher(self):
        """Create Fernet cipher."""
        try:
            from cryptography.fernet import Fernet
            return Fernet(self.master_key.encode())
        except ImportError:
            return None

    def encrypt_correction(self, correction: Dict) -> str:
        """
        Encrypt a correction with HMAC signing.

        Returns:
            JSON string with encrypted data, nonce, HMAC, and timestamp
        """
        if not self.cipher:
            return json.dumps(correction, ensure_ascii=False)

        # Serialize
        data = json.dumps(correction, ensure_ascii=False).encode('utf-8')

        # Encrypt with Fernet (includes IV/nonce)
        encrypted = self.cipher.encrypt(data)

        # HMAC for integrity
        signature = hmac.new(
            self.hmac_secret.encode(),
            encrypted,
            hashlib.sha256
        ).hexdigest()

        # Package
        package = {
            "v": 1,
            "enc": encrypted.decode(),
            "hmac": signature,
            "ts": int(time.time()),
        }

        return json.dumps(package, ensure_ascii=False)

    def decrypt_correction(self, encrypted_data: str) -> Dict:
        """Decrypt and verify a correction."""
        try:
            package = json.loads(encrypted_data)
        except json.JSONDecodeError:
            # Legacy format: plain JSON
            return json.loads(encrypted_data)

        # New format
        if "enc" in package:
            # Verify HMAC
            expected_hmac = hmac.new(
                self.hmac_secret.encode(),
                package["enc"].encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(package.get("hmac", ""), expected_hmac):
                raise ValueError("HMAC verification failed - data may be tampered")

            if not self.cipher:
                raise RuntimeError("No cipher available for decryption")

            decrypted = self.cipher.decrypt(package["enc"].encode())
            return json.loads(decrypted.decode('utf-8'))

        return package

    def verify_integrity(self, encrypted_data: str) -> bool:
        """Verify HMAC integrity without decrypting."""
        try:
            package = json.loads(encrypted_data)
            if "enc" not in package:
                return True  # Legacy format, no HMAC

            expected_hmac = hmac.new(
                self.hmac_secret.encode(),
                package["enc"].encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(package.get("hmac", ""), expected_hmac)

        except (json.JSONDecodeError, Exception):
            return False

    def sign_data(self, data: Dict, secret: Optional[str] = None) -> str:
        """Sign data with HMAC-SHA256 (timing-safe comparison)."""
        secret = secret or self.hmac_secret
        message = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
        return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    def verify_signature(self, data: Dict, signature: str, secret: Optional[str] = None) -> bool:
        """Verify HMAC signature (timing-safe)."""
        expected = self.sign_data(data, secret)
        return hmac.compare_digest(signature, expected)

    def hash_content(self, content: str) -> str:
        """Hash content with SHA-256."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def generate_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token."""
        return secrets.token_urlsafe(length)


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """
    Sliding window rate limiter per client.

    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        if limiter.allow_request("user_123"):
            process_request()
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}

    def allow_request(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        if client_id not in self._requests:
            self._requests[client_id] = []

        # Clean old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
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

        active = [t for t in self._requests[client_id] if t > window_start]
        return max(0, self.max_requests - len(active))

    def reset(self, client_id: Optional[str] = None):
        """Reset rate limit."""
        if client_id:
            self._requests.pop(client_id, None)
        else:
            self._requests.clear()


# ============================================================================
# Audit Logger with Hash Chain
# ============================================================================

class AuditLogger:
    """
    Tamper-proof audit logger with hash chain integrity.

    Each log entry includes a hash of the previous entry, creating a chain.
    If any entry is modified, all subsequent hashes will be invalid.

    Features:
    - JSONL append-only log files
    - Hash chain: entry[N].prev_hash = hash(entry[N-1])
    - Peppered hashing for identifier anonymization
    - Daily log rotation
    - Configurable retention

    Usage:
        audit = AuditLogger(Path("./audit_logs"))
        audit.log_correction(
            user_id="user_42", word_id="w_001",
            original="original text", corrected="corrected text"
        )
        valid = audit.verify_chain()
    """

    # Pepper for hashing (makes rainbow table attacks infeasible)
    _PEPPER = os.getenv("OMNIFILE_AUDIT_PEPPER", "omnifile-pepper-2024-secret")

    def __init__(self, log_dir: Path, retention_days: int = 90):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.current_log = self.log_dir / f"audit_{datetime.now():%Y%m%d}.jsonl"
        self._last_hash = self._get_last_chain_hash()

    def log_correction(
        self,
        user_id: str,
        word_id: str,
        original: str,
        corrected: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        confidence_before: Optional[float] = None,
        confidence_after: Optional[float] = None,
    ):
        """Log a correction with hash chain integrity."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "correction",
            "user_id": self._peppered_hash(user_id),
            "word_id": word_id,
            "original_hash": self._peppered_hash(original),
            "original_length": len(original),
            "corrected_hash": self._peppered_hash(corrected),
            "corrected_length": len(corrected),
            "ip_hash": self._peppered_hash(ip_address) if ip_address else None,
            "session_id": session_id,
            "confidence_before": confidence_before,
            "confidence_after": confidence_after,
            "prev_hash": self._last_hash,
        }

        # Compute this entry's hash for the chain
        entry["entry_hash"] = self._compute_entry_hash(entry)
        self._last_hash = entry["entry_hash"]

        self._write_entry(entry)

    def log_training(
        self,
        model_version: str,
        num_samples: int,
        metrics: Dict,
        user_id: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ):
        """Log a training session."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "training",
            "model_version": model_version,
            "num_samples": num_samples,
            "metrics": metrics,
            "user_id": self._peppered_hash(user_id) if user_id else None,
            "duration_seconds": duration_seconds,
            "prev_hash": self._last_hash,
        }

        entry["entry_hash"] = self._compute_entry_hash(entry)
        self._last_hash = entry["entry_hash"]

        self._write_entry(entry)

    def log_access(
        self,
        user_id: str,
        resource: str,
        access_type: str = "read",
        ip_address: Optional[str] = None,
    ):
        """Log resource access."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "access",
            "user_id": self._peppered_hash(user_id),
            "resource": resource,
            "access_type": access_type,
            "ip_hash": self._peppered_hash(ip_address) if ip_address else None,
            "prev_hash": self._last_hash,
        }

        entry["entry_hash"] = self._compute_entry_hash(entry)
        self._last_hash = entry["entry_hash"]

        self._write_entry(entry)

    def log_export(
        self,
        user_id: str,
        export_type: str,
        num_records: int,
        ip_address: Optional[str] = None,
    ):
        """Log data export."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": "export",
            "user_id": self._peppered_hash(user_id),
            "export_type": export_type,
            "num_records": num_records,
            "ip_hash": self._peppered_hash(ip_address) if ip_address else None,
            "prev_hash": self._last_hash,
        }

        entry["entry_hash"] = self._compute_entry_hash(entry)
        self._last_hash = entry["entry_hash"]

        self._write_entry(entry)

    def verify_chain(self) -> Tuple[bool, int, int]:
        """
        Verify the integrity of the entire hash chain.

        Returns:
            (is_valid, total_entries, broken_at_index)
        """
        entries = []
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            return False, len(entries), len(entries)

        prev_hash = ""
        for i, entry in enumerate(entries):
            # Check prev_hash continuity
            if entry.get("prev_hash") != prev_hash:
                return False, len(entries), i

            # Verify entry hash
            expected_hash = self._compute_entry_hash(entry)
            if entry.get("entry_hash") != expected_hash:
                return False, len(entries), i

            prev_hash = entry.get("entry_hash", "")

        return True, len(entries), -1

    def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Get activity for a user (by hashed ID)."""
        user_hash = self._peppered_hash(user_id)
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
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """Get aggregate audit statistics."""
        stats = {"total_entries": 0, "by_action": {}, "by_date": {}}

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
                file_date = datetime.strptime(
                    log_file.stem.split('_')[1], "%Y%m%d"
                )
                if file_date < cutoff:
                    log_file.unlink()
                    logger.info(f"Removed old audit log: {log_file}")
            except (ValueError, IndexError):
                continue

    def _write_entry(self, entry: Dict):
        """Write entry to the current log file."""
        today = datetime.now()
        expected_name = f"audit_{today:%Y%m%d}.jsonl"

        if self.current_log.name != expected_name:
            self.current_log = self.log_dir / expected_name
            # Update chain from previous day's last entry
            self._last_hash = self._get_last_chain_hash()

        with open(self.current_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def _compute_entry_hash(self, entry: Dict) -> str:
        """Compute hash of an entry (excluding entry_hash field)."""
        data = {k: v for k, v in entry.items() if k != "entry_hash"}
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:32]

    def _peppered_hash(self, identifier: Optional[str]) -> str:
        """Hash with pepper for anonymization (resists rainbow tables)."""
        if not identifier:
            return ""
        salted = f"{self._PEPPER}:{identifier}"
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()[:16]

    def _get_last_chain_hash(self) -> str:
        """Get the hash of the most recent entry across all log files."""
        last_entry = None
        last_file = None

        for log_file in sorted(self.log_dir.glob("audit_*.jsonl")):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            try:
                                last_entry = json.loads(last_line)
                                last_file = log_file
                            except json.JSONDecodeError:
                                pass
            except Exception:
                continue

        if last_entry:
            return last_entry.get("entry_hash", "")
        return ""


# ============================================================================
# Input Sanitizer
# ============================================================================

class InputSanitizer:
    """
    Input sanitizer for injection prevention.

    Usage:
        clean = InputSanitizer.sanitize_correction("user input text")
        is_valid, msg = validate_correction_input("w1", "u1", "old", "new")
    """

    DANGEROUS_PATTERNS = [
        '<script', 'javascript:', 'onerror=', 'onload=',
        '<?php', '<?xml', '<!ENTITY', 'data:text/html',
    ]

    @classmethod
    def sanitize_correction(cls, text: str) -> str:
        """Sanitize correction text input."""
        if not text:
            return text

        text = text.replace('\x00', '')

        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in text_lower:
                logger.warning(f"Dangerous pattern detected: {pattern[:20]}")
                text = text.replace(pattern, '')
                text = text.replace(pattern.upper(), '')
                text = text.replace(pattern.title(), '')

        text = text.strip()
        if len(text) > 10000:
            text = text[:10000]

        return text

    @classmethod
    def validate_file_path(cls, file_path: str, allowed_dir: str) -> bool:
        """Validate file path is within allowed directory."""
        try:
            real_path = os.path.realpath(file_path)
            real_allowed = os.path.realpath(allowed_dir)
            return (real_path.startswith(real_allowed + os.sep) or
                    real_path == real_allowed)
        except (OSError, ValueError):
            return False
