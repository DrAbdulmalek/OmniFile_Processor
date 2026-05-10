#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_checkpoint.py
======================

تقييم نموذج HTR/OCR مع مقاييس CER/WER وتحليل الأخطاء.

الاستخدام:
    python evaluate_checkpoint.py --checkpoint ./checkpoints --test-dataset ./test
    python evaluate_checkpoint.py --checkpoint ./checkpoints --test-dataset ./test --visualize

المؤلف: Dr. Abdulmalek Al-husseini
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from peft import PeftModel

# ============================================================================
# التطبيع العربي
# ============================================================================

class ArabicNormalizer:
    """تطبيع النص العربي للتقييم العادل."""
    
    ALEF_VARIANTS = {
        'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا'
    }
    
    YEH_VARIANTS = {
        'ى': 'ي', 'ئ': 'ي'
    }
    
    HEH_VARIANTS = {
        'ة': 'ه'
    }
    
    DIACRITICS = ''.join(chr(c) for c in range(0x064B, 0x065F+1))
    
    def __init__(self, remove_diacritics: bool = False,
                 normalize_alef: bool = True,
                 normalize_yeh: bool = True,
                 normalize_heh: bool = False):
        self.remove_diacritics = remove_diacritics
        self.normalize_alef = normalize_alef
        self.normalize_yeh = normalize_yeh
        self.normalize_heh = normalize_heh
    
    def normalize(self, text: str) -> str:
        """تطبيق التطبيع."""
        result = text
        
        # إزالة التشكيل
        if self.remove_diacritics:
            result = ''.join(c for c in result if c not in self.DIACRITICS)
        
        # تطبيع الألف
        if self.normalize_alef:
            for old, new in self.ALEF_VARIANTS.items():
                result = result.replace(old, new)
        
        # تطبيع الياء
        if self.normalize_yeh:
            for old, new in self.YEH_VARIANTS.items():
                result = result.replace(old, new)
        
        # تطبيع التاء المربوطة
        if self.normalize_heh:
            for old, new in self.HEH_VARIANTS.items():
                result = result.replace(old, new)
        
        return result


# ============================================================================
# حساب المقاييس
# ============================================================================

def compute_cer(predictions: List[str], references: List[str]) -> float:
    """حساب Character Error Rate."""
    total_errors = 0
    total_chars = 0
    
    for pred, ref in zip(predictions, references):
        # مسافة ليفنشتاين
        m, n = len(pred), len(ref)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if pred[i-1] == ref[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # حذف
                    dp[i][j-1] + 1,      # إدراج
                    dp[i-1][j-1] + cost  # استبدال
                )
        
        total_errors += dp[m][n]
        total_chars += n
    
    return total_errors / total_chars if total_chars > 0 else 0


def compute_wer(predictions: List[str], references: List[str]) -> float:
    """حساب Word Error Rate."""
    total_errors = 0
    total_words = 0
    
    for pred, ref in zip(predictions, references):
        pred_words = pred.split()
        ref_words = ref.split()
        
        m, n = len(pred_words), len(ref_words)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if pred_words[i-1] == ref_words[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost
                )
        
        total_errors += dp[m][n]
        total_words += n
    
    return total_errors / total_words if total_words > 0 else 0


def compute_accuracy(predictions: List[str], references: List[str]) -> float:
    """حساب الدقة الحرفية."""
    correct = sum(p == r for p, r in zip(predictions, references))
    return correct / len(predictions) if predictions else 0


# ============================================================================
# تحليل الأخطاء
# ============================================================================

