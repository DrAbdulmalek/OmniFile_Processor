"""
وحدة تشفير الملفات (File Encryption Module)
==============================================
تشفير وفك تشفير الملفات الحساسة باستخدام Fernet (AES-128).
يدعم تشفير الملفات الفردية والمجلدات بالكامل.
"""

import os
import base64
import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileEncryptor:
    """مشفر الملفات باستخدام Fernet (AES-128-CBC)."""

    def __init__(self, key: Optional[str] = None, key_file: Optional[str] = None):
        """
        تهيئة مشفر الملفات.

        Args:
            key: مفتاح التشفير (Base64 encoded) أو None لتوليد واحد
            key_file: مسار ملف لحفظ/تحميل المفتاح
        """
        self._key = None
        self._cipher = None

        if key:
            self._init_from_key(key)
        elif key_file and os.path.exists(key_file):
            self._load_key_from_file(key_file)
        else:
            self._generate_key()

        if key_file and not os.path.exists(key_file):
            self._save_key_to_file(key_file)

    def _init_from_key(self, key: str) -> None:
        """تهيئة من مفتاح."""
        try:
            from cryptography.fernet import Fernet
            if not key.startswith("gAAAAA"):
                # ربما كلمة مرور - تحويلها لمفتاح
                key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode()
            self._key = key.encode() if isinstance(key, str) else key
            self._cipher = Fernet(self._key)
            logger.info("تم تهيئة مشفر الملفات من مفتاح")
        except ImportError:
            logger.error("مكتبة cryptography غير مثبتة. pip install cryptography")
        except Exception as e:
            logger.error("فشل تهيئة التشفير: %s", e)

    def _generate_key(self) -> None:
        """توليد مفتاح تشفير عشوائي."""
        try:
            from cryptography.fernet import Fernet
            self._key = Fernet.generate_key()
            self._cipher = Fernet(self._key)
            logger.info("تم توليد مفتاح تشفير جديد")
        except ImportError:
            logger.error("مكتبة cryptography غير مثبتة")

    def _load_key_from_file(self, path: str) -> None:
        """تحميل المفتاح من ملف."""
        try:
            with open(path, "r") as f:
                key = f.read().strip()
            self._init_from_key(key)
            logger.info("تم تحميل مفتاح التشفير من %s", path)
        except Exception as e:
            logger.warning("فشل تحميل المفتاح: %s", e)
            self._generate_key()

    def _save_key_to_file(self, path: str) -> None:
        """حفظ المفتاح في ملف."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(self._key.decode() if isinstance(self._key, bytes) else self._key)
            os.chmod(path, 0o600)
            logger.info("تم حفظ مفتاح التشفير في %s", path)
        except Exception as e:
            logger.warning("فشل حفظ المفتاح: %s", e)

    @property
    def is_available(self) -> bool:
        """هل التشفير متاح؟"""
        return self._cipher is not None

    @property
    def key(self) -> Optional[str]:
        """المفتاح الحالي (Base64)."""
        return self._key.decode() if isinstance(self._key, bytes) else self._key

    def encrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        تشفير ملف.

        Args:
            input_path: مسار الملف المراد تشفيره
            output_path: مسار الملف المشفر (الافتراضي: نفس المسار + .enc)

        Returns:
            مسار الملف المشفر
        """
        if not self._cipher:
            raise RuntimeError("التشفير غير متاح - تأكد من تثبيت cryptography")

        input_path = str(input_path)
        output_path = output_path or input_path + ".enc"

        with open(input_path, "rb") as f:
            data = f.read()

        encrypted = self._cipher.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted)

        logger.info("تم تشفير %s (%d bytes -> %d bytes)", input_path, len(data), len(encrypted))
        return output_path

    def decrypt_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        فك تشفير ملف.

        Args:
            input_path: مسار الملف المشفر
            output_path: مسار الملف بعد فك التشفير (الافتراضي: إزالة .enc)

        Returns:
            مسار الملف المفكوك
        """
        if not self._cipher:
            raise RuntimeError("التشفير غير متاح")

        input_path = str(input_path)
        if output_path is None:
            output_path = input_path.removesuffix(".enc") if input_path.endswith(".enc") else input_path + ".dec"

        with open(input_path, "rb") as f:
            encrypted = f.read()

        decrypted = self._cipher.decrypt(encrypted)

        with open(output_path, "wb") as f:
            f.write(decrypted)

        logger.info("تم فك تشفير %s (%d bytes -> %d bytes)", input_path, len(encrypted), len(decrypted))
        return output_path

    def encrypt_data(self, data: bytes) -> bytes:
        """تشفير بيانات خام."""
        if not self._cipher:
            raise RuntimeError("التشفير غير متاح")
        return self._cipher.encrypt(data)

    def decrypt_data(self, data: bytes) -> bytes:
        """فك تشفير بيانات خام."""
        if not self._cipher:
            raise RuntimeError("التشفير غير متاح")
        return self._cipher.decrypt(data)

    def encrypt_directory(self, input_dir: str, output_dir: Optional[str] = None, pattern: str = "*") -> list[str]:
        """
        تشفير جميع الملفات في مجلد.

        Args:
            input_dir: مسار المجلد
            output_dir: مسار الإخراج (الافتراضي: مجلد مشفر جديد)
            pattern: نمط أسماء الملفات (glob)

        Returns:
            قائمة مسارات الملفات المشفرة
        """
        import glob

        input_dir = Path(input_dir)
        output_dir = Path(output_dir) if output_dir else input_dir.parent / (input_dir.name + "_encrypted")
        output_dir.mkdir(parents=True, exist_ok=True)

        encrypted_files = []
        for file_path in sorted(input_dir.glob(pattern)):
            if file_path.is_file():
                out = str(output_dir / (file_path.name + ".enc"))
                self.encrypt_file(str(file_path), out)
                encrypted_files.append(out)

        logger.info("تم تشفير %d ملف من %s", len(encrypted_files), input_dir)
        return encrypted_files

    def decrypt_directory(self, input_dir: str, output_dir: Optional[str] = None) -> list[str]:
        """
        فك تشفير جميع الملفات .enc في مجلد.

        Args:
            input_dir: مسار المجلد المشفر
            output_dir: مسار الإخراج

        Returns:
            قائمة مسارات الملفات المفكوكة
        """
        import glob

        input_dir = Path(input_dir)
        output_dir = Path(output_dir) if output_dir else input_dir.parent / (input_dir.name + "_decrypted")
        output_dir.mkdir(parents=True, exist_ok=True)

        decrypted_files = []
        for file_path in sorted(input_dir.glob("*.enc")):
            out = str(output_dir / file_path.name.removesuffix(".enc"))
            self.decrypt_file(str(file_path), out)
            decrypted_files.append(out)

        logger.info("تم فك تشفير %d ملف من %s", len(decrypted_files), input_dir)
        return decrypted_files


# === Module-level convenience functions for OmniFile_v500_Colab ===
_default_encryptor = FileEncryptor()

def encrypt_file(input_path: str, output_path: str = None) -> str:
    """تشفير ملف — واجهة مستوى الوحدة."""
    return _default_encryptor.encrypt_file(input_path, output_path)

def decrypt_file(input_path: str, output_path: str = None) -> str:
    """فك تشفير ملف — واجهة مستوى الوحدة."""
    return _default_encryptor.decrypt_file(input_path, output_path)
