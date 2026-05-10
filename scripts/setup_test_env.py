#!/usr/bin/env python3
"""
إعداد بيئة اختبار مصغرة مع بيانات نموذجية.
Setup minimal test environment with sample data.
"""

import os
import json
from pathlib import Path
import cv2
import numpy as np


def create_test_directories():
    """إنشاء هيكل المجلدات."""
    dirs = [
        "test_data/images",
        "test_data/corrections",
        "test_data/output",
        "test_data/models",
        "test_data/training_data",
        "test_logs",
    ]

    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] Created: {d}")


def generate_sample_images():
    """توليد صور نموذجية للاختبار."""

    samples = [
        # (filename, text, image_type)
        ("simple_text.jpg", "Hello World", "simple"),
        ("arabic_like.jpg", "مرحبا", "arabic"),  # will be simulated
        ("handwritten.jpg", "Test Word", "handwritten"),
        ("with_table.jpg", None, "table"),
        ("with_diagram.jpg", None, "diagram"),
        ("mixed_content.jpg", None, "mixed"),
    ]

    for filename, text, img_type in samples:
        filepath = Path("test_data/images") / filename

        if img_type == "simple":
            img = create_simple_image(text)
        elif img_type == "arabic":
            img = create_arabic_like_image(text)
        elif img_type == "handwritten":
            img = create_handwritten_like_image(text)
        elif img_type == "table":
            img = create_table_image()
        elif img_type == "diagram":
            img = create_diagram_image()
        elif img_type == "mixed":
            img = create_mixed_image()
        else:
            img = create_simple_image("Default")

        cv2.imwrite(str(filepath), img)
        print(f"  [*] Generated: {filename} ({img_type})")