class ErrorAnalyzer:
    """تحليل أنماط الأخطاء في OCR."""
    
    def __init__(self):
        self.substitutions = Counter()
        self.insertions = Counter()
        self.deletions = Counter()
        self.confusion_matrix = defaultdict(Counter)
        self.error_by_length = defaultdict(list)
        self.error_by_char = Counter()
    
    def analyze(self, predictions: List[str], references: List[str]):
        """تحليل الأخطاء بين التنبؤات والمراجع."""
        for pred, ref in zip(predictions, references):
            # محاذاة التسلسل
            aligned_pred, aligned_ref = self._align_sequences(pred, ref)
            
            # تحليل
            for p_char, r_char in zip(aligned_pred, aligned_ref):
                if p_char == r_char:
                    continue
                
                if p_char == '_':
                    # حذف
                    self.deletions[r_char] += 1
                    self.error_by_char[r_char] += 1
                elif r_char == '_':
                    # إدراج
                    self.insertions[p_char] += 1
                else:
                    # استبدال
                    self.substitutions[(r_char, p_char)] += 1
                    self.confusion_matrix[r_char][p_char] += 1
                    self.error_by_char[r_char] += 1
            
            # حفظ حسب الطول
            self.error_by_length[len(ref)].append(
                (pred, ref, compute_cer([pred], [ref]))
            )
    
    def _align_sequences(self, seq1: str, seq2: str) -> Tuple[str, str]:
        """محاذاة تسلسلين باستخدام Needleman-Wunsch."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = -i
        for j in range(n + 1):
            dp[0][j] = -j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = 1 if seq1[i-1] == seq2[j-1] else -1
                dp[i][j] = max(
                    dp[i-1][j-1] + match,
                    dp[i-1][j] - 1,
                    dp[i][j-1] - 1
                )
        
        # التتبع العكسي
        aligned1, aligned2 = [], []
        i, j = m, n
        while i > 0 or j > 0:
            if i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + (1 if seq1[i-1] == seq2[j-1] else -1):
                aligned1.append(seq1[i-1])
                aligned2.append(seq2[j-1])
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i-1][j] - 1:
                aligned1.append(seq1[i-1])
                aligned2.append('_')
                i -= 1
            else:
                aligned1.append('_')
                aligned2.append(seq2[j-1])
                j -= 1
        
        return ''.join(reversed(aligned1)), ''.join(reversed(aligned2))
    
    def get_report(self, top_n: int = 20) -> Dict:
        """توليد تقرير الأخطاء."""
        return {
            'top_substitutions': self.substitutions.most_common(top_n),
            'top_deletions': self.deletions.most_common(top_n),
            'top_insertions': self.insertions.most_common(top_n),
            'most_confused_chars': [
                (char, self.confusion_matrix[char].most_common(3))
                for char, _ in self.error_by_char.most_common(top_n)
            ],
            'error_by_length': {
                length: {
                    'count': len(errors),
                    'avg_cer': np.mean([e[2] for e in errors])
                }
                for length, errors in sorted(self.error_by_length.items())
            }
        }


# ============================================================================
# التقييم الرئيسي
# ============================================================================

class HTREvaluator:
    """مُقيّم شامل لنماذج HTR."""
    
    def __init__(
        self,
        checkpoint_path: Path,
        device: str = 'cuda',
        use_lora: bool = True
    ):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.checkpoint_path = Path(checkpoint_path)
        self.use_lora = use_lora
        
        # تحميل النموذج
        self._load_model()
    
    def _load_model(self):
        """تحميل النموذج والمعالج."""
        logger.info(f"📥 تحميل النموذج من: {self.checkpoint_path}")
        
        # البحث عن النموذج
        if (self.checkpoint_path / 'merged').exists():
            model_path = self.checkpoint_path / 'merged'
        elif (self.checkpoint_path / 'lora_adapter').exists():
            model_path = self.checkpoint_path
            lora_path = self.checkpoint_path / 'lora_adapter'
        else:
            model_path = self.checkpoint_path
            lora_path = None
        
        # تحميل المعالج
        self.processor = TrOCRProcessor.from_pretrained(model_path)
        
        # تحميل النموذج الأساسي
        base_model = VisionEncoderDecoderModel.from_pretrained(model_path)
        
        # تطبيق LoRA إن وجد
        if lora_path and lora_path.exists() and self.use_lora:
            logger.info("🔧 تطبيق LoRA...")
            base_model = PeftModel.from_pretrained(base_model, lora_path)
        
        self.model = base_model.to(self.device)
        self.model.eval()
        
        logger.info("✅ تم تحميل النموذج")
    
    def predict(self, image: Image.Image) -> str:
        """التنبؤ بصورة واحدة."""
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(pixel_values)
        
        text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text
    
    def evaluate(
        self,
        test_dataset_path: Path,
        batch_size: int = 8,
        num_beams: int = 4,
        normalizer: ArabicNormalizer = None
    ) -> Dict:
        """تقييم النموذج على مجموعة اختبار."""
        
        # تحميل البيانات
        test_samples = self._load_test_data(test_dataset_path)
        logger.info(f"📊 عدد عينات الاختبار: {len(test_samples)}")
        
        predictions = []
        references = []
        raw_predictions = []
        
        # التنبؤ
        for i in tqdm(range(0, len(test_samples), batch_size), desc="🔍 التقييم"):
            batch = test_samples[i:i+batch_size]
            
            # معالجة الصور
            images = [s['image'] for s in batch]
            pixel_values = self.processor(images, return_tensors="pt").pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # التوليد
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    num_beams=num_beams,
                    early_stopping=True
                )
            
            batch_preds = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )
            
            for sample, pred in zip(batch, batch_preds):
                raw_predictions.append(pred)
                ref = sample['text']
                
                # تطبيع
                if normalizer:
                    pred = normalizer.normalize(pred)
                    ref = normalizer.normalize(ref)
                
                predictions.append(pred)
                references.append(ref)
        
        # حساب المقاييس
        cer = compute_cer(predictions, references)
        wer = compute_wer(predictions, references)
        accuracy = compute_accuracy(predictions, references)
        
        # تحليل الأخطاء
        analyzer = ErrorAnalyzer()
        analyzer.analyze(predictions, references)
        
        results = {
            'cer': cer,
            'wer': wer,
            'accuracy': accuracy,
            'num_samples': len(test_samples),
            'error_analysis': analyzer.get_report(),
            'samples': []
        }
        
        # عينات للمراجعة
        for i in range(min(10, len(predictions))):
            results['samples'].append({
                'prediction': raw_predictions[i],
                'reference': test_samples[i]['text'],
                'normalized_pred': predictions[i],
                'normalized_ref': references[i],
                'correct': predictions[i] == references[i]
            })
        
        return results
    
    def _load_test_data(self, path: Path) -> List[Dict]:
        """تحميل بيانات الاختبار."""
        samples = []
        
        if path.suffix == '.lmdb':
            import lmdb
            import pickle
            
            env = lmdb.open(str(path), readonly=True)
            with env.begin() as txn:
                n = int(txn.get(b'__len__'))
                for i in range(n):
                    key = f"{i:08d}".encode()
                    data = pickle.loads(txn.get(key))
                    
                    img = Image.frombytes(
                        'RGB',
                        data.get('size', (384, 384)),
                        data['image']
                    ) if 'size' in data else Image.open(data['image_path'])
                    
                    samples.append({
                        'image': img,
                        'text': data['text']
                    })
            env.close()
            
        elif path.is_dir():
            # مجلد صور + labels.txt
            labels_file = path / 'labels.txt'
            images_dir = path / 'images'
            
            with open(labels_file, 'r', encoding='utf-8') as f:
                next(f)  # تخطي العنوان
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) == 2:
                        img_path = images_dir / parts[0]
                        if img_path.exists():
                            samples.append({
                                'image': Image.open(img_path).convert('RGB'),
                                'text': parts[1]
                            })
        
        return samples
    
    def visualize_errors(
        self,
        test_dataset_path: Path,
        output_dir: Path,
        max_samples: int = 50
    ):
        """تصور الأخطاء."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        test_samples = self._load_test_data(test_dataset_path)
        
        errors_dir = output_dir / 'errors'
        correct_dir = output_dir / 'correct'
        errors_dir.mkdir(exist_ok=True)
        correct_dir.mkdir(exist_ok=True)
        
        error_count = 0
        correct_count = 0
        
        for sample in tqdm(test_samples, desc="🎨 تصور"):
            pred = self.predict(sample['image'])
            ref = sample['text']
            
            is_correct = pred == ref
            
            if is_correct and correct_count < max_samples:
                sample['image'].save(correct_dir / f"correct_{correct_count:04d}.png")
                with open(correct_dir / f"correct_{correct_count:04d}.txt", 'w') as f:
                    f.write(f"Pred: {pred}\nRef:  {ref}")
                correct_count += 1
            
            elif not is_correct and error_count < max_samples:
                # إنشاء صورة مقارنة
                fig = self._create_comparison_image(
                    sample['image'], pred, ref
                )
                cv2.imwrite(
                    str(errors_dir / f"error_{error_count:04d}.png"),
                    fig
                )
                error_count += 1
            
            if error_count >= max_samples and correct_count >= max_samples:
                break
        
        logger.info(f"✅ تصحيح: {correct_count}, أخطاء: {error_count}")
    
    def _create_comparison_image(
        self,
        image: Image.Image,
        prediction: str,
        reference: str
    ) -> np.ndarray:
        """إنشاء صورة مقارنة."""
        img_array = np.array(image)
        h, w = img_array.shape[:2]
        
        # إنشاء لوحة
        panel_h = h + 100
        panel = np.ones((panel_h, w, 3), dtype=np.uint8) * 255
        
        # وضع الصورة
        panel[:h, :w] = img_array
        
        # إضافة النصوص
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # التنبؤ (أحمر إن كان خطأ)
        color_pred = (0, 0, 255) if prediction != reference else (0, 255, 0)
        cv2.putText(panel, f"Pred: {prediction[:50]}", (10, h + 30),
                   font, 0.6, color_pred, 2)
        
        # المرجع (أخضر)
        cv2.putText(panel, f"Ref:  {reference[:50]}", (10, h + 60),
                   font, 0.6, (0, 128, 0), 2)
        
        return panel


