#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prepare_htr_dataset.py
======================

يحول أي مجموعة صور إلى تنسيق تدريب جاهز لنماذج HTR/OCR.

الاستخدام:
    python prepare_htr_dataset.py --input-dir ./images --labels labels.txt --output-dir ./dataset
    python prepare_htr_dataset.py --pdf document.pdf --output-dir ./dataset
    python prepare_htr_dataset.py --mobile-review ocr_corrected.json --output-dir ./dataset

المؤلف: Dr. Abdulmalek Al-husseini
"""

import argparse
import json
import lmdb
import os
import pickle
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

# ============================================================================
# الثوابت
# ============================================================================

SUPPORTED_FORMATS = ["lmdb", "tsv", "jsonl", "hf_dataset", "folder"]
DEFAULT_IMAGE_SIZE = (384, 384)
LMDB_MAP_SIZE = 1099511627776  # 1TB

# ============================================================================
# فئات المحملات (Loaders)
# ============================================================================

class BaseDatasetLoader:
    """الفئة الأساسية لجميع محملات البيانات."""
    
    def __init__(self, config: dict):
        self.config = config
        self.samples: List[Dict] = []
    
    def load(self) -> List[Dict]:
        """تحميل العينات. يجب تجاوزها."""
        raise NotImplementedError
    
    def validate(self) -> bool:
        """التحقق من صحة البيانات."""
        raise NotImplementedError


class ImageFolderLoader(BaseDatasetLoader):
    """
    محمل صور منفصلة + ملف نصي.
    
    تنسيق labels.txt:
        image_001.jpg \t السلام عليكم
        image_002.png \t مرحبا بالعالم
    """
    
    def __init__(self, image_dir: Path, labels_file: Path, **kwargs):
        super().__init__(kwargs)
        self.image_dir = Path(image_dir)
        self.labels_file = Path(labels_file)
    
    def load(self) -> List[Dict]:
        self.samples = []
        
        # قراءة ملف التسميات
        with open(self.labels_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('\t')
                if len(parts) != 2:
                    # محاولة الفصل بالمسافة
                    parts = line.split(' ', 1)
                    if len(parts) != 2:
                        print(f"⚠️  سطر {line_num}: تنسيق غير صحيح - {line[:50]}")
                        continue
                
                image_name, text = parts[0].strip(), parts[1].strip()
                image_path = self.image_dir / image_name
                
                if not image_path.exists():
                    print(f"⚠️  الصورة غير موجودة: {image_path}")
                    continue
                
                self.samples.append({
                    'image_path': str(image_path),
                    'text': text,
                    'source': 'image_folder'
                })
        
        print(f"✅ تم تحميل {len(self.samples)} عينة من مجلد الصور")
        return self.samples
    
    def validate(self) -> bool:
        valid = 0
        for sample in self.samples:
            img_path = Path(sample['image_path'])
            if img_path.exists() and img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                valid += 1
        
        print(f"✅ صالحة: {valid}/{len(self.samples)}")
        return valid > 0


class PDFLoader(BaseDatasetLoader):
    """محمل PDF مع استخراج النصوص."""
    
    def __init__(self, pdf_path: Path, dpi: int = 300, **kwargs):
        super().__init__(kwargs)
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi
    
    def load(self) -> List[Dict]:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF مطلوب. ثبته: pip install PyMuPDF")
        
        self.samples = []
        doc = fitz.open(self.pdf_path)
        
        output_dir = Path(self.config.get('output_dir', './pdf_extracted'))
        images_dir = output_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for page_num in tqdm(range(len(doc)), desc="📄 استخراج صفحات PDF"):
            page = doc[page_num]
            
            # استخراج النص
            text = page.get_text().strip()
            if not text:
                continue
            
            # تحويل الصفحة لصورة
            pix = page.get_pixmap(matrix=fitz.Matrix(self.dpi/72, self.dpi/72))
            image_path = images_dir / f"page_{page_num:04d}.png"
            pix.save(str(image_path))
            
            self.samples.append({
                'image_path': str(image_path),
                'text': text,
                'source': 'pdf',
                'page': page_num
            })
        
        doc.close()
        print(f"✅ تم استخراج {len(self.samples)} صفحة من PDF")
        return self.samples
    
    def validate(self) -> bool:
        return len(self.samples) > 0


class MobileReviewLoader(BaseDatasetLoader):
    """
    محمل تصديرات mobile_review.
    
    تنسيق JSON:
    [
        {
            "image_path": "...",
            "ocr_result": "نص OCR",
            "corrected_text": "النص المصحح",
            "confidence": 0.75,
            "reviewer_agreement": 0.95
        }
    ]
    """
    
    def __init__(self, review_json: Path, min_confidence: float = 0.7,
                 auto_include_high_confidence: bool = True, **kwargs):
        super().__init__(kwargs)
        self.review_json = Path(review_json)
        self.min_confidence = min_confidence
        self.auto_include_high_confidence = auto_include_high_confidence
    
    def load(self) -> List[Dict]:
        with open(self.review_json, 'r', encoding='utf-8') as f:
            reviews = json.load(f)
        
        self.samples = []
        auto_train = []
        needs_review = []
        
        for review in reviews:
            # التحقق من وجود تصحيح
            corrected = review.get('corrected_text', '').strip()
            if not corrected:
                continue
            
            confidence = review.get('confidence', 0)
            agreement = review.get('reviewer_agreement', 0)
            
            sample = {
                'image_path': review.get('image_path', ''),
                'text': corrected,
                'ocr_original': review.get('ocr_result', ''),
                'confidence': confidence,
                'reviewer_agreement': agreement,
                'source': 'mobile_review'
            }
            
            # تصنيف العينة
            if (agreement > 0.9 and confidence > self.min_confidence and 
                self.auto_include_high_confidence):
                sample['auto_train'] = True
                auto_train.append(sample)
            else:
                sample['auto_train'] = False
                needs_review.append(sample)
            
            self.samples.append(sample)
        
        print(f"✅ تم تحميل {len(self.samples)} تصحيح")
        print(f"   🟢 تدريب تلقائي: {len(auto_train)}")
        print(f"   🟡 تحتاج مراجعة: {len(needs_review)}")
        
        return self.samples
    
    def validate(self) -> bool:
        return len(self.samples) > 0
    
    def export_split(self, output_dir: Path):
        """تصدير العينات المصنفة."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        auto_train = [s for s in self.samples if s.get('auto_train', False)]
        needs_review = [s for s in self.samples if not s.get('auto_train', False)]
        
        with open(output_dir / 'auto_train.json', 'w', encoding='utf-8') as f:
            json.dump(auto_train, f, ensure_ascii=False, indent=2)
        
        with open(output_dir / 'needs_review.json', 'w', encoding='utf-8') as f:
            json.dump(needs_review, f, ensure_ascii=False, indent=2)
        
        print(f"💾 تم تصدير التقسيم إلى {output_dir}")