def create_simple_image(text: str, width: int = 800, height: int = 200) -> np.ndarray:
    """Simple text image."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Black text
    cv2.putText(
        img, text,
        (50, height // 2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        2, (0, 0, 0), 3
    )

    return img


def create_arabic_like_image(text: str, width: int = 800, height: int = 200) -> np.ndarray:
    """Simulated Arabic text image (RTL)."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Simulate Arabic text: right to left
    # Use Latin characters as substitute for testing
    x_pos = width - 50

    for i, char in enumerate(text):
        cv2.putText(
            img, char,
            (x_pos - i * 60, height // 2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            2, (0, 0, 0), 3
        )

    # Line simulating Arabic baseline
    cv2.line(img, (50, height // 2 + 40), (width - 50, height // 2 + 40), (200, 200, 200), 1)

    return img


def create_handwritten_like_image(text: str, width: int = 800, height: int = 200) -> np.ndarray:
    """Simulated handwritten image."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Add light noise to background
    noise = np.random.normal(0, 5, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # "Handwritten" text - thinner and less regular
    base_y = height // 2 + 20
    x_pos = 50

    for char in text:
        # Position variation simulating handwriting
        y_offset = np.random.randint(-5, 5)
        angle = np.random.randint(-3, 3)

        # Draw character
        cv2.putText(
            img, char,
            (x_pos, base_y + y_offset),
            cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,  # handwriting-like font
            2.2, (50, 50, 50), 2  # dark gray
        )

        x_pos += 50 + np.random.randint(-5, 10)

    return img


def create_table_image(width: int = 800, height: int = 600) -> np.ndarray:
    """Image containing a table."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Title
    cv2.putText(
        img, "Sales Report 2024",
        (280, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2, (0, 0, 0), 2
    )

    # Table borders
    table_x, table_y = 100, 100
    table_w, table_h = 600, 400
    rows, cols = 5, 4

    cv2.rectangle(img, (table_x, table_y), (table_x + table_w, table_y + table_h), (0, 0, 0), 2)

    # Horizontal lines
    for i in range(1, rows):
        y = table_y + i * (table_h // rows)
        cv2.line(img, (table_x, y), (table_x + table_w, y), (0, 0, 0), 1)

    # Vertical lines
    for i in range(1, cols):
        x = table_x + i * (table_w // cols)
        cv2.line(img, (x, table_y), (x, table_y + table_h), (0, 0, 0), 1)

    # Table content
    headers = ["Month", "Sales", "Target", "Status"]
    data = [
        ["Jan", "15000", "14000", "Good"],
        ["Feb", "12000", "15000", "Low"],
        ["Mar", "18000", "16000", "Great"],
        ["Apr", "16000", "16000", "On Track"],
    ]

    # Draw text
    cell_h = table_h // rows
    cell_w = table_w // cols

    for j, header in enumerate(headers):
        x = table_x + j * cell_w + 20
        y = table_y + 30
        cv2.putText(img, header, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 150), 2)

    for i, row in enumerate(data):
        for j, cell in enumerate(row):
            x = table_x + j * cell_w + 20
            y = table_y + (i + 1) * cell_h + 35
            cv2.putText(img, cell, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    return img


def create_diagram_image(width: int = 800, height: int = 600) -> np.ndarray:
    """Image containing a box diagram."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Title
    cv2.putText(
        img, "Process Flow",
        (300, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.2, (0, 0, 0), 2
    )

    # Boxes
    boxes = [
        (300, 100, 500, 180, "Start", (200, 230, 200)),      # light green
        (300, 220, 500, 300, "Process", (200, 200, 230)),     # light blue
        (300, 340, 500, 420, "Decision", (230, 230, 200)),  # light yellow
        (150, 460, 350, 540, "Yes", (200, 230, 200)),         # green
        (450, 460, 650, 540, "No", (230, 200, 200)),          # red
    ]

    for x1, y1, x2, y2, text, color in boxes:
        # Draw box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, -1)  # fill
        cv2.rectangle(img, (x1, y1), (x2, y2), (100, 100, 100), 2)  # border

        # Text
        text_x = x1 + (x2 - x1) // 2 - len(text) * 10
        text_y = y1 + (y2 - y1) // 2 + 10
        cv2.putText(img, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    # Arrows
    # Start -> Process
    cv2.arrowedLine(img, (400, 180), (400, 220), (100, 100, 100), 2, tipLength=0.3)

    # Process -> Decision
    cv2.arrowedLine(img, (400, 300), (400, 340), (100, 100, 100), 2, tipLength=0.3)

    # Decision -> Yes
    cv2.arrowedLine(img, (350, 460), (250, 460), (100, 100, 100), 2, tipLength=0.3)
    cv2.putText(img, "Yes", (280, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 0), 1)

    # Decision -> No
    cv2.arrowedLine(img, (500, 460), (550, 460), (100, 100, 100), 2, tipLength=0.3)
    cv2.putText(img, "No", (520, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 0, 0), 1)

    return img


def create_mixed_image(width: int = 1000, height: int = 800) -> np.ndarray:
    """Mixed content image with all elements."""
    img = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Text at top
    cv2.putText(img, "Quarterly Report", (350, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    # Text paragraph
    cv2.putText(img, "This report shows the performance", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(img, "of our OCR system in Q1 2024.", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

    # Small table
    table_x, table_y = 50, 200
    cv2.rectangle(img, (table_x, table_y), (table_x + 400, table_y + 200), (0, 0, 0), 2)
    cv2.line(img, (table_x + 133, table_y), (table_x + 133, table_y + 200), (0, 0, 0), 1)
    cv2.line(img, (table_x + 266, table_y), (table_x + 266, table_y + 200), (0, 0, 0), 1)
    cv2.line(img, (table_x, table_y + 50), (table_x + 400, table_y + 50), (0, 0, 0), 1)

    cv2.putText(img, "Metric", (60, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 150), 1)
    cv2.putText(img, "Value", (200, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 150), 1)
    cv2.putText(img, "Status", (340, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 150), 1)

    cv2.putText(img, "Accuracy", (60, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "95%", (210, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    cv2.putText(img, "Good", (340, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 150, 0), 1)

    # Small box diagram
    cv2.rectangle(img, (500, 200), (700, 280), (200, 230, 200), -1)
    cv2.rectangle(img, (500, 200), (700, 280), (100, 100, 100), 2)
    cv2.putText(img, "Export", (560, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    cv2.rectangle(img, (750, 200), (950, 280), (230, 200, 200), -1)
    cv2.rectangle(img, (750, 200), (950, 280), (100, 100, 100), 2)
    cv2.putText(img, "Cancel", (810, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    # Arrow
    cv2.arrowedLine(img, (700, 240), (750, 240), (100, 100, 100), 2, tipLength=0.3)

    # Additional text
    cv2.putText(img, "Conclusion: System performs well", (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "with room for improvement in", (50, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)
    cv2.putText(img, "handwritten documents.", (50, 560), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 1)

    return img


def create_config_file():
    """Create test configuration file."""
    config = {
        "model": {
            "base_model": "microsoft/trocr-base-handwritten",
            "device": "cpu",
            "fallback_model": "microsoft/trocr-small-printed"
        },
        "processing": {
            "confidence_threshold": 0.7,
            "min_word_length": 2,
            "language": "auto"
        },
        "learning": {
            "auto_train": False,
            "min_corrections": 5,
            "learning_rate": 5e-5
        },
        "output": {
            "formats": ["html", "json"],
            "preserve_layout": True,
            "include_background": True
        },
        "paths": {
            "test_data": "test_data",
            "output": "test_data/output",
            "models": "test_data/models"
        }
    }

    with open("test_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("  [*] Created: test_config.json")


if __name__ == "__main__":
    print("=" * 50)
    print("Setting up test environment")
    print("=" * 50)

    create_test_directories()
    generate_sample_images()
    create_config_file()

    print("\n" + "=" * 50)
    print("Test environment ready!")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Run: python scripts/test_basic.py")
    print("  2. Run: python scripts/test_segmentation.py")
    print("  3. Run: python scripts/test_interactive.py")
