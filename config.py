"""
OmniFile AI Processor v5.0 - الإعدادات المركزية
===================================================
مدمج من: OmniFile_Processor + HandwrittenOCR + handwriting-ocr
         + arabic-ocr-pro + advanced-ocr + OCR-Enhancer

يدعم:
- بيئة Google Colab + Drive
- التشغيل المحلي (Manjaro/Arch Linux)
- Docker / HuggingFace Spaces

جديد في v3.0 (دمج 6 مشاريع):
- 4 محركات OCR: TrOCR, EasyOCR, Tesseract, PaddleOCR
- دمج نتائج متعدد المحركات (4 استراتيجيات: Fusion)
- تحليل التخطيط والجداول (Layout & Table Extraction)
- معالجة RTL عربية شاملة (Arabic RTL Processing)
- معالجة النصوص المختلطة (Mixed Arabic/English/Numbers)
- قاموس عربي 186 تصحيح (Arabic Fixes Dictionary)
- تصدير متعدد الصيغات (DOCX RTL, HTML RTL, Searchable PDF)
- التعلم الذكي بالأنماط (SSIM Pattern Matching)
- تحسين بنقرة واحدة (GPT AI Corrector + Gemini Refiner)
- تقييم دقة OCR (CER/WER Metrics)
- واجهة React + shadcn/ui (Web Frontend)
- معالجة آمنة للملفات (Secure File Handler)
"""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class OmniFileConfig:
    """إعدادات المشروع المركزية - OmniFile AI Processor v4.1.1"""

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

    # === محركات OCR - تفعيل/تعطيل ===
    enable_trocr: bool = True
    enable_easyocr: bool = True
    enable_tesseract: bool = True
    enable_paddleocr: bool = False  # محرك PaddleOCR (الأفضل للعربية)
    paddleocr_lang: str = "ar"  # لغة PaddleOCR (ar, en, ar+en)

    # === خيارات الذاكرة والأداء ===
    trocr_model_variant: str = "base"  # base | small | large
    use_onnx: bool = False  # استخدام ONNX Runtime لتسريع الاستدلال
    use_quantization: bool = False  # تخفيف دقة النماذج لتقليل الذاكرة
    ocr_cache_enabled: bool = True  # تخزين مؤقت لنتائج OCR
    ocr_cache_ttl: int = 3600  # مدة صلاحية الكاش بالثواني

    # === دعم اللغات المقلص ===
    supported_languages: list = field(default_factory=lambda: ["en", "ar", "de"])

    # === Summarization ===
    enable_summarization: bool = True
    summarization_model: str = "facebook/bart-large-cnn"
    summarization_max_length: int = 130
    summarization_min_length: int = 30

    # === الأمان المتقدم ===
    enable_sensitive_scan: bool = True
    use_presidio: bool = True

    # === المعالجة غير المتزامنة ===
    enable_celery: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # === الواجهة ===
    dark_mode: bool = True
    theme_color: str = "#1E88E5"

    # === دمج النتائج (Result Fusion) ===
    fusion_strategy: str = "highest_confidence"  # highest_confidence | weighted_average | voting | longest_text

    # === معالجة RTL ===
    enable_rtl_processing: bool = True
    enable_mixed_text: bool = True

    # === التعلم الذكي ===
    enable_pattern_matching: bool = False  # SSIM Pattern Matching
    pattern_db_path: str = "patterns.db"

    # === تحسين AI ===
    enable_gemini_refiner: bool = False  # Gemini AI text refinement
    enable_gpt_corrector: bool = False  # GPT-based AI correction
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # === التصدير ===
    enable_docx_export: bool = True
    enable_html_export: bool = True
    enable_pdf_overlay: bool = True
    enable_excel_export: bool = True

    # === تقييم ===
    enable_evaluation: bool = True

    # === واجهة الويب (React Frontend) ===
    enable_frontend: bool = True
    frontend_port: int = 3000
    backend_api_port: int = 5001

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

    # === بروفايلات المحركات (اقتراح QWEN: نظام Progressive Enhancement) ===
    # المستوى 0 (low):      Tesseract فقط  — يعمل على أي جهاز
    # المستوى 1 (balanced): + EasyOCR + TrOCR — يتطلب 6GB RAM
    # المستوى 2 (high):     + PaddleOCR + ONNX — يتطلب GPU و14GB RAM
    engine_profile: str = "balanced"  # low | balanced | high

    # === تصدير/استيراد قاموس التصحيحات (اقتراح QWEN: export_corrections) ===
    corrections_export_path: str = "artifacts/correction_dict.json"
    corrections_auto_export: bool = False  # تصدير تلقائي عند كل تحديث

    # === الموجّه الذكي للمحركات (اقتراح QWEN + Claude: Engine Router) ===
    enable_engine_router: bool = True   # تفعيل الاختيار الذكي بدلاً من تشغيل كل المحركات
    router_max_engines: int = 2         # أقصى عدد محركات تُشغَّل معاً

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
    def trocr_model_name_resolved(self) -> str:
        variants = {
            "small": "microsoft/trocr-small-handwritten",
            "base": "microsoft/trocr-base-handwritten",
            "large": "microsoft/trocr-large-handwritten",
        }
        return variants.get(self.trocr_model_variant, "microsoft/trocr-base-handwritten")

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
    def from_profile(cls, profile: str = "balanced", **overrides) -> "OmniFileConfig":
        """
        إنشاء إعدادات بناءً على بروفايل الجهاز.
        اقتراح QWEN: نظام الملفات الشخصية (Profiles) للأجهزة الضعيفة/المتوسطة/القوية.

        Args:
            profile: "low" | "balanced" | "high"
            **overrides: إعدادات إضافية تطغى على القيم الافتراضية

        Returns:
            OmniFileConfig مُعَدّة للبروفايل المطلوب

        مثال:
            cfg = OmniFileConfig.from_profile("low")   # Tesseract فقط
            cfg = OmniFileConfig.from_profile("high", use_gpu=True)
        """
        PROFILES = {
            "low": {
                "engine_profile":    "low",
                "enable_trocr":      False,
                "enable_easyocr":    True,
                "enable_tesseract":  True,
                "enable_paddleocr":  False,
                "use_onnx":          True,
                "use_quantization":  True,
                "low_memory":        True,
                "trocr_batch_size":  2,
            },
            "balanced": {
                "engine_profile":    "balanced",
                "enable_trocr":      True,
                "enable_easyocr":    True,
                "enable_tesseract":  True,
                "enable_paddleocr":  False,
                "use_onnx":          False,
                "use_quantization":  False,
                "low_memory":        False,
                "trocr_batch_size":  8,
            },
            "high": {
                "engine_profile":    "high",
                "enable_trocr":      True,
                "enable_easyocr":    True,
                "enable_tesseract":  True,
                "enable_paddleocr":  True,
                "use_onnx":          False,
                "use_quantization":  False,
                "low_memory":        False,
                "trocr_batch_size":  16,
            },
        }
        base = dict(PROFILES.get(profile, PROFILES["balanced"]))
        base.update(overrides)
        return cls(**{k: v for k, v in base.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def auto_profile(ram_gb: float = 0.0, has_gpu: bool = False) -> str:
        """
        اختيار البروفايل تلقائياً بناءً على موارد الجهاز.

        Args:
            ram_gb: حجم الذاكرة المتاحة بالجيجابايت (0 = كشف تلقائي)
            has_gpu: هل يوجد GPU

        Returns:
            "low" | "balanced" | "high"
        """
        if ram_gb == 0.0:
            try:
                with open("/proc/meminfo") as f:
                    lines = f.read()
                mem_kb = int([l for l in lines.split("\n") if "MemAvailable" in l][0].split()[1])
                ram_gb = mem_kb / 1e6
            except Exception:
                ram_gb = 8.0
        if ram_gb >= 14 and has_gpu:
            return "high"
        elif ram_gb >= 6:
            return "balanced"
        else:
            return "low"

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
