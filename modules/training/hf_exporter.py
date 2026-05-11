# ══════════════════════════════════════════════════════════╗
#  HuggingFace Exporter + Incremental Training
#  Build dataset -> Fine-tune -> Export to HF Hub
# ══════════════════════════════════════════════════════════╝

import json
import cv2
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image


class HuggingFaceExporter:
    """
    مصدّر HuggingFace + تدريب تزايدي.

    Workflow:
    1. Build dataset from corrected data (JSON or labels.txt)
    2. Fine-tune incrementally on the latest model
    3. Save new model version
    4. Upload to HuggingFace Hub (optional)
    """

    def __init__(
        self,
        models_dir: str,
        dataset_dir: str,
        hf_token: Optional[str] = None,
        hf_repo_name: str = "medical-ocr-arabic-custom",
    ):
        self.models_dir = Path(models_dir)
        self.dataset_dir = Path(dataset_dir)
        self.hf_token = hf_token
        self.hf_repo_name = hf_repo_name

    # ────────────────────────────────────────────────────────
    # Model Version Management
    # ────────────────────────────────────────────────────────

    def get_latest_model_path(self) -> str:
        """Return latest trained model path or base fallback."""
        if self.models_dir.exists():
            versions = sorted(
                [d for d in self.models_dir.iterdir()
                 if d.is_dir() and d.name.startswith('v')],
                key=lambda x: float(x.name[1:]),
            )
            if versions:
                return str(versions[-1])
        return "microsoft/trocr-base-handwritten"

    def get_next_version(self) -> str:
        """Calculate next version number."""
        if self.models_dir.exists():
            versions = sorted(
                [d for d in self.models_dir.iterdir()
                 if d.is_dir() and d.name.startswith('v')],
                key=lambda x: float(x.name[1:]),
            )
            if versions:
                current = float(versions[-1].name[1:])
                return f"v{current + 0.1:.1f}"
        return "v1.0"

    # ────────────────────────────────────────────────────────
    # Build Dataset from Corrected JSON
    # ────────────────────────────────────────────────────────

    def build_dataset_from_json(
        self,
        corrected_json: str,
    ) -> Tuple[str, int]:
        """
        Build training dataset from corrected JSON file.

        Args:
            corrected_json: Path to final_corrected.json.

        Returns:
            Tuple of (labels_file_path, total_lines).
        """
        json_path = Path(corrected_json)
        if not json_path.exists():
            raise FileNotFoundError(f"Corrected JSON not found: {json_path}")

        data = json.loads(json_path.read_text(encoding='utf-8'))

        images_dir = self.dataset_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_file = self.dataset_dir / 'labels.txt'

        labels = []
        for page in data:
            page_name = page.get('page', 'unknown')
            for line in page.get('lines', []):
                idx = line.get('idx', 0)
                text = line.get('text', '')
                if not text:
                    continue

                fn = f"{page_name}_L{idx:03d}.png"
                labels.append(f"{fn}\t{text}")

                crop = line.get('crop')
                if crop is not None:
                    if isinstance(crop, list):
                        crop = np.array(crop, dtype=np.uint8)
                    if len(crop.shape) == 2:
                        cv2.imwrite(str(images_dir / fn), crop)

        labels_file.write_text('\n'.join(labels), encoding='utf-8')
        print(f"Dataset built: {len(labels)} lines -> {labels_file}")
        return str(labels_file), len(labels)

    # ────────────────────────────────────────────────────────
    # Incremental Fine-tuning
    # ────────────────────────────────────────────────────────

    def fine_tune(
        self,
        labels_file: str,
        epochs: int = 15,
        batch_size: int = 8,
        learning_rate: float = 5e-5,
    ) -> str:
        """
        Incremental fine-tuning on corrected data.

        Args:
            labels_file: Path to labels.txt (tab-separated: filename\\ttext).
            epochs: Number of training epochs.
            batch_size: Training batch size.
            learning_rate: Learning rate.

        Returns:
            Path to the saved model directory.
        """
        from transformers import (
            TrOCRProcessor,
            VisionEncoderDecoderModel,
            Trainer,
            TrainingArguments,
            default_data_collator,
        )
        from torch.utils.data import Dataset

        model_src = self.get_latest_model_path()
        print(f"Loading base model: {model_src}")

        processor = TrOCRProcessor.from_pretrained(model_src)
        model = VisionEncoderDecoderModel.from_pretrained(model_src)

        labels_path = Path(labels_file)
        images_dir = labels_path.parent / 'images'
        content = labels_path.read_text(encoding='utf-8')
        entries = [l.strip().split('\t') for l in content.split('\n')
                    if l.strip() and '\t' in l]

        class OCRDataset(Dataset):
            def __init__(self, entries_list, images_directory, proc):
                self.entries = entries_list
                self.img_dir = images_directory
                self.processor = proc

            def __len__(self):
                return len(self.entries)

            def __getitem__(self, idx):
                fn, text = self.entries[idx]
                img_path = self.img_dir / fn
                if not img_path.exists():
                    pixel_values = torch.zeros(1, 3, 224, 224)
                    labels_tok = self.processor.tokenizer(
                        "", return_tensors='pt'
                    ).input_ids[0]
                    return {'pixel_values': pixel_values, 'labels': labels_tok}

                image = Image.open(str(img_path)).convert('RGB')
                encoding = self.processor(
                    images=image, text=text,
                    padding='max_length', max_length=64,
                    truncation=True, return_tensors='pt',
                )
                encoding = {k: v.squeeze(0) for k, v in encoding.items()}
                return encoding

        # 90/10 split
        split_idx = int(len(entries) * 0.9)
        train_entries = entries[:split_idx]
        eval_entries = entries[split_idx:]

        train_dataset = OCRDataset(train_entries, images_dir, processor)
        eval_dataset = OCRDataset(eval_entries, images_dir, processor)

        # Configure model
        model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
        model.config.pad_token_id = processor.tokenizer.pad_token_id
        model.config.vocab_size = model.config.decoder.vocab_size

        new_version = self.get_next_version()
        output_dir = self.models_dir / new_version
        output_dir.mkdir(parents=True, exist_ok=True)

        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            logging_steps=10,
            save_strategy='epoch',
            evaluation_strategy='epoch',
            load_best_model_at_end=True,
            metric_for_best_model='eval_loss',
            greater_is_better=False,
            remove_unused_columns=False,
            report_to='none',
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=default_data_collator,
        )

        print(f"Starting incremental training for {epochs} epochs...")
        trainer.train()

        trainer.save_model(str(output_dir))
        processor.save_pretrained(str(output_dir))
        print(f"Model saved: {output_dir}")
        return str(output_dir)

    # ────────────────────────────────────────────────────────
    # Export to HuggingFace Hub
    # ────────────────────────────────────────────────────────

    def export_to_huggingface(
        self,
        model_path: Optional[str] = None,
        repo_id: Optional[str] = None,
    ) -> str:
        """
        Upload model to HuggingFace Hub.

        Args:
            model_path: Local model path. If None, uses latest.
            repo_id: Target repo ID.

        Returns:
            Repository URL.
        """
        if not self.hf_token:
            raise ValueError("HuggingFace token is required for export.")

        from huggingface_hub import login, create_repo, HfApi

        login(self.hf_token)

        if model_path is None:
            model_path = self.get_latest_model_path()

        if repo_id is None:
            repo_id = self.hf_repo_name

        try:
            create_repo(repo_id, exist_ok=True)
        except Exception:
            pass

        api = HfApi()
        version = Path(model_path).name
        api.upload_folder(
            folder_path=model_path,
            repo_id=repo_id,
            commit_message=f"Update model {version}",
        )

        url = f"https://huggingface.co/{repo_id}"
        print(f"Model uploaded to: {url}")
        return url

    # ────────────────────────────────────────────────────────
    # Full Pipeline
    # ────────────────────────────────────────────────────────

    def run_full_pipeline(
        self,
        corrected_json: str,
        epochs: int = 15,
        export: bool = False,
    ) -> Dict:
        """
        Execute full pipeline: build dataset -> train -> export.

        Args:
            corrected_json: Path to final_corrected.json.
            epochs: Training epochs.
            export: If True, exports to HuggingFace.

        Returns:
            Dict with model_path, version, total_lines, hf_url (optional).
        """
        labels_file, total_lines = self.build_dataset_from_json(corrected_json)
        model_path = self.fine_tune(labels_file, epochs=epochs)
        version = Path(model_path).name

        result = {
            'model_path': model_path,
            'version': version,
            'total_lines': total_lines,
        }

        if export and self.hf_token:
            hf_url = self.export_to_huggingface(model_path)
            result['hf_url'] = hf_url

        return result
