### `models/arabic_spell_corrector.py`

> 💡 *لماذا Qwen2.5-0.5B وليس TinyLlama؟* → دعم عربي أصلي، معمارية حديثة، وأداء أفضل بـ 3x على النصوص المختلطة. سنستخدم `LoRA` للتدريب على 4GB VRAM (متاح حتى في Colab المجاني).

### 📦 1. تحضير البيانات للتدريب
```python
# prepare_training_data.py
import json
from pathlib import Path
from core.voting_tracker import CorrectionVoter

def export_instruction_data(voting_cache: str, output_path: str, min_samples: int = 100):
    voter = CorrectionVoter(storage_path=voting_cache)
    approved = voter.export_approved_corrections()

    if len(approved) < min_samples:
        raise ValueError(f"نحتاج {min_samples} تصحيح معتمد على الأقل. المتاح: {len(approved)}")

    instructions = []
    for original, corrected in approved.items():
        instructions.append({
            "instruction": "صحح الأخطاء الإملائية والنحوية في النص التالي مع الحفاظ على المعنى والأرقام والتكوين الأصلي.",
            "input": original,
            "output": corrected
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(instructions, f, ensure_ascii=False, indent=2)
    return output_path
```

### 🏋️ 2. كود التدريب (Colab-Ready)
```python
# train_corrector.py
import os, json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, DataCollatorForSeq2Seq
from datasets import load_dataset
from trl import SFTTrainer
from peft import LoraConfig, get_peft_model, TaskType

def train_arabic_corrector(
    data_path: str,
    output_dir: str = "models/qwen2.5-0.5b-ar-corrector",
    epochs: int = 3,
    batch_size: int = 8
):
    # 1. تحميل النموذج والـ Tokenizer
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    # 2. إعداد LoRA (تدريب خفيف على 4GB VRAM)
    lora_config = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05,
        bias="none", task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 3. تحميل البيانات وتنسيقها
    def format_prompt(examples):
        texts = [
            f"<|im_start|>system\nأنت مصحح لغوي عربي متخصص في نصوص OCR.<|im_end|>\n"
            f"<|im_start|>user\nصحح: {inp}<|im_end|>\n"
            f"<|im_start|>assistant\n{out}<|im_end|>"
            for inp, out in zip(examples["input"], examples["output"])
        ]
        return tokenizer(texts, padding=True, truncation=True, max_length=512)

    ds = load_dataset("json", data_files=data_path, split="train")
    ds = ds.train_test_split(test_size=0.1)
    tokenized_ds = ds.map(format_prompt, batched=True, remove_columns=["instruction", "input", "output"])

    # 4. التدريب
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=epochs,
        fp16=True,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        remove_unused_columns=False,
        report_to="none"
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_ds["train"],
        eval_dataset=tokenized_ds["test"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8)
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    return output_dir
```

### 🔍 3. واجهة الاستدلال (Inference Wrapper)
```python
# inference_corrector.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

class ArabicSpellCorrector:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
        )
        self.pipe = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=128)

    def correct(self, text: str, fallback_to_voting: bool = True, voter: "CorrectionVoter" = None) -> str:
        if not text.strip(): return text

        # محاولة التصحيح الآلي أولاً
        prompt = f"<|im_start|>system\nأنت مصحح لغوي عربي متخصص في نصوص OCR.<|im_end|>\n<|im_start|>user\nصحح: {text}<|im_end|>\n<|im_start|>assistant\n"
        result = self.pipe(prompt, do_sample=True, temperature=0.3, top_p=0.9)[0]["generated_text"]
        corrected = result.split("<|im_start|>assistant\n")[-1].strip()

        # التحقق من جودة المخرج
        if len(corrected) < len(text) * 0.5 or len(corrected) > len(text) * 2:
            if fallback_to_voting and voter:
                consensus = voter.get_consensus(text)
                if consensus:
                    return consensus[0]
            return text  # فشل الآلي، إرجاع الأصلي

        return corrected
```

---

