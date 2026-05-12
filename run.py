#!/usr/bin/env python3
"""
OmniFile AI Processor — Single Entry Point
==========================================
This is the main entry point for the OmniFile AI Processor.

Usage:
    python run.py                 # Launch Gradio UI (default)
    python run.py --api           # Launch FastAPI backend
    python run.py --medical-ocr   # Launch Medical OCR tab
    python run.py --train         # Launch training interface
    python run.py --help          # Show all options
"""

import argparse
import sys
import os

def launch_gradio():
    """Launch the main Gradio interface."""
    try:
        from hf_app import create_demo
        demo = create_demo()
        demo.launch(server_name="0.0.0.0", server_port=7860)
    except ImportError:
        try:
            import gradio as gr
            gr.Markdown("# OmniFile AI Processor").launch()
        except ImportError:
            print("Error: gradio not installed. Run: pip install -r requirements.txt")
            sys.exit(1)


def launch_api():
    """Launch the FastAPI backend."""
    try:
        import uvicorn
        uvicorn.run("backend.main:app", host="0.0.0.0", port=5001, reload=True)
    except ImportError:
        print("Error: fastapi not installed. Run: pip install -r requirements.txt")
        sys.exit(1)


def launch_medical_ocr():
    """Launch the Medical OCR Gradio tab."""
    try:
        from modules.vision.medical_ocr_gradio import create_medical_ocr_tab
        tab = create_medical_ocr_tab()
        tab.launch(server_name="0.0.0.0", server_port=7861)
    except ImportError as e:
        print(f"Error: {e}. Run: pip install -r requirements.txt")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="OmniFile AI Processor - Single Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                 # Gradio UI on :7860
  python run.py --api           # FastAPI on :5001
  python run.py --medical-ocr   # Medical OCR on :7861
        """
    )
    parser.add_argument("--api", action="store_true", help="Launch FastAPI backend on :5001")
    parser.add_argument("--medical-ocr", action="store_true", help="Launch Medical OCR interface on :7861")
    parser.add_argument("--port", type=int, default=None, help="Custom port (overrides default)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Custom host")
    
    args = parser.parse_args()
    
    if args.api:
        print("🚀 Starting OmniFile API Server on :5001")
        print("   Docs: http://localhost:5001/docs")
        launch_api()
    elif args.medical_ocr:
        print("🏥 Starting Medical OCR on :7861")
        launch_medical_ocr()
    else:
        print("🚀 Starting OmniFile Gradio UI on :7860")
        launch_gradio()


if __name__ == "__main__":
    main()
