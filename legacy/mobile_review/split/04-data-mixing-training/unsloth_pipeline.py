# unsloth_pipeline.py - Fast training pipeline using Unsloth

"""
🏋️ خط أنابيب تدريب مُحسّن بـ Unsloth لتصحيح الأخطاء العربية
متوافق مع Colab Free Tier (T4 16GB)
"""

import os, json
import torch
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments, DataCollatorForSeq2Seq
from datasets import load_dataset
import logging

logger = logging.getLogger(__name__)

def train_with_unsloth(
    data_path: str,
    output_dir: str = "qwen2.5-0.5b-unsloth-ar",
    epochs: int = 3,
    batch_size: int = 4,
    lr: float = 2e-4
) -> str:
    # 1️⃣ تحميل النموذج بـ 4-bit quantization + تحسينات Unsloth
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        max_seq_length=512,
        dtype=None,  # يكتشف fp16 تلقائياً على GPU
        load_in_4bit=True,
    )

    # 2️⃣ تطبيق LoRA المُحسّن
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",  # توفير VRAM هائل
        random_state=42,
    )

    # 3️⃣ تنسيق البيانات
    def format_prompt(examples):
        prompts = [
            f"<|im_start|>system\nأنت مصحح لغوي عربي متخصص في نصوص OCR. صحح الأخطاء مع الحفاظ على الأرقام والهيكل.<|im_end|>\n"
            f"<|im_start|>user\nالنص: {inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
            for inp, out in zip(examples["input"], examples["output"])
        ]
        return tokenizer(prompts, padding="max_length", truncation=True, max_length=512)

    ds = load_dataset("json", data_files=data_path, split="train")
    ds = ds.train_test_split(test_size=0.1)
    tokenized = ds.map(format_prompt, batched=True, remove_columns=["instruction", "input", "output"])

    # 4️⃣ معاملات التدريب المُسرّعة
    args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=lr,
        num_train_epochs=epochs,
        fp16=True,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        remove_unused_columns=False,
        optim="paged_adamw_8bit",  # مُحسّن لـ Unsloth
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
        args=args,
    )

    logger.info("🚀 بدء التدريب المُحسّن...")
    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    logger.info(f"✅ اكتمل التدريب وحُفظ في: {output_dir}")
    return output_dir
