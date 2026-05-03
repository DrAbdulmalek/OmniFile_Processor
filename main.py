"""
OmniFile AI Processor v2.0 - Entry Point
==========================================
نقطة الدخول الرئيسية للتشغيل المحلي/CLI.

الاستخدام:
    python main.py                # تشغيل Streamlit UI
    python main.py --gradio       # تشغيل Gradio UI (متقدم)
    python main.py --cli          # وضع سطر الأوامر
    python main.py --colab        # إعداد بيئة Colab
"""

import argparse
import os
import sys
from pathlib import Path

# إضافة المشروع للمسار
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies() -> list[str]:
    """فحص الحزم الأساسية المطلوبة."""
    required = [
        "streamlit",
        "PIL",
        "numpy",
        "pandas",
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def run_streamlit():
    """تشغيل واجهة Streamlit."""
    import subprocess
    app_path = PROJECT_ROOT / "app.py"
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
    ])


def run_gradio():
    """تشغيل واجهة Gradio المتقدمة من src/."""
    try:
        from src.gradio_ui import build_gradio_app, launch_gradio
        app = build_gradio_app()
        launch_gradio(app)
    except ImportError:
        print("❌ فشل استيراد Gradio UI. تأكد من وجود مجلد src/gradio_ui.py")
        print("   يمكنك تشغيل Streamlit بدلاً من ذلك: python main.py")
        sys.exit(1)


def run_colab_setup():
    """إعداد بيئة Google Colab."""
    print("🔄 جارٍ إعداد بيئة Google Colab...")
    print()

    # ربط Google Drive
    print("📁 ربط Google Drive...")
    try:
        from google.colab import drive
        drive.mount("/content/drive")
        print("✅ تم ربط Google Drive")
    except ImportError:
        print("⚠️ لا يبدو أنك في بيئة Colab")

    print()
    print("📦 تثبيت الحزم...")
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        os.system(f"pip install -q -r {req_file}")
    else:
        os.system("pip install -q streamlit pandas numpy Pillow opencv-python-headless easyocr PyMuPDF transformers torch")

    print()
    print("✅ اكتمل الإعداد!")
    print("🚀 قم بتشغيل: streamlit run app.py --server.port 7860")


def main():
    parser = argparse.ArgumentParser(
        description="OmniFile AI Processor v2.0",
    )
    parser.add_argument(
        "--gradio", action="store_true",
        help="تشغيل واجهة Gradio المتقدمة",
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="وضع سطر الأوامر",
    )
    parser.add_argument(
        "--colab", action="store_true",
        help="إعداد بيئة Google Colab",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="عرض رقم الإصدار",
    )

    args = parser.parse_args()

    if args.version:
        from __init__ import __version__
        print(f"OmniFile AI Processor v{__version__}")
        return

    if args.colab:
        run_colab_setup()
        return

    # فحص الحزم
    missing = check_dependencies()
    if missing:
        print(f"⚠️ حزم مفقودة: {', '.join(missing)}")
        print("   قم بتثبيتها: pip install -r requirements.txt")
        return

    if args.gradio:
        run_gradio()
    elif args.cli:
        print("وضع CLI - قريباً")
        print("استخدم: python main.py        # Streamlit")
        print("أو:     python main.py --gradio # Gradio")
    else:
        run_streamlit()


if __name__ == "__main__":
    main()
