#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_synthetic_data.py
==========================

توليد بيانات صناعية للتدريب على التعرف على النصوص اليدوية.

يدعم:
- توليد نصوص عربية بخطوط متنوعة
- تعزيزات واقعية (ضوضاء، تشويه، دوران)
- تقليد خصائص الكتابة اليدوية
- دعم SynthTIGER للتوليد المتقدم

الاستخدام:
    python generate_synthetic_data.py \
        --corpus ./corpus_arabic.txt \
        --fonts-dir ./fonts/arabic/ \
        --output-dir ./synthetic \
        --num-samples 100000

المؤلف: Dr. Abdulmalek Al-husseini
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from tqdm import tqdm

# ============================================================================
# إعدادات التسجيل
# ============================================================================

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# مولد النصوص
# ============================================================================

class TextGenerator:
    """مولد نصوص عشوائية من corpus."""
    
    def __init__(self, corpus_path: Path):
        with open(corpus_path, 'r', encoding='utf-8') as f:
            self.texts = [line.strip() for line in f if line.strip()]
        
        # بناء نموذج n-gram بسيط
        self.char_freq = self._build_char_model()
        
        logger.info(f"📚 تم تحميل {len(self.texts)} نص")
    
    def _build_char_model(self) -> Dict[str, Dict[str, int]]:
        """بناء نموذج انتقال الأحرف."""
        transitions = defaultdict(lambda: defaultdict(int))
        
        for text in self.texts:
            for i in range(len(text) - 1):
                transitions[text[i]][text[i+1]] += 1
        
        return dict(transitions)
    
    def random_text(self, min_length: int = 5, max_length: int = 50) -> str:
        """توليد نص عشوائي."""
        # 80% من corpus، 20% توليد
        if random.random() < 0.8 and self.texts:
            text = random.choice(self.texts)
            # اقتطاع جزء عشوائي
            start = random.randint(0, max(0, len(text) - min_length))
            end = min(start + random.randint(min_length, max_length), len(text))
            return text[start:end].strip()
        
        # توليد بـ n-gram
        return self._generate_text(min_length, max_length)
    
    def _generate_text(self, min_length: int, max_length: int) -> str:
        """توليد نص باستخدام n-gram."""
        if not self.char_freq:
            return random.choice(self.texts)[:max_length] if self.texts else "نص عينة"
        
        # اختيار حرف بداية عشوائي
        current = random.choice(list(self.char_freq.keys()))
        result = [current]
        
        for _ in range(max_length - 1):
            if current not in self.char_freq:
                break
            
            next_chars = self.char_freq[current]
            if not next_chars:
                break
            
            # weighted random
            chars, weights = zip(*next_chars.items())
            current = random.choices(chars, weights=weights)[0]
            result.append(current)
            
            if len(result) >= min_length and random.random() < 0.1:
                break
        
        return ''.join(result)


# ============================================================================
# محمل الخطوط
# ============================================================================

class FontLoader:
    """محمل وإدارة الخطوط."""
    
    def __init__(self, fonts_dir: Path):
        self.fonts_dir = Path(fonts_dir)
        self.fonts = self._load_fonts()
        logger.info(f"🔤 تم تحميل {len(self.fonts)} خط")
    
    def _load_fonts(self) -> List[Path]:
        """جمع جميع ملفات الخطوط."""
        extensions = ['.ttf', '.otf', '.ttc', '.woff', '.woff2']
        fonts = []
        
        for ext in extensions:
            fonts.extend(self.fonts_dir.glob(f'**/*{ext}'))
        
        return sorted(fonts)
    
    def random_font(self, size_range: Tuple[int, int] = (24, 48)) -> Tuple[ImageFont.FreeTypeFont, int]:
        """اختيار خط وحجم عشوائيين."""
        font_path = random.choice(self.fonts)
        size = random.randint(*size_range)
        
        try:
            font = ImageFont.truetype(str(font_path), size)
            return font, size
        except:
            # fallback
            return ImageFont.load_default(), size
    
    def get_font_by_name(self, name: str, size: int = 32) -> Optional[ImageFont.FreeTypeFont]:
        """الحصول على خط باسم محدد."""
        for font_path in self.fonts:
            if name.lower() in font_path.stem.lower():
                return ImageFont.truetype(str(font_path), size)
        return None


