#!/usr/bin/env python3
"""
الاختبار الأساسي - التحقق من عمل المكونات الأساسية.
Basic tests - Verify core components work.
"""

import sys
from pathlib import Path

# Add path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np


def test_imports():
    """Test library imports."""
    print("\n[TEST] Testing imports...")

    try:
        from interactive_learning import InteractiveLearningSystem
        print("  [OK] InteractiveLearningSystem")
    except Exception as e:
        print(f"  [FAIL] InteractiveLearningSystem: {e}")
        return False

    try:
        from interactive_learning.core.segmenter import SmartSegmenter
        print("  [OK] SmartSegmenter")
    except Exception as e:
        print(f"  [FAIL] SmartSegmenter: {e}")
        return False

    try:
        from interactive_learning.learning.online_learner import OnlineLearner
        print("  [OK] OnlineLearner")
    except Exception as e:
        print(f"  [FAIL] OnlineLearner: {e}")
        return False

    try:
        from interactive_learning.rendering.html_renderer import HTMLRenderer
        print("  [OK] HTMLRenderer")
    except Exception as e:
        print(f"  [FAIL] HTMLRenderer: {e}")
        return False

    return True


def test_simple_segmentation():
    """Test simple segmentation."""
    print("\n[TEST] Testing simple segmentation...")

    from interactive_learning.core.segmenter import SmartSegmenter

    # Create simple image
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Test", (200, 120), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 4)

    # Save temporarily
    temp_path = Path("test_data/temp_simple.jpg")
    temp_path.parent.mkdir(exist_ok=True)
    cv2.imwrite(str(temp_path), img)

    try:
        segmenter = SmartSegmenter(device="cpu")
        layout = segmenter.segment_page(temp_path)

        print(f"  [OK] Segmented: {layout.width}x{layout.height}")
        print(f"     Paragraphs: {len(layout.paragraphs)}")

        total_words = sum(
            len(line.words)
            for para in layout.paragraphs
            for line in para.lines
        )
        print(f"     Words found: {total_words}")

        # Cleanup
        temp_path.unlink()
        return True

    except Exception as e:
        print(f"  [FAIL] Segmentation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_word_extraction():
    """Test word extraction."""
    print("\n[TEST] Testing word extraction...")

    from interactive_learning.core.segmenter import SmartSegmenter, WordBox

    img = np.ones((100, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Hi", (150, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)

    segmenter = SmartSegmenter(device="cpu")

    word = WordBox(
        id="test_1",
        text="Hi",
        confidence=0.9,
        bbox=(140, 20, 260, 90),
        baseline=(30, 80)
    )

    try:
        word_img = segmenter.extract_word_image(img, word)
        print(f"  [OK] Extracted word image: {word_img.shape}")
        return True
    except Exception as e:
        print(f"  [FAIL] Extraction failed: {e}")
        return False


def test_html_rendering():
    """Test HTML rendering."""
    print("\n[TEST] Testing HTML rendering...")

    from interactive_learning.rendering.html_renderer import HTMLRenderer
    from interactive_learning.core.segmenter import (
        PageLayout, ParagraphBox, LineBox, WordBox
    )

    # Create simple layout
    word = WordBox(
        id="w1",
        text="Hello",
        confidence=0.95,
        bbox=(100, 50, 200, 100),
        baseline=(60, 90),
        reading_order=0
    )

    line = LineBox(
        id="l1",
        words=[word],
        bbox=(100, 50, 200, 100),
        alignment="left"
    )

    para = ParagraphBox(
        id="p1",
        lines=[line],
        bbox=(100, 50, 200, 100)
    )

    layout = PageLayout(
        width=400,
        height=200,
        paragraphs=[para]
    )

    try:
        renderer = HTMLRenderer(interactive=False, rtl=False)

        output_path = Path("test_data/output/test_basic.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = renderer.render(layout, output_path=output_path)

        print(f"  [OK] HTML rendered: {len(html)} chars")
        print(f"     Saved to: {output_path}")

        # Verify content
        content = output_path.read_text()
        assert "Hello" in content
        print("  [OK] Content verified")

        return True

    except Exception as e:
        print(f"  [FAIL] Rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner."""
    print("=" * 60)
    print("OmniFile Basic Tests")
    print("=" * 60)

    results = []

    # 1. Imports
    results.append(("Imports", test_imports()))

    # 2. Simple segmentation
    results.append(("Simple Segmentation", test_simple_segmentation()))

    # 3. Word extraction
    results.append(("Word Extraction", test_word_extraction()))

    # 4. HTML rendering
    results.append(("HTML Rendering", test_html_rendering()))

    # Results
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\nAll basic tests passed!")
        print("\nNext: Run test_segmentation.py for advanced tests")
        return 0
    else:
        print("\nSome tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
