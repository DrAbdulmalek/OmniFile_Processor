#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_arabic_htr_dataset.py
=====================================

Generate synthetic Arabic handwriting training data for quick start.

Usage:
    python scripts/generate_arabic_htr_dataset.py \
        --output-dir ./data/arabic_htr_synthetic \
        --num-samples 5000
"""

import argparse
import json
import random
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, **kw: x


# ============================================================================
# Arabic training texts
# ============================================================================

ARABIC_TEXTS = [
    "بسم الله الرحمن الرحيم",
    "الحمد لله رب العالمين",
    "السلام عليكم ورحمة الله وبركاته",
    "كيف حالك اليوم",
    "العلم نور والجهل ظلام",
    "الصبر مفتاح الفرج",
    "من جد وجد ومن زرع حصد",
    "الوقت كالسيف إن لم تقطعه قطعك",
    "خير الكلام ما قل ودل",
    "الإسلام دين الرحمة",
    "طلب العلم فريضة على كل مسلم",
    "العلم في الصغر كالنقش على الحجر",
    "إنما العلم بالتعلم",
    "وفي أنفسكم أفلا تبصرون",
    "اقرأ باسم ربك الذي خلق",
    "Actions speak louder than words",
    "The quick brown fox jumps over the lazy dog",
    "Hello World",
    "Machine Learning",
    "Natural Language Processing",
    "1234567890",
    "٠١٢٣٤٥٦٧٨٩",
]

ARABIC_CHARS = "ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأؤإئةى"


# ============================================================================
# Data Generator
# ============================================================================

class ArabicHandwritingGenerator:
    """Synthetic Arabic handwriting generator."""

    def __init__(
        self,
        fonts_dir: Path = None,
        image_size: tuple = (400, 100),
        augment: bool = True
    ):
        self.image_size = image_size
        self.augment = augment

        # Load fonts
        self.fonts = self._load_fonts(fonts_dir)

        # Background colors
        self.backgrounds = [
            (255, 255, 255),   # white
            (250, 248, 245),   # light beige
            (245, 245, 245),   # light gray
        ]

    def _load_fonts(self, fonts_dir: Path = None) -> List[ImageFont.FreeTypeFont]:
        """Load Arabic fonts."""
        fonts = []

        if fonts_dir and fonts_dir.exists():
            for font_file in fonts_dir.glob("*.ttf"):
                try:
                    font = ImageFont.truetype(str(font_file), size=random.randint(28, 40))
                    fonts.append(font)
                except Exception:
                    pass

        # Default font if none found
        if not fonts:
            try:
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                ]
                for fp in font_paths:
                    try:
                        font = ImageFont.truetype(fp, 32)
                        fonts.append(font)
                        break
                    except (OSError, IOError):
                        continue
            except Exception:
                fonts.append(ImageFont.load_default())

        return fonts

    def generate(self, text: str = None) -> tuple:
        """
        Generate a handwriting image.

        Returns:
            (image, text)
        """
        if text is None:
            text = random.choice(ARABIC_TEXTS)

        # Create image
        bg_color = random.choice(self.backgrounds)
        image = Image.new('RGB', self.image_size, bg_color)
        draw = ImageDraw.Draw(image)

        # Choose font
        font = random.choice(self.fonts)

        # Calculate position (center)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except TypeError:
            text_width = len(text) * 15
            text_height = 30

        x = (self.image_size[0] - text_width) // 2
        y = (self.image_size[1] - text_height) // 2

        # Ink color (varied)
        ink_colors = [
            (0, 0, 0),       # black
            (20, 20, 20),    # dark gray
            (0, 0, 40),      # dark blue
            (60, 30, 0),     # brown
        ]
        ink = random.choice(ink_colors)

        # Draw text
        draw.text((x, y), text, font=font, fill=ink)

        # Augmentations (simulate handwriting)
        if self.augment:
            image = self._augment(image)

        return image, text

    def _augment(self, image: Image.Image) -> Image.Image:
        """Apply realistic augmentations."""
        img_array = np.array(image)

        # 1. Light noise
        if random.random() < 0.7:
            noise = np.random.normal(0, 5, img_array.shape).astype(np.int16)
            img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # 2. Light rotation
        if random.random() < 0.5:
            angle = random.uniform(-2, 2)
            from PIL import ImageFilter
            image = Image.fromarray(img_array).rotate(angle, fillcolor=(255, 255, 255))
            img_array = np.array(image)

        # 3. Contrast change
        if random.random() < 0.5:
            factor = random.uniform(0.8, 1.2)
            img_array = np.clip(img_array.astype(np.float32) * factor, 0, 255).astype(np.uint8)

        # 4. Light blur
        if random.random() < 0.3:
            from PIL import ImageFilter
            image = Image.fromarray(img_array).filter(ImageFilter.GaussianBlur(radius=0.5))
            img_array = np.array(image)

        return Image.fromarray(img_array)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Arabic handwriting data")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-samples", type=int, default=1000)
    parser.add_argument("--fonts-dir", type=Path, default=None)
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--test-split", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # Create directories
    output_dir = Path(args.output_dir)
    for split in ["train", "val", "test"]:
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)

    # Generator
    generator = ArabicHandwritingGenerator(fonts_dir=args.fonts_dir)

    # Splits
    splits = {
        "train": int(args.num_samples * args.train_split),
        "val": int(args.num_samples * args.val_split),
        "test": int(args.num_samples * args.test_split)
    }

    # Generate
    for split, count in splits.items():
        print(f"\nGenerating {split}: {count} samples...")

        labels = []

        for i in tqdm(range(count), desc=split):
            image, text = generator.generate()

            filename = f"{split}_{i:06d}.png"
            image.save(output_dir / split / "images" / filename)

            labels.append(f"{filename}\t{text}\n")

        # Save labels
        with open(output_dir / split / "labels.txt", "w", encoding="utf-8") as f:
            f.write("filename\ttext\n")
            f.writelines(labels)

    # Config
    config = {
        "num_samples": args.num_samples,
        "splits": splits,
        "seed": args.seed,
        "source": "synthetic"
    }

    with open(output_dir / "dataset_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nDone: {output_dir}")
    print(f"   Train: {splits['train']}")
    print(f"   Val:   {splits['val']}")
    print(f"   Test:  {splits['test']}")


if __name__ == "__main__":
    main()
