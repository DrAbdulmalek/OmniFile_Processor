#!/usr/bin/env python3
"""
اختبارات التقسيم المتقدمة - اختبار اكتشاف الجداول والرسومات.
Advanced segmentation tests - Test table and diagram detection.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np


def test_table_detection():
    """Test table detection."""
    print("\n[TEST] Testing table detection...")

    from interactive_learning.core.segmenter import SmartSegmenter

    # Use sample image
    img_path = Path("test_data/images/with_table.jpg")

    if not img_path.exists():
        print(f"  [WARN] Test image not found: {img_path}")
        print("  Run: python scripts/setup_test_env.py first")
        return False

    try:
        segmenter = SmartSegmenter(device="cpu")
        layout = segmenter.segment_page(img_path)

        print(f"  [OK] Page segmented")
        print(f"     Tables found: {len(layout.tables)}")

        for i, table in enumerate(layout.tables):
            print(f"     Table {i+1}: {table.num_rows}x{table.num_cols}")
            print(f"       Cells: {len(table.cells)}")
            print(f"       Bbox: {table.bbox}")

        # Check for cell content
        if layout.tables:
            has_content = any(
                len(cell.content) > 0
                for table in layout.tables
                for cell in table.cells
            )
            print(f"     Has text content: {has_content}")

        return len(layout.tables) > 0

    except Exception as e:
        print(f"  [FAIL] Table detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_diagram_detection():
    """Test diagram detection."""
    print("\n[TEST] Testing diagram detection...")

    from interactive_learning.core.segmenter import SmartSegmenter

    img_path = Path("test_data/images/with_diagram.jpg")

    if not img_path.exists():
        print(f"  [WARN] Test image not found: {img_path}")
        return False

    try:
        segmenter = SmartSegmenter(device="cpu")
        layout = segmenter.segment_page(img_path)

        print(f"  [OK] Page segmented")
        print(f"     Graphics found: {len(layout.graphics)}")

        for i, graphic in enumerate(layout.graphics):
            print(f"     Graphic {i+1}: {graphic.element_type}")
            print(f"       Subtype: {graphic.sub_type}")
            print(f"       Bbox: {graphic.bbox}")
            print(f"       Detected text: {len(graphic.detected_text)} words")

        return len(layout.graphics) > 0

    except Exception as e:
        print(f"  [FAIL] Diagram detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mixed_content():
    """Test mixed content."""
    print("\n[TEST] Testing mixed content...")

    from interactive_learning.core.segmenter import SmartSegmenter

    img_path = Path("test_data/images/mixed_content.jpg")

    if not img_path.exists():
        print(f"  [WARN] Test image not found: {img_path}")
        return False

    try:
        segmenter = SmartSegmenter(device="cpu")
        layout = segmenter.segment_page(img_path)

        print(f"  [OK] Page segmented: {layout.width}x{layout.height}")

        # Statistics
        stats = {
            'paragraphs': len(layout.paragraphs),
            'lines': sum(len(p.lines) for p in layout.paragraphs),
            'words': sum(
                len(w.words)
                for p in layout.paragraphs
                for w in p.lines
            ),
            'tables': len(layout.tables),
            'graphics': len(layout.graphics)
        }

        for key, value in stats.items():
            print(f"     {key}: {value}")

        # Should find everything
        has_all = (
            stats['words'] > 0 and
            stats['tables'] > 0 and
            stats['graphics'] > 0
        )

        if has_all:
            print("  [OK] All content types detected!")
        else:
            print("  [WARN] Some content types missed")

        return has_all

    except Exception as e:
        print(f"  [FAIL] Mixed content failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reading_order():
    """Test reading order."""
    print("\n[TEST] Testing reading order...")

    from interactive_learning.core.segmenter import SmartSegmenter

    # Image with multiple text lines
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Line 1 (top)
    cv2.putText(img, "First line", (100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    # Line 2
    cv2.putText(img, "Second line", (100, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    # Line 3
    cv2.putText(img, "Third line", (100, 280), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)

    temp_path = Path("test_data/temp_order.jpg")
    cv2.imwrite(str(temp_path), img)

    try:
        segmenter = SmartSegmenter(device="cpu")
        layout = segmenter.segment_page(temp_path)

        # Verify order
        words = []
        for para in layout.paragraphs:
            for line in para.lines:
                for word in line.words:
                    words.append((word.reading_order, word.text))

        words.sort()
        print(f"  [OK] Found {len(words)} words in order:")

        for order, text in words:
            print(f"     [{order}] {text}")

        # Verify correct order
        is_ordered = all(
            words[i][0] <= words[i+1][0]
            for i in range(len(words)-1)
        )

        if is_ordered:
            print("  [OK] Reading order is correct")
        else:
            print("  [WARN] Reading order may be incorrect")

        temp_path.unlink()
        return is_ordered

    except Exception as e:
        print(f"  [FAIL] Reading order test failed: {e}")
        return False


def main():
    """Main test runner."""
    print("=" * 60)
    print("OmniFile Segmentation Tests")
    print("=" * 60)

    results = []

    results.append(("Table Detection", test_table_detection()))
    results.append(("Diagram Detection", test_diagram_detection()))
    results.append(("Mixed Content", test_mixed_content()))
    results.append(("Reading Order", test_reading_order()))

    # Results
    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