# ============================================================================
# تعزيزات واقعية
# ============================================================================

class HandwritingAugmenter:
    """تطبيق تعزيزات تقلد الكتابة اليدوية."""
    
    def __init__(self):
        self.augmentations = [
            self.add_noise,
            self.add_blur,
            self.adjust_contrast,
            self.add_distortion,
            self.add_background_texture,
            self.add_ink_bleed,
            self.add_skew,
            self.add_compression_artifacts,
        ]
    
    def apply(self, image: Image.Image, intensity: float = 1.0) -> Image.Image:
        """تطبيق تعزيزات عشوائية."""
        img = image.copy()
        
        # تطبيق 2-5 تعزيزات عشوائية
        num_augs = random.randint(2, 5)
        selected = random.sample(self.augmentations, num_augs)
        
        for aug in selected:
            if random.random() < intensity:
                img = aug(img)
        
        return img
    
    def add_noise(self, image: Image.Image) -> Image.Image:
        """إضافة ضوضاء."""
        img_array = np.array(image)
        noise = np.random.normal(0, random.randint(5, 20), img_array.shape).astype(np.int16)
        noisy = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy)
    
    def add_blur(self, image: Image.Image) -> Image.Image:
        """إضافة ضبابية."""
        radius = random.uniform(0.3, 1.5)
        return image.filter(ImageFilter.GaussianBlur(radius))
    
    def adjust_contrast(self, image: Image.Image) -> Image.Image:
        """تعديل التباين."""
        factor = random.uniform(0.7, 1.3)
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    def add_distortion(self, image: Image.Image) -> Image.Image:
        """إضافة تشويه هندسي."""
        img_array = np.array(image)
        h, w = img_array.shape[:2]
        
        # تشويه مرن بسيط
        dx = random.randint(-w//20, w//20)
        dy = random.randint(-h//20, h//20)
        
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        distorted = cv2.warpAffine(
            img_array, M, (w, h),
            borderMode=cv2.BORDER_REPLICATE
        )
        
        return Image.fromarray(distorted)
    
    def add_background_texture(self, image: Image.Image) -> Image.Image:
        """إضافة نسيج خلفية (ورق)."""
        img_array = np.array(image).astype(np.float32)
        h, w = img_array.shape[:2]
        
        # نسيج ورق بسيط
        texture = np.random.normal(240, 10, (h, w, 3)).astype(np.float32)
        
        # مزج
        alpha = random.uniform(0.85, 0.98)
        blended = img_array * alpha + texture * (1 - alpha)
        
        return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))
    
    def add_ink_bleed(self, image: Image.Image) -> Image.Image:
        """تقليد انتشار الحبر."""
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # تمديد الحبر الداكن
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(255 - gray, kernel, iterations=random.randint(1, 2))
        
        # مزج
        result = 255 - (dilated * random.uniform(0.3, 0.7)).astype(np.uint8)
        result_rgb = cv2.cvtColor(result, cv2.COLOR_GRAY2RGB)
        
        return Image.fromarray(result_rgb)
    
    def add_skew(self, image: Image.Image) -> Image.Image:
        """إضافة ميلان."""
        angle = random.uniform(-3, 3)
        return image.rotate(angle, fillcolor=(255, 255, 255), expand=True)
    
    def add_compression_artifacts(self, image: Image.Image) -> Image.Image:
        """تقليد ضغط JPEG."""
        import io
        quality = random.randint(40, 85)
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        
        return Image.open(buffer)


# ============================================================================
# مولد الصور
# ============================================================================

