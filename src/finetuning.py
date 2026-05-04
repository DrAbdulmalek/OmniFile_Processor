"""
HandwrittenOCR - تدريب LoRA على TrOCR v4.0
==============================================
المحسنات:
- global trocr_model (تصحيح #10)
- commit_message مع التاريخ
- تحديث تلقائي للنموذج في OCREngine
"""

import os
import io
import logging
from PIL import Image
from datetime import datetime

logger = logging.getLogger("HandwrittenOCR")


def finetune_trocr_lora(
    ocr_engine,
    db,
    save_path: str,
    min_samples: int = 50,
    epochs: int = 5,
    batch_size: int = 4,
    lr: float = 1e-5,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.1,
    lora_target_modules: list | None = None,
) -> bool:
    """
    تدريب TrOCR باستخدام LoRA على البيانات الموثقة.

    بعد التدريب يُحدَّث ocr_engine.trocr_model تلقائياً.
    """
    try:
        from peft import get_peft_model, LoraConfig, TaskType
        from torch.optim import AdamW
        from torch.utils.data import Dataset, DataLoader
    except ImportError:
        logger.error("peft غير مثبت")
        return False

    if lora_target_modules is None:
        lora_target_modules = ["query", "value"]

    # تصريح global لتحديث النموذج (تصحيح #10)
    global trocr_model
    trocr_model = ocr_engine.trocr_model
    trocr_processor = ocr_engine.trocr_processor
    device = ocr_engine.device

    # فحص العينات (يشمل verified و sentence_corrected)
    verified = db.get_verified()
    verified = [
        w for w in verified
        if w.get("status") in ("verified", "sentence_corrected")
    ]

    if len(verified) < min_samples:
        logger.warning(
            f"عينات غير كافية: {len(verified)} < {min_samples}"
        )
        return False

    print(f"بدء التدريب على {len(verified)} عينة...")

    # إعداد LoRA
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        target_modules=lora_target_modules,
        lora_dropout=lora_dropout,
    )
    model = get_peft_model(trocr_model, lora_config)
    model.train()

    # Dataset
    class HandwritingDataset(Dataset):
        def __init__(self, records):
            self.records = records

        def __len__(self):
            return len(self.records)

        def __getitem__(self, idx):
            row = self.records[idx]
            img = Image.open(io.BytesIO(row["image_data"])).convert("RGB")
            pixel_values = trocr_processor(
                images=img, return_tensors="pt"
            ).pixel_values.squeeze()
            text = row["predicted_text"] or ""
            labels = trocr_processor.tokenizer(
                text, return_tensors="pt",
                padding="max_length", max_length=64,
            ).input_ids.squeeze()
            labels[labels == trocr_processor.tokenizer.pad_token_id] = -100
            return {"pixel_values": pixel_values, "labels": labels}

    dataset = HandwritingDataset(verified)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = AdamW(model.parameters(), lr=lr)

    # التدريب
    for epoch in range(epochs):
        total_loss = 0
        batch_count = 0
        for batch in loader:
            out = model(
                pixel_values=batch["pixel_values"].to(device),
                labels=batch["labels"].to(device),
            )
            out.loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            total_loss += out.loss.item()
            batch_count += 1

        avg_loss = total_loss / max(batch_count, 1)
        print(f"Epoch {epoch + 1}/{epochs} | Loss: {avg_loss:.4f}")

    # حفظ النموذج
    os.makedirs(save_path, exist_ok=True)
    model.save_pretrained(save_path)
    trocr_processor.save_pretrained(save_path)

    # تحديث النموذج في OCREngine تلقائياً
    ocr_engine.trocr_model = model
    ocr_engine.lora_loaded = True

    print(f"تم حفظ النموذج في: {save_path}")
    logger.info(f"تم تدريب LoRA وحفظه في: {save_path}")
    return True


def check_auto_train(db, min_samples: int = 100) -> bool:
    """
    فحص ما إذا كان عدد العينات المؤكدة كافياً للتدريب التلقائي.
    يُستدعى بعد كل عملية مراجعة لتشغيل التدريب تلقائياً.
    """
    verified_count = db.get_verified_count()
    logger.debug(f"check_auto_train: {verified_count} عينة مؤكدة (مطلوب ≥{min_samples})")
    if verified_count >= min_samples:
        logger.info(f"العدد كافي ({verified_count} ≥ {min_samples}) — يمكن بدء التدريب التلقائي")
        return True
    return False
