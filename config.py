"""
OmniFile AI Processor v2.0 - الإعدادات المركزية
==================================================
مدمج من: OmniFile_Processor + HandwrittenOCR + handwriting-ocr

يدعم:
- بيئة Google Colab + Drive
- التشغيل المحلي (Manjaro/Arch Linux)
- Docker / HuggingFace Spaces
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class OmniFileConfig:
    """إعدادات المشروع المركزية - OmniFile AI Processor v2.0"""

    # === المسارات الأساسية ===
    project_root: str = ""
    environment: str = "colab"  # colab | local | docker

    # === وحدة الرؤية الحاسوبية (CV & OCR) ===
    trocr_model_name: str = "microsoft/trocr-base-handwritten"
    easyocr_languages: list = field(default_factory=lambda: ["en", "ar"])
    tesseract_langs: str = "eng+ara"
    dpi: int = 300
    trocr_batch_size: int = 8
    num_beams: int = 4
    use_gpu: bool = True
    easy_conf_threshold: float = 0.80
    low_memory: bool = False

    # === وحدة المعالجة النصية (NLP) ===
    translation_model: str = "Helsinki-NLP/opus-mt-en-ar"
    ner_model: str = "aubmindlab/bert-base-arabertv02-ner"
    text_classifier_model: str = "aubmindlab/bert-base-arabertv2"
    max_text_length: int = 512
    enable_translation: bool = True
    enable_ner: bool = True
    enable_classification: bool = True

    # === وحدة الحماية والأمان ===
    protect_python_keywords: bool = True
    protect_code_blocks: bool = True
    allowed_extensions: list = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".md",
        ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".json", ".csv",
        ".xlsx", ".docx", ".pptx", ".zip", ".tar.gz", ".ipynb"
    ])
    blocked_patterns: list = field(default_factory=lambda: [
        "password", "secret", "api_key", "token", "credential"
    ])

    # === HuggingFace ===
    hf_token: str = ""
    hf_username: str = "DrAbdulmalek"
    hf_dataset_repo: str = ""
    hf_model_repo: str = ""

    # === GitHub ===
    github_token: str = ""
    github_repo: str = "DrAbdulmalek/OmniFile_Processor"
    github_username: str = ""
    github_email: str = ""

    # === قاعدة البيانات ===
    db_name: str = "omnifile_data.db"

    # === المزامنة ===
    sync_enabled: bool = True
    auto_save_interval: int = 300  # ثانية

    # === واجهة المستخدم ===
    ui_port: int = 8501
    api_port: int = 8000
    share_public: bool = True

    # === التدريب (Fine-tuning) ===
    finetune_epochs: int = 3
    finetune_batch_size: int = 4
    finetune_lr: float = 1e-4
    lora_r: int = 8
    lora_alpha: int = 16

    # === Properties ===

    @property
    def root(self) -> Path:
        return Path(self.project_root) if self.project_root else Path.cwd()

    @property
    def db_path(self) -> str:
        return str(self.root / "database" / self.db_name)

    @property
    def data_raw_dir(self) -> str:
        return str(self.root / "data" / "raw")

    @property
    def data_processed_dir(self) -> str:
        return str(self.root / "data" / "processed")

    @property
    def exports_dir(self) -> str:
        return str(self.root / "data" / "exports")

    @property
    def models_cache_dir(self) -> str:
        return str(self.root / "models_cache")

    @property
    def logs_dir(self) -> str:
        return str(self.root / "logs")

    @property
    def input_pdfs_dir(self) -> str:
        return str(self.root / "data" / "raw" / "pdfs")

    @property
    def is_colab(self) -> bool:
        """كشف بيئة Google Colab تلقائياً"""
        try:
            import google.colab
            return True
        except Exception:
            return False

    def ensure_dirs(self) -> None:
        """إنشاء جميع المجلدات المطلوبة"""
        dirs = [
            self.root / "database",
            self.root / "data" / "raw" / "pdfs",
            self.root / "data" / "raw" / "images",
            self.root / "data" / "raw" / "archives",
            self.root / "data" / "processed",
            self.root / "data" / "exports",
            self.root / "models_cache",
            self.root / "logs",
            self.root / "backups",
            self.root / "notebooks",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def setup_environment(self) -> None:
        """إعداد البيئة الكامل: مجلدات + متغيرات + ملفات"""
        self.ensure_dirs()

        # إعداد HuggingFace
        if self.hf_token:
            os.environ["HF_TOKEN"] = self.hf_token
            os.environ["HUGGING_FACE_HUB_TOKEN"] = self.hf_token

        # إعداد مسار التخزين المؤقت
        cache = self.models_cache_dir
        if cache:
            os.makedirs(cache, exist_ok=True)
            os.environ["TRANSFORMERS_CACHE"] = cache
            os.environ["TORCH_HOME"] = cache
            os.environ["HF_HOME"] = cache

        # إعداد Git
        if self.github_username and self.github_email:
            os.system(f'git config --global user.name "{self.github_username}"')
            os.system(f'git config --global user.email "{self.github_email}"')
            os.system('git config --global init.defaultBranch main')

    def save(self, path: Optional[str] = None) -> None:
        """حفظ الإعدادات كملف JSON"""
        save_path = path or str(self.root / "config" / "settings.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "OmniFileConfig":
        """تحميل الإعدادات من ملف JSON"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_colab_drive(cls, **overrides) -> "OmniFileConfig":
        """إنشاء إعدادات لبيئة Google Colab + Drive"""
        base = "/content/drive/MyDrive/OmniFile_AI"
        defaults = dict(
            project_root=base,
            environment="colab",
            use_gpu=True,
            share_public=True,
            models_cache_dir=os.path.join(base, "models_cache"),
        )
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def from_local(cls, project_root: str = "", **overrides) -> "OmniFileConfig":
        """إنشاء إعدادات للتشغيل المحلي"""
        import torch
        if not project_root:
            project_root = str(Path.home() / "OmniFile_AI")
        defaults = dict(
            project_root=project_root,
            environment="local",
            use_gpu=torch.cuda.is_available(),
            share_public=False,
            models_cache_dir=os.path.join(project_root, "models_cache"),
        )
        defaults.update(overrides)
        return cls(**defaults)