# ============================================================================
# الدالة الرئيسية
# ============================================================================

import logging
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="تقييم نموذج HTR")
    parser.add_argument('--checkpoint', type=Path, required=True,
                       help='مسار checkpoint النموذج')
    parser.add_argument('--test-dataset', type=Path, required=True,
                       help='مسار بيانات الاختبار')
    parser.add_argument('--output', type=Path, default='./evaluation_results',
                       help='مجلد نتائج التقييم')
    parser.add_argument('--metrics', nargs='+', 
                       default=['cer', 'wer', 'accuracy'],
                       choices=['cer', 'wer', 'accuracy', 'all'])
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--num-beams', type=int, default=4)
    parser.add_argument('--normalize-arabic', action='store_true',
                       help='تطبيع النص العربي')
    parser.add_argument('--remove-diacritics', action='store_true',
                       help='إزالة التشكيل')
    parser.add_argument('--visualize', action='store_true',
                       help='تصور الأخطاء')
    parser.add_argument('--export-errors', type=Path,
                       help='تصدير تحليل الأخطاء لملف JSON')
    
    args = parser.parse_args()
    
    # إعداد التسجيل
    logging.basicConfig(level=logging.INFO)
    
    # التطبيع
    normalizer = None
    if args.normalize_arabic:
        normalizer = ArabicNormalizer(
            remove_diacritics=args.remove_diacritics,
            normalize_alef=True,
            normalize_yeh=True
        )
    
    # التقييم
    evaluator = HTREvaluator(args.checkpoint)
    results = evaluator.evaluate(
        args.test_dataset,
        batch_size=args.batch_size,
        num_beams=args.num_beams,
        normalizer=normalizer
    )
    
    # طباعة النتائج
    print("\n" + "=" * 60)
    print("📊 نتائج التقييم")
    print("=" * 60)
    print(f"📝 عدد العينات: {results['num_samples']}")
    print(f"📉 CER:        {results['cer']:.4f} ({results['cer']*100:.2f}%)")
    print(f"📉 WER:        {results['wer']:.4f} ({results['wer']*100:.2f}%)")
    print(f"✅ Accuracy:   {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
    print("=" * 60)
    
    # تحليل الأخطاء
    if 'error_analysis' in results:
        print("\n🔍 تحليل الأخطاء:")
        analysis = results['error_analysis']
        
        print("\nأكثر الاستبدالات شيوعاً:")
        for (orig, pred), count in analysis['top_substitutions'][:5]:
            print(f"  '{orig}' → '{pred}': {count}")
        
        print("\nأكثر الحذوفات:")
        for char, count in analysis['top_deletions'][:5]:
            print(f"  '{char}': {count}")
    
    # تصدير
    args.output.mkdir(parents=True, exist_ok=True)
    
    with open(args.output / 'results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # تصدير الأخطاء المفصلة
    if args.export_errors:
        with open(args.export_errors, 'w', encoding='utf-8') as f:
            json.dump(results['error_analysis'], f, ensure_ascii=False, indent=2)
    
    # تصور
    if args.visualize:
        print("\n🎨 جاري تصور الأخطاء...")
        evaluator.visualize_errors(
            args.test_dataset,
            args.output / 'visualizations'
        )
    
    print(f"\n💾 تم حفظ النتائج في: {args.output}")


if __name__ == '__main__':
    main()
