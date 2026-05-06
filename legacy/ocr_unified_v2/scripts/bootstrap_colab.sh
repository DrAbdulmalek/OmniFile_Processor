#!/usr/bin/env bash
set -euo pipefail
apt-get update -qq
apt-get install -y -qq poppler-utils tesseract-ocr tesseract-ocr-ara
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-colab.txt