class SyntheticDataGenerator(BaseDatasetLoader):
    """
    مولد بيانات صناعية للتدريب.
    يستخدم PIL لرسم نصوص عربية بخطوط مختلفة.
    """
    
    def __init__(self, corpus_path: Path, fonts_dir: Path, 
                 num_samples: int = 10000, lang: str = 'ar',
                 augmentations: List[str] = None, **kwargs):
        super().__init__(kwargs)
        self.corpus_path = Path(corpus_path)
        self.fonts_dir = Path(fonts_dir)
        self.num_samples = num_samples
        self.lang = lang
        self.augmentations = augmentations or ['rotation', 'noise', 'blur', 'contrast']
    
    def load(self) -> List[Dict]:
        # قراءة النصوص
        with open(self.corpus_path, 'r', encoding='utf-8') as f:
            texts = [line.strip() for line in f if line.strip()]
        
        # جمع الخطوط
        fonts = list(self.fonts_dir.glob('**/*.ttf')) + \
                list(self.fonts_dir.glob('**/*.otf'))
        
        if not fonts:
            raise ValueError(f"لا توجد خطوط في {self.fonts_dir}")
        
        print(f"📝 {len(texts)} نص، {len(fonts)} خط")
        
        self.samples = []
        output_dir = Path(self.config.get('output_dir', './synthetic'))
        images_dir = output_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for i in tqdm(range(self.num_samples), desc="🎨 توليد بيانات صناعية"):
            # اختيار نص عشوائي
            text = np.random.choice(texts)
            
            # اختيار خط عشوائي
            font_path = np.random.choice(fonts)
            
            # إنشاء الصورة
            image = self._render_text(text, font_path)
            
            # تطبيق التعزيزات
            image = self._augment(image)
            
            # حفظ
            image_path = images_dir / f"synth_{i:06d}.png"
            image.save(image_path)
            
            self.samples.append({
                'image_path': str(image_path),
                'text': text,
                'source': 'synthetic',
                'font': font_path.name
            })
        
        print(f"✅ تم توليد {len(self.samples)} عينة صناعية")
        return self.samples
    
    def _render_text(self, text: str, font_path: Path) -> Image.Image:
        """رسم نص على صورة."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import arabic_reshaper
            from bidi.algorithm import get_display
            
            # إعادة تشكيل العربي
            reshaped = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped)
            
            # تحميل الخط
            font_size = np.random.randint(24, 48)
            font = ImageFont.truetype(str(font_path), font_size)
            
            # حساب الحجم
            dummy_img = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            bbox = draw.textbbox((0, 0), bidi_text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            # إنشاء الصورة مع هوامش
            padding = 20
            img = Image.new('RGB', (w + padding*2, h + padding*2), 'white')
            draw = ImageDraw.Draw(img)
            draw.text((padding, padding), bidi_text, font=font, fill='black')
            
            return img
            
        except Exception as e:
            # fallback بسيط
            img = Image.new('RGB', (400, 100), 'white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), text, fill='black')
            return img
    
    def _augment(self, image: Image.Image) -> Image.Image:
        """تطبيق تعزيزات عشوائية."""
        img_array = np.array(image)
        
        if 'rotation' in self.augmentations and np.random.random() < 0.3:
            angle = np.random.uniform(-5, 5)
            h, w = img_array.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            img_array = cv2.warpAffine(img_array, M, (w, h), 
                                       borderValue=(255, 255, 255))
        
        if 'noise' in self.augmentations and np.random.random() < 0.3:
            noise = np.random.normal(0, 15, img_array.shape).astype(np.uint8)
            img_array = cv2.add(img_array, noise)
        
        if 'blur' in self.augmentations and np.random.random() < 0.2:
            k = np.random.choice([3, 5])
            img_array = cv2.GaussianBlur(img_array, (k, k), 0)
        
        if 'contrast' in self.augmentations and np.random.random() < 0.3:
            alpha = np.random.uniform(0.8, 1.2)
            beta = np.random.uniform(-10, 10)
            img_array = cv2.convertScaleAbs(img_array, alpha=alpha, beta=beta)
        
        return Image.fromarray(img_array)
    
    def validate(self) -> bool:
        return len(self.samples) > 0


# ============================================================================
# فئات التنسيقات (Formatters)
# ============================================================================

class BaseFormatter:
    """الفئة الأساسية لتنسيقات التصدير."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def format(self, samples: List[Dict], split: str = 'train'):
        raise NotImplementedError


