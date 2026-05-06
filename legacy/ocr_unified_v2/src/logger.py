"""
HandwrittenOCR - إعداد نظام التسجيل v4.0
============================================
RotatingFileHandler + StreamHandler.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config


def setup_logging(config: Config) -> logging.Logger:
    """
    إعداد نظام التسجيل مع:
    - RotatingFileHandler (max 2MB, 5 backups)
    - StreamHandler (الشاشة)
    """
    config.ensure_dirs()

    logger = logging.getLogger("HandwrittenOCR")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # ملف سجل
    log_file = config.log_file
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # الشاشة
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger
