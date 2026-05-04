#!/usr/bin/env bash
# OmniFile AI Processor — Quick Setup
set -e
echo "🧠 OmniFile AI Processor — Setup"
echo "================================="

# Detect environment
if [ -d "/content" ]; then
    ENV="colab"
elif [ -f "/etc/manjaro-release" ]; then
    ENV="manjaro"
else
    ENV="linux"
fi
echo "📍 Environment: $ENV"

# Install core
pip install -q -r requirements-core.txt

# Ask about heavy packages
read -p "Install OCR engines? (EasyOCR/Tesseract) [y/N]: " ocr
if [[ "$ocr" =~ ^[Yy]$ ]]; then
    pip install -q -r requirements-ocr.txt
fi

read -p "Install NLP models? (transformers/Helsinki) [y/N]: " nlp
if [[ "$nlp" =~ ^[Yy]$ ]]; then
    pip install -q -r requirements-nlp.txt
fi

echo ""
echo "✅ Setup complete!"
echo "   Start:  python -m src.gradio_ui"
echo "   Test:   pytest tests/ -x -q"