class LMDBFormatter(BaseFormatter):
    """تنسيق LMDB للتدريب السريع."""
    
    def format(self, samples: List[Dict], split: str = 'train'):
        output_path = self.output_dir / f'{split}.lmdb'
        
        # حذف القديم
        if output_path.exists():
            shutil.rmtree(output_path)
        
        env = lmdb.open(str(output_path), map_size=LMDB_MAP_SIZE)
        
        with env.begin(write=True) as txn:
            for idx, sample in enumerate(tqdm(samples, desc=f"💾 LMDB {split}")):
                # قراءة الصورة
                with open(sample['image_path'], 'rb') as f:
                    image_bytes = f.read()
                
                # تخزين
                key = f"{idx:08d}".encode()
                value = pickle.dumps({
                    'image': image_bytes,
                    'text': sample['text'],
                    'source': sample.get('source', 'unknown')
                })
                txn.put(key, value)
            
            # تخزين العدد
            txn.put(b'__len__', str(len(samples)).encode())
        
        env.close()
        print(f"✅ LMDB {split}: {len(samples)} عينة → {output_path}")
        return output_path


class TSVFormatter(BaseFormatter):
    """تنسيق TSV بسيط."""
    
    def format(self, samples: List[Dict], split: str = 'train'):
        output_path = self.output_dir / f'{split}.tsv'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("image_path\ttext\n")
            for sample in samples:
                f.write(f"{sample['image_path']}\t{sample['text']}\n")
        
        print(f"✅ TSV {split}: {len(samples)} عينة → {output_path}")
        return output_path


