"""
HandwrittenOCR - إعدادات المشروع v5.0
==========================================
ملف الإعدادات المركزي - يدعم:
- التخزين المؤقت للنماذج على Drive/القرص
- Batch TrOCR + Beam Search
- Active Learning + Auto Export
- WER/CER Metrics + Backup
- التشغيل المحلي (Offline) + المزامنة (Syncthing)
- قفل الملفات لمنع التعارضات بين الأجهزة
"""

import os
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """إعدادات المشروع الرئيسية — v4.0 Ultimate"""

    # --- المسارات ---
    project_root: str = str(Path.home() / "Handwritten_OCR_Ultimate")
    pdf_path: str = "input.pdf"
    output_dir: str = ""
    db_name: str = "handwriting_data.db"

    # --- النماذج ---
    trocr_model_name: str = "David-Magdy/TR_OCR_LARGE"
    hf_token: str = ""
    hf_dataset_repo: str = ""
    ocr_languages: list = field(default_factory=lambda: ["en", "ar"])

    # --- الأداء ---
    dpi: int = 300
    use_gpu: bool = True
    trocr_batch_size: int = 16       # ← batching لـ 3-6x تسريع
    num_beams: int = 5              # ← beam search لدقة أعلى (مُحدَّث من 4 إلى 5)
    low_memory: bool = False        # ← وضع خفيف: يقلل DPI ويزيل EasyOCR العربي
    skip_trocr: bool = False         # ← تخطي TrOCR بالكامل: EasyOCR فقط (يوفّر ~600 MB)
    skip_spellcheck: bool = False    # ← تخطي المدققات الإملائية (يوفّر ~200 MB)
    max_text_length: int = 64
    easy_conf_threshold: float = 0.80  # ← تخطي TrOCR لو EasyOCR واثق
    trocr_default_confidence: float = 0.70
    low_conf_threshold: float = 0.50
    model_cache_dir: str = ""
    easyocr_persistent: bool = False

    # --- Preprocessing ---
    clahe_clip: float = 2.0
    clahe_tile: tuple = (8, 8)
    denoise_h: int = 20
    enable_deskew: bool = True
    min_word_w: int = 15
    min_word_h: int = 10
    dilation_kernel: tuple = (25, 5)

    # --- التصحيح ---
    correction_min_votes: int = 1   # ← خُفض من 2 إلى 1

    # --- الصفحات ---
    pages_start: int = 1
    pages_end: int = 5

    # --- التدريب ---
    finetune_min_samples: int = 50
    finetune_epochs: int = 5
    finetune_batch_size: int = 4
    finetune_lr: float = 1e-5       # ← خُفض من 5e-5
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: list = field(default_factory=lambda: ["query", "value"])

    # --- Active Learning ---
    al_min_new_corrections: int = 50    # تشغيل تلقائي بعد N تصحيح
    al_reprocess_low_conf_limit: int = 100

    # --- التصدير ---
    export_val_ratio: float = 0.1
    auto_export_after_run: bool = True

    # --- Gradio ---
    gradio_share: bool = True
    gradio_port: int = 7860

    # --- المزامنة ---
    sync_enabled: bool = False          # تفعيل نظام المزامنة
    sync_lock_timeout: int = 30        # مهلة القفل بالثواني
    sync_status_file: str = "sync_status.json"
    server_host: str = "127.0.0.1"     # عنوان الاستماع (0.0.0.0 للشبكة المحلية)

    # --- Logging ---
    log_level: str = "INFO"

    # === Properties ===

    @property
    def root(self) -> Path:
        base = self.output_dir or self.project_root
        return Path(base)

    @property
    def db_path(self) -> str:
        return str(self.root / "database" / self.db_name)

    @property
    def logs_dir(self) -> str:
        return str(self.root / "logs")

    @property
    def log_file(self) -> str:
        from datetime import datetime
        return os.path.join(
            self.logs_dir,
            f"ocr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

    @property
    def exports_dir(self) -> str:
        return str(self.root / "exports")

    @property
    def cache_dir(self) -> str:
        return str(self.root / "models_cache")

    @property
    def artifacts_dir(self) -> str:
        return str(self.root / "artifacts")

    @property
    def backups_dir(self) -> str:
        return str(self.root / "backups")

    @property
    def tensorboard_dir(self) -> str:
        return str(self.root / "runs")

    @property
    def feedback_csv(self) -> str:
        return os.path.join(self.logs_dir, "user_corrections_feedback.csv")

    @property
    def stats_json(self) -> str:
        return os.path.join(self.logs_dir, "processing_stats.json")

    @property
    def correction_dict_path(self) -> str:
        return os.path.join(self.artifacts_dir, "correction_dict.json")

    @property
    def checkpoint_file(self) -> str:
        return os.path.join(self.artifacts_dir, "ocr_checkpoint.json")

    @property
    def metrics_log(self) -> str:
        return os.path.join(self.logs_dir, "metrics_history.csv")

    @property
    def runs_csv(self) -> str:
        return os.path.join(self.logs_dir, "runs_history.csv")

    @property
    def events_jsonl(self) -> str:
        return os.path.join(self.logs_dir, "ocr_events.jsonl")

    @property
    def easyocr_drive_path(self) -> str:
        return os.path.join(str(self.root), ".EasyOCR")

    @property
    def easyocr_local_path(self) -> str:
        return str(Path.home() / ".EasyOCR")

    @property
    def export_dir(self) -> str:
        return os.path.join(self.exports_dir, "hf_training_dataset")

    @property
    def lora_save_path(self) -> str:
        cache = self.model_cache_dir or self.cache_dir
        return os.path.join(cache or str(self.root), "trocr_lora_finetuned")

    @property
    def sync_status_path(self) -> str:
        return os.path.join(self.root, self.sync_status_file)

    @property
    def lock_file_path(self) -> str:
        return os.path.join(self.artifacts_dir, "processing.lock")

    @property
    def input_pdfs_dir(self) -> str:
        return str(self.root / "input_pdfs")

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
        for d in [
            self.root / "database",
            Path(self.logs_dir),
            Path(self.exports_dir),
            Path(self.cache_dir) if self.cache_dir else None,
            Path(self.artifacts_dir),
            Path(self.backups_dir),
            Path(self.tensorboard_dir),
            Path(self.input_pdfs_dir),
        ]:
            if d is not None:
                d.mkdir(parents=True, exist_ok=True)
        if self.model_cache_dir:
            os.makedirs(self.model_cache_dir, exist_ok=True)

    def setup(self) -> None:
        """إعداد شامل: مجلدات + متغيرات بيئة + ملفات CSV"""
        self.ensure_dirs()
        if self.hf_token:
            os.environ["HF_TOKEN"] = self.hf_token
            os.environ["HUGGING_FACE_HUB_TOKEN"] = self.hf_token
        if self.cache_dir:
            os.environ["TRANSFORMERS_CACHE"] = self.cache_dir
            os.environ["TORCH_HOME"] = self.cache_dir
            os.environ["HF_HOME"] = self.cache_dir

        # إنشاء ملفات CSV إذا لم تكن موجودة
        import pandas as pd
        for csv_path, cols in [
            (self.feedback_csv, ["timestamp", "image_id", "original_text", "corrected_text", "status"]),
            (self.runs_csv, ["run_id", "timestamp", "pages", "words", "avg_conf", "duration_sec", "status"]),
        ]:
            if not os.path.exists(csv_path):
                pd.DataFrame(columns=cols).to_csv(csv_path, index=False, encoding="utf-8-sig")

    def apply_hf_token(self) -> None:
        if self.hf_token:
            os.environ["HF_TOKEN"] = self.hf_token
            os.environ["HUGGING_FACE_HUB_TOKEN"] = self.hf_token

    def apply_cache_env(self) -> None:
        cache = self.model_cache_dir or self.cache_dir
        if cache:
            os.makedirs(cache, exist_ok=True)
            os.environ["TRANSFORMERS_CACHE"] = cache
            os.environ["TORCH_HOME"] = cache
            os.environ["HF_HOME"] = cache

    def setup_easyocr_symlink(self) -> None:
        """ربط نماذج EasyOCR بـ Drive (Colab فقط) — بدون استخدام !ln"""
        if not self.easyocr_persistent:
            return
        import shutil
        drive_path = self.easyocr_drive_path
        local_path = self.easyocr_local_path
        if not os.path.exists(drive_path):
            os.makedirs(drive_path, exist_ok=True)
        if os.path.exists(local_path) and not os.path.islink(local_path) and not os.path.exists(drive_path):
            shutil.move(local_path, drive_path)
        if not os.path.exists(local_path):
            try:
                os.symlink(drive_path, local_path)
            except Exception:
                pass

    @classmethod
    def from_colab_drive(
        cls,
        pdf_name: str = "python notes.pdf",
        hf_token: str = "",
        hf_repo: str = "",
    ) -> "Config":
        """إنشاء إعدادات لبيئة Google Colab"""
        base = "/content/drive/MyDrive"
        return cls(
            project_root=f"{base}/Handwritten_OCR_Ultimate",
            output_dir=f"{base}/Handwritten_OCR_Ultimate",
            pdf_path=f"{base}/{pdf_name}",
            model_cache_dir=f"{base}/Handwritten_OCR_Ultimate/models_cache",
            hf_token=hf_token,
            hf_dataset_repo=hf_repo,
            easyocr_persistent=True,
            gradio_share=True,
        )

    def apply_low_memory(self) -> None:
        """تفعيل الوضع الخفيف — تقليل استهلاك الذاكرة لأجهزة RAM محدودة.

        يُنفَّذ تلقائياً عند تمرير --low-memory من سطر الأوامر.

        التغييرات:
        - DPI: 300 → 150 (يوفّر 75% من ذاكرة الصور)
        - EasyOCR: [en, ar] → [en] (يوفّر ~800 MB من نموذج العربية)
        - batch_size: 16 → 4 (يقلل الذاكرة المؤقتة)
        - deskew: معطّل (يوفّر ذاكرة warpAffine)
        - denoise_h: 20 → 10 (تقليل سلاسة الضوضاء)
        """
        if self.low_memory:
            self.dpi = 150
            self.ocr_languages = ["en"]
            self.trocr_batch_size = 4
            self.enable_deskew = False
            self.denoise_h = 10
            self.max_text_length = 48
            self.skip_trocr = True  # تلقائي: تخطي TrOCR في الوضع الخفيف
            self.skip_spellcheck = True  # تلقائي: تخطي المدققات الإملائية
            logger = logging.getLogger("HandwrittenOCR")
            logger.info("الوضع الخفيف مفعّل: DPI=150, EasyOCR=[en], batch=4, deskew=off, TrOCR=off, SpellCheck=off")

    @classmethod
    def from_local(cls, pdf_path: str = "", project_root: str = "") -> "Config":
        """
        إنشاء إعدادات للتشغيل المحلي (Offline).
        يكتشف تلقائياً: GPU، مسار المشروع، بيئة التشغيل.

        الاستخدام:
            CFG = Config.from_local()
            CFG = Config.from_local(pdf_path="~/documents/notes.pdf")
        """
        import torch

        # تحديد مسار المشروع تلقائياً
        if not project_root:
            candidate = Path(__file__).parent.resolve()
            if (candidate / "database").exists():
                project_root = str(candidate)
            else:
                project_root = str(Path.home() / "Handwritten_OCR_Ultimate")

        base = Path(project_root)
        pdf = pdf_path or str(base / "input.pdf")

        return cls(
            project_root=project_root,
            pdf_path=pdf,
            use_gpu=torch.cuda.is_available(),
            gradio_share=False,
            sync_enabled=True,
            server_host="0.0.0.0",
            model_cache_dir=str(base / "models_cache"),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """إنشاء إعدادات من قاموس"""
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)
