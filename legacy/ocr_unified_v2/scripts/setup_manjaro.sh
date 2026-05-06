#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${1:-$HOME/Handwritten_OCR_Ultimate}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

sudo pacman -Syu --noconfirm
sudo pacman -S --needed --noconfirm   python python-pip python-virtualenv tesseract tesseract-data-ara   poppler base-devel gcc

mkdir -p "$PROJECT_DIR"
rsync -a --delete ./ "$PROJECT_DIR/"
cd "$PROJECT_DIR"

$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-manjaro.txt

echo
echo "✅ تم الإعداد على Manjaro"
echo "لتشغيل المشروع:" 
echo "  cd $PROJECT_DIR"
echo "  source .venv/bin/activate"
echo "  python run.py --local --pdf /path/to/input.pdf"