class JSONLFormatter(BaseFormatter):
    """تنسيق JSON Lines."""
    
    def format(self, samples: List[Dict], split: str = 'train'):
        output_path = self.output_dir / f'{split}.jsonl'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                json.dump(sample, f, ensure_ascii=False)
                f.write('\n')
        
        print(f"✅ JSONL {split}: {len(samples)} عينة → {output_path}")
        return output_path


class HuggingFaceFormatter(BaseFormatter):
    """تنسيق HuggingFace Dataset."""
    
    def format(self, samples: List[Dict], split: str = 'train'):
        try:
            from datasets import Dataset, Features, Value, Image as HFImage
        except ImportError:
            raise ImportError("datasets مطلوب. ثبته: pip install datasets")
        
        # تحويل الصور
        images = []
        texts = []
        sources = []
        
        for sample in tqdm(samples, desc=f"🤗 HF {split}"):
            img = Image.open(sample['image_path']).convert('RGB')
            images.append(img)
            texts.append(sample['text'])
            sources.append(sample.get('source', 'unknown'))
        
        dataset = Dataset.from_dict({
            'image': images,
            'text': texts,
            'source': sources
        })
        
        output_path = self.output_dir / f'{split}_hf'
        dataset.save_to_disk(str(output_path))
        
        print(f"✅ HF Dataset {split}: {len(samples)} عينة → {output_path}")
        return output_path


class FolderFormatter(BaseFormatter):
    """نسخ الصور إلى مجلد منظم."""
    
    def format(self, samples: List[Dict], split: str = 'train'):
        split_dir = self.output_dir / split
        images_dir = split_dir / 'images'
        images_dir.mkdir(parents=True, exist_ok=True)
        
        labels_file = split_dir / 'labels.txt'
        
        with open(labels_file, 'w', encoding='utf-8') as f:
            for idx, sample in enumerate(tqdm(samples, desc=f"📁 {split}")):
                # نسخ الصورة
                src = Path(sample['image_path'])
                dst = images_dir / f"{idx:08d}{src.suffix}"
                shutil.copy2(src, dst)
                
                # كتابة التسمية
                f.write(f"{dst.name}\t{sample['text']}\n")
        
        print(f"✅ Folder {split}: {len(samples)} عينة → {split_dir}")
        return split_dir


# ============================================================================
# معالج التقسيم
# ============================================================================

