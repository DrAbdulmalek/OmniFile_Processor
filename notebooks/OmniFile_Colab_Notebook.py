"""
notebooks/OmniFile_Colab_Notebook.py
======================================
Google Colab helper script for OmniFile AI Processor v5.0.
This file is for reference — use OmniFile_v500_Colab.ipynb for actual Colab execution.

Author: Dr. Abdulmalek Tamer Al-husseini | Homs, Syria
"""
# NOTE: The full interactive Colab notebook is at:
#   notebooks/OmniFile_v500_Colab.ipynb  (59 cells)
# This script provides standalone helper functions for non-Colab environments.

import os
import sys
import subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "src"))


def setup_colab(repo_url: str = "https://github.com/DrAbdulmalek/OmniFile_Processor.git") -> str:
    """Clone or update the repo and install requirements."""
    repo_name = "OmniFile_Processor"
    repo_dir  = f"/content/{repo_name}"
    if os.path.exists(repo_dir):
        subprocess.run(["git", "pull", "-q"], cwd=repo_dir)
        print(f"Updated: {repo_dir}")
    else:
        subprocess.run(["git", "clone", "-q", repo_url])
        print(f"Cloned: {repo_dir}")
    subprocess.run(["pip", "install", "-q", "-r", "requirements-colab.txt"], cwd=repo_dir)
    sys.path.insert(0, repo_dir)
    sys.path.insert(0, f"{repo_dir}/src")
    return repo_dir


def run_ocr(image_path: str, lang: str = "ar+en") -> dict:
    """Run OCR on an image and return word-level results."""
    from PIL import Image
    import easyocr
    img    = Image.open(image_path)
    reader = easyocr.Reader(["ar", "en"], gpu=False, verbose=False)
    import numpy as np
    results = reader.readtext(np.array(img))
    words   = [{"text": t, "confidence": round(c, 3)} for _, t, c in results]
    return {"words": words, "count": len(words)}


def run_spell_check(text: str) -> dict:
    """Auto-detect language and spell-check text."""
    from modules.core.spell_checker import HybridSpellChecker
    sc = HybridSpellChecker()
    return sc.check_text(text)


def get_db_stats() -> dict:
    """Get correction database statistics."""
    from modules.core.word_trainer import WordCorrectionDB
    return WordCorrectionDB().stats()


def export_corrections(output_path: str = "/tmp/corrections.json") -> str:
    """Export correction database to JSON."""
    from modules.core.word_trainer import WordCorrectionDB
    return WordCorrectionDB().export_json(output_path)


if __name__ == "__main__":
    print("OmniFile Colab Helper v5.0")
    print("Use OmniFile_v500_Colab.ipynb for the full interactive notebook.")
    print(f"Project root: {REPO}")
