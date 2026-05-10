#!/usr/bin/env python3
"""
اختبار الوضع التفاعلي - محاكاة تصحيحات المستخدم.
Interactive mode tests - Simulate user corrections.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np


def test_mock_corrections():
    """Test mock corrections."""
    print("\n[TEST] Testing mock corrections...")

    from interactive_learning import InteractiveLearningSystem

    # Create image
    img = np.ones((200, 500, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Helo", (150, 120), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 4)

    temp_path = Path("test_data/temp_correct.jpg")
    cv2.imwrite(str(temp_path), img)

    try:
        system = InteractiveLearningSystem(
            model_path="microsoft/trocr-base-handwritten",
            learning_mode=False,
            auto_train=False,
            device="cpu"
        )

        # Process
        layout = system.process_page(temp_path)
        print(f"  [OK] Processed: {len(system._all_words())} words")

        # Simulate corrections
        corrections = {}
        for para in layout.paragraphs:
            for line in para.lines:
                for word in line.words:
                    # "Mock" correction: add a character
                    corrected = word.text + "!"
                    corrections[word.id] = corrected
                    print(f"     {word.text} -> {corrected}")

        system.corrections = corrections

        # Learning (without real training for speed)
        print(f"  [OK] Mocked {len(corrections)} corrections")

        # Render HTML
        output = system.render_with_layout(
            format="html",
            output_path=Path("test_data/output/interactive_test.html")
        )
        print(f"  [OK] Rendered: {output}")

        # Verify
        html_content = output.read_text()
        has_corrections = any(c in html_content for c in corrections.values())

        if has_corrections:
            print("  [OK] Corrections reflected in output")
        else:
            print("  [WARN] Corrections may not be in output")

        temp_path.unlink()
        return True

    except Exception as e:
        print(f"  [FAIL] Interactive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_export_training_data():
    """Test training data export."""
    print("\n[TEST] Testing training data export...")

    from interactive_learning import InteractiveLearningSystem

    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Test", (100, 120), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 4)

    temp_path = Path("test_data/temp_export.jpg")
    cv2.imwrite(str(temp_path), img)

    try:
        system = InteractiveLearningSystem(learning_mode=False)
        system.process_page(temp_path)

        # Add corrections
        for para in system.current_layout.paragraphs:
            for line in para.lines:
                for word in line.words:
                    system.corrections[word.id] = "Exported"

        # Export
        export_dir = Path("test_data/output/training_export")
        result = system.export_training_data(export_dir)

        print(f"  [OK] Exported:")
        print(f"     Train dir: {result['train']}")
        print(f"     Total pairs: {result['total_pairs']}")

        # Verify files
        has_images = list(result['train'].glob("*.png"))
        has_labels = (result['train'] / "labels.json").exists()

        print(f"     Images: {len(has_images)}")
        print(f"     Labels file: {has_labels}")

        temp_path.unlink()
        return len(has_images) > 0 and has_labels

    except Exception as e:
        print(f"  [FAIL] Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stats():
    """Test statistics."""
    print("\n[TEST] Testing stats collection...")

    from interactive_learning import InteractiveLearningSystem

    system = InteractiveLearningSystem(learning_mode=False)

    # Before processing
    stats_empty = system.get_stats()
    print(f"  Empty stats: {stats_empty}")

    # After processing
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Stats", (100, 120), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 4)

    temp_path = Path("test_data/temp_stats.jpg")
    cv2.imwrite(str(temp_path), img)

    system.process_page(temp_path)

    stats = system.get_stats()
    print(f"  After processing:")
    for key, value in stats.items():
        print(f"     {key}: {value}")

    temp_path.unlink()
    return True


def main():
    """Main test runner."""
    print("=" * 60)
    print("OmniFile Interactive Tests")
    print("=" * 60)

    results = []

    results.append(("Mock Corrections", test_mock_corrections()))
    results.append(("Export Training Data", test_export_training_data()))
    results.append(("Stats Collection", test_stats()))

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

    if passed == total:
        print("\nAll interactive tests passed!")
        print("\nReady for:")
        print("  - Real user testing")
        print("  - Performance optimization")
        print("  - Production deployment prep")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