def split_dataset(samples: List[Dict], 
                  train_ratio: float = 0.8,
                  val_ratio: float = 0.1,
                  test_ratio: float = 0.1,
                  seed: int = 42) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """تقسيم البيانات."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "المجموع يجب أن يكون 1.0"
    
    np.random.seed(seed)
    indices = np.random.permutation(len(samples))
    
    n = len(samples)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]
    
    train_samples = [samples[i] for i in train_idx]
    val_samples = [samples[i] for i in val_idx]
    test_samples = [samples[i] for i in test_idx]
    
    return train_samples, val_samples, test_samples


# ============================================================================
# الدالة الرئيسية
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="إعداد بيانات التدريب لنماذج HTR/OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  # من مجلد صور
  python prepare_htr_dataset.py --input-dir ./images --labels labels.txt --output-dir ./dataset
  
  # من PDF
  python prepare_htr_dataset.py --pdf document.pdf --output-dir ./dataset --dpi 300
  
  # من mobile_review
  python prepare_htr_dataset.py --mobile-review corrections.json --output-dir ./dataset
  
  # توليد صناعي
  python prepare_htr_dataset.py --synthetic --corpus corpus.txt --fonts-dir ./fonts --num-samples 10000
        """
    )
    
    # مصادر البيانات
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--input-dir', type=Path, help='مجلد الصور')
    source_group.add_argument('--pdf', type=Path, help='ملف PDF')
    source_group.add_argument('--mobile-review', type=Path, help='تصدير mobile_review JSON')
    source_group.add_argument('--synthetic', action='store_true', help='توليد بيانات صناعية')
    
    # معلمات مشتركة
    parser.add_argument('--labels', type=Path, help='ملف التسميات (مع --input-dir)')
    parser.add_argument('--output-dir', type=Path, required=True, help='مجلد الإخراج')
    parser.add_argument('--format', choices=SUPPORTED_FORMATS, default='lmdb',
                       help='تنسيق الإخراج')
    parser.add_argument('--train-split', type=float, default=0.8)
    parser.add_argument('--val-split', type=float, default=0.1)
    parser.add_argument('--test-split', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    
    # معلمات PDF
    parser.add_argument('--dpi', type=int, default=300)
    parser.add_argument('--lang', type=str, default='ar')
    
    # معلمات mobile_review
    parser.add_argument('--min-confidence', type=float, default=0.7)
    parser.add_argument('--auto-include-high-confidence', action='store_true', default=True)
    
    # معلمات البيانات الصناعية
    parser.add_argument('--corpus', type=Path, help='ملف النصوص للتوليد الصناعي')
    parser.add_argument('--fonts-dir', type=Path, help='مجلد الخطوط')
    parser.add_argument('--num-samples', type=int, default=10000)
    parser.add_argument('--augmentations', nargs='+', 
                       default=['rotation', 'noise', 'blur', 'contrast'])
    
    args = parser.parse_args()
    
    # تحميل البيانات
    print("=" * 60)
    print("🚀 OmniFile HTR Dataset Preparer")
    print("=" * 60)
    
    if args.input_dir:
        assert args.labels, "--labels مطلوب مع --input-dir"
        loader = ImageFolderLoader(args.input_dir, args.labels)
    elif args.pdf:
        loader = PDFLoader(args.pdf, dpi=args.dpi, output_dir=args.output_dir, lang=args.lang)
    elif args.mobile_review:
        loader = MobileReviewLoader(
            args.mobile_review, 
            min_confidence=args.min_confidence,
            auto_include_high_confidence=args.auto_include_high_confidence
        )
    elif args.synthetic:
        assert args.corpus and args.fonts_dir, "--corpus و --fonts-dir مطلوبان"
        loader = SyntheticDataGenerator(
            args.corpus, args.fonts_dir,
            num_samples=args.num_samples,
            lang=args.lang,
            augmentations=args.augmentations,
            output_dir=args.output_dir
        )
    
    # التحميل والتحقق
    samples = loader.load()
    if not loader.validate():
        print("❌ فشل التحقق من البيانات!")
        return 1
    
    # تصدير mobile_review split إن وجد
    if isinstance(loader, MobileReviewLoader):
        loader.export_split(args.output_dir / 'review_split')
    
    # التقسيم
    print("\n📊 تقسيم البيانات...")
    train, val, test = split_dataset(
        samples, 
        args.train_split, 
        args.val_split, 
        args.test_split,
        args.seed
    )
    print(f"   Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
    
    # التنسيق
    formatters = {
        'lmdb': LMDBFormatter,
        'tsv': TSVFormatter,
        'jsonl': JSONLFormatter,
        'hf_dataset': HuggingFaceFormatter,
        'folder': FolderFormatter
    }
    
    formatter = formatters[args.format](args.output_dir)
    
    print(f"\n💾 تصدير بتنسيق: {args.format}")
    formatter.format(train, 'train')
    formatter.format(val, 'val')
    formatter.format(test, 'test')
    
    # إنشاء ملف الإعدادات
    config = {
        'format': args.format,
        'num_samples': len(samples),
        'splits': {
            'train': len(train),
            'val': len(val),
            'test': len(test)
        },
        'source': loader.__class__.__name__
    }
    
    with open(args.output_dir / 'dataset_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ تم الانتهاء!")
    print(f"📁 الإخراج: {args.output_dir}")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    exit(main())