class SyntheticImageGenerator:
    """مولد الصور الاصطناعية."""
    
    def __init__(
        self,
        text_generator: TextGenerator,
        font_loader: FontLoader,
        augmenter: HandwritingAugmenter
    ):
        self.text_generator = text_generator
        self.font_loader = font_loader
        self.augmenter = augmenter
        
        # ألوان الحبر
        self.ink_colors = [
            (0, 0, 0),        # أسود
            (20, 20, 20),     # رمادي داكن
            (0, 0, 40),       # أزرق داكن
            (40, 0, 0),       # بني داكن
        ]
    
    def generate(
        self,
        text: Optional[str] = None,
        image_size: Optional[Tuple[int, int]] = None,
        apply_augmentation: bool = True
    ) -> Tuple[Image.Image, str]:
        """
        توليد صورة اصطناعية.
        
        Returns:
            (صورة, النص)
        """
        # توليد نص إن لم يُزود
        if text is None:
            text = self.text_generator.random_text()
        
        # إعداد الصورة
        font, font_size = self.font_loader.random_font()
        
        # حساب الحجم
        dummy = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy)
        
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except:
            text_w, text_h = len(text) * font_size, font_size
        
        # هوامش
        padding_x = random.randint(20, 60)
        padding_y = random.randint(15, 40)
        
        if image_size is None:
            w = text_w + padding_x * 2
            h = text_h + padding_y * 2
        else:
            w, h = image_size
        
        # إنشاء الصورة
        bg_color = (255, 255, 255)
        img = Image.new('RGB', (w, h), bg_color)
        draw = ImageDraw.Draw(img)
        
        # لون الحبر
        ink_color = random.choice(self.ink_colors)
        
        # موضع النص
        x = padding_x
        y = (h - text_h) // 2
        
        # رسم النص
        draw.text((x, y), text, font=font, fill=ink_color)
        
        # تعزيزات
        if apply_augmentation:
            img = self.augmenter.apply(img)
        
        return img, text


# ============================================================================
# مولد بيانات SynthTIGER (اختياري)
# ============================================================================

class SynthTigerGenerator:
    """
    مولد باستخدام SynthTIGER للتوليد المتقدم.
    يتطلب: pip install synthtiger
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.available = self._check_synthtiger()
    
    def _check_synthtiger(self) -> bool:
        """التحقق من توفر SynthTIGER."""
        try:
            import synthtiger
            return True
        except ImportError:
            logger.warning("⚠️  SynthTIGER غير مثبت. استخدم: pip install synthtiger")
            return False
    
    def generate_batch(
        self,
        output_dir: Path,
        num_samples: int,
        corpus_path: Path
    ) -> List[Dict]:
        """توليد دفعة باستخدام SynthTIGER."""
        if not self.available:
            raise RuntimeError("SynthTIGER غير متوفر")
        
        from synthtiger import main
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # إنشاء إعدادات مؤقتة
        config = self._create_config(corpus_path, output_dir)
        
        # تشغيل SynthTIGER
        main(
            config_path=str(config),
            output=str(output_dir / 'images'),
            count=num_samples,
            worker=4
        )
        
        # قراءة النتائج
        results = []
        for img_path in sorted((output_dir / 'images').glob('*.jpg')):
            gt_path = img_path.with_suffix('.txt')
            if gt_path.exists():
                with open(gt_path, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                
                results.append({
                    'image_path': str(img_path),
                    'text': text
                })
        
        return results
    
    def _create_config(self, corpus_path: Path, output_dir: Path) -> Path:
        """إنشاء إعدادات SynthTIGER."""
        config = {
            'name': 'SynthTiger',
            'workflow': [
                {'name': 'text', 'corpus': str(corpus_path)},
                {'name': 'color'},
                {'name': 'transform'},
                {'name': 'texture'},
                {'name': 'colormap'},
                {'name': 'image'}
            ]
        }
        
        config_path = output_dir / 'synthtiger_config.yaml'
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        return config_path


# ============================================================================
# المولد الرئيسي
# ============================================================================

class SyntheticDatasetGenerator:
    """منسق توليد مجموعات البيانات الاصطناعية."""
    
    def __init__(
        self,
        corpus_path: Path,
        fonts_dir: Path,
        output_dir: Path,
        use_synthtiger: bool = False
    ):
        self.corpus_path = Path(corpus_path)
        self.fonts_dir = Path(fonts_dir)
        self.output_dir = Path(output_dir)
        
        # المكونات
        self.text_gen = TextGenerator(self.corpus_path)
        self.font_loader = FontLoader(self.fonts_dir)
        self.augmenter = HandwritingAugmenter()
        self.image_gen = SyntheticImageGenerator(
            self.text_gen, self.font_loader, self.augmenter
        )
        
        # SynthTIGER اختياري
        self.synthtiger = SynthTigerGenerator() if use_synthtiger else None
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        num_samples: int,
        splits: Dict[str, float] = None,
        save_metadata: bool = True
    ) -> Dict[str, Path]:
        """
        توليد مجموعة بيانات كاملة.
        
        Args:
            num_samples: عدد العينات الإجمالي
            splits: تقسيم train/val/test
            save_metadata: حفظ ملفات التعريف
        
        Returns:
            مسارات المجلدات المنشأة
        """
        if splits is None:
            splits = {'train': 0.8, 'val': 0.1, 'test': 0.1}
        
        # حساب الأعداد
        split_counts = {
            name: int(num_samples * ratio)
            for name, ratio in splits.items()
        }
        
        # ضبط العدد الإجمالي
        total = sum(split_counts.values())
        if total < num_samples:
            split_counts['train'] += num_samples - total
        
        # توليد كل split
        results = {}
        
        for split_name, count in split_counts.items():
            split_dir = self.output_dir / split_name
            split_dir.mkdir(exist_ok=True)
            
            images_dir = split_dir / 'images'
            images_dir.mkdir(exist_ok=True)
            
            logger.info(f"\n🎨 توليد {split_name}: {count} عينة")
            
            metadata = []
            
            for i in tqdm(range(count), desc=f"  {split_name}"):
                # توليد
                image, text = self.image_gen.generate()
                
                # حفظ
                img_filename = f"{split_name}_{i:06d}.png"
                img_path = images_dir / img_filename
                
                image.save(img_path, 'PNG')
                
                metadata.append({
                    'filename': img_filename,
                    'text': text,
                    'width': image.width,
                    'height': image.height
                })
            
            # حفظ labels.txt
            with open(split_dir / 'labels.txt', 'w', encoding='utf-8') as f:
                f.write("filename\ttext\n")
                for item in metadata:
                    f.write(f"{item['filename']}\t{item['text']}\n")
            
            # حفظ metadata.json
            if save_metadata:
                with open(split_dir / 'metadata.json', 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            results[split_name] = split_dir
        
        # حفظ إعدادات التوليد
        config = {
            'num_samples': num_samples,
            'splits': splits,
            'num_fonts': len(self.font_loader.fonts),
            'augmentations': [a.__name__ for a in self.augmenter.augmentations]
        }
        
        with open(self.output_dir / 'generation_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        return results
    
    def generate_for_active_learning(
        self,
        num_samples: int,
        difficulty_distribution: Dict[str, float] = None
    ) -> Path:
        """
        توليد بيانات بمستويات صعوبة مختلفة.
        
        Args:
            num_samples: العدد الإجمالي
            difficulty_distribution: نسب easy/medium/hard
        
        Returns:
            مسار المجلد
        """
        if difficulty_distribution is None:
            difficulty_distribution = {'easy': 0.3, 'medium': 0.5, 'hard': 0.2}
        
        output_dir = self.output_dir / 'active_learning_pool'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        images_dir = output_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        
        metadata = []
        
        for difficulty, ratio in difficulty_distribution.items():
            count = int(num_samples * ratio)
            
            for i in range(count):
                # تعديل المعاملات حسب الصعوبة
                if difficulty == 'easy':
                    # خط واضح، خلفية بيضاء
                    text = self.text_gen.random_text(5, 20)
                    aug_intensity = 0.3
                elif difficulty == 'medium':
                    # بعض التعقيد
                    text = self.text_gen.random_text(10, 40)
                    aug_intensity = 0.6
                else:  # hard
                    # صعوبة عالية
                    text = self.text_gen.random_text(20, 100)
                    aug_intensity = 1.0
                
                image, _ = self.image_gen.generate(
                    text=text,
                    apply_augmentation=True
                )
                
                # تطبيق تعزيزات إضافية للصعوبة
                if difficulty == 'hard':
                    image = self._apply_hard_augmentations(image)
                
                img_path = images_dir / f"al_{difficulty}_{i:06d}.png"
                image.save(img_path)
                
                metadata.append({
                    'id': f"al_{difficulty}_{i:06d}",
                    'image_path': str(img_path),
                    'text': text,
                    'difficulty': difficulty,
                    'intended_use': 'active_learning'
                })
        
        with open(output_dir / 'pool_metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return output_dir
    
    def _apply_hard_augmentations(self, image: Image.Image) -> Image.Image:
        """تعزيزات إضافية للصعوبة العالية."""
        img = image
        
        # تشويه شديد
        img_array = np.array(img)
        h, w = img_array.shape[:2]
        
        # Perspective transform
        pts1 = np.float32([
            [0, 0], [w, 0], [0, h], [w, h]
        ])
        pts2 = np.float32([
            [random.randint(0, w//10), random.randint(0, h//10)],
            [w - random.randint(0, w//10), random.randint(0, h//10)],
            [random.randint(0, w//10), h - random.randint(0, h//10)],
            [w - random.randint(0, w//10), h - random.randint(0, h//10)]
        ])
        
        M = cv2.getPerspectiveTransform(pts1, pts2)
        warped = cv2.warpPerspective(img_array, M, (w, h))
        
        return Image.fromarray(warped)


# ============================================================================
# الدالة الرئيسية
# ============================================================================

from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description="توليد بيانات صناعية للتدريب")
    parser.add_argument('--corpus', type=Path, required=True,
                       help='ملف النصوص المصدر')
    parser.add_argument('--fonts-dir', type=Path, required=True,
                       help='مجلد الخطوط')
    parser.add_argument('--output-dir', type=Path, default='./synthetic_dataset',
                       help='مجلد الإخراج')
    parser.add_argument('--num-samples', type=int, default=10000,
                       help='عدد العينات')
    parser.add_argument('--train-split', type=float, default=0.8)
    parser.add_argument('--val-split', type=float, default=0.1)
    parser.add_argument('--test-split', type=float, default=0.1)
    parser.add_argument('--use-synthtiger', action='store_true',
                       help='استخدام SynthTIGER إن توفر')
    parser.add_argument('--for-active-learning', action='store_true',
                       help='توليد لـ Active Learning')
    parser.add_argument('--seed', type=int, default=42)
    
    args = parser.parse_args()
    
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # التحقق من المدخلات
    if not args.corpus.exists():
        logger.error(f"❌ ملف corpus غير موجود: {args.corpus}")
        return 1
    
    if not args.fonts_dir.exists():
        logger.error(f"❌ مجلد الخطوط غير موجود: {args.fonts_dir}")
        return 1
    
    # التوليد
    generator = SyntheticDatasetGenerator(
        args.corpus,
        args.fonts_dir,
        args.output_dir,
        use_synthtiger=args.use_synthtiger
    )
    
    if args.for_active_learning:
        output = generator.generate_for_active_learning(args.num_samples)
        logger.info(f"\n✅ تم توليد مجموعة Active Learning: {output}")
    else:
        results = generator.generate(
            num_samples=args.num_samples,
            splits={
                'train': args.train_split,
                'val': args.val_split,
                'test': args.test_split
            }
        )
        
        logger.info(f"\n{'='*60}")
        logger.info("✅ تم توليد مجموعة البيانات!")
        logger.info(f"{'='*60}")
        for name, path in results.items():
            logger.info(f"  📁 {name}: {path}")
    
    return 0


if __name__ == '__main__':
    exit(main())
