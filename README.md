<div align="center">

# 🧠 OmniFile AI Processor

### نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Environment](https://img.shields.io/badge/Environment-Colab%20%7C%20Local%20%7C%20Docker-orange.svg)]()

**Author:** Dr. Abdulmalek · **License:** MIT · **Version:** 1.0.0

</div>

---

## 📋 Features Overview

| Feature | Module | Description |
|---------|--------|-------------|
| 📄 **PDF Processing** | `modules.vision` | Extract text, images, tables from PDFs using PyMuPDF |
| 🔍 **Multi-Engine OCR** | `modules.vision` | TrOCR + EasyOCR + Tesseract with auto-fallback |
| 📝 **Spell Correction** | `modules.nlp` | Arabic & English spelling correction with technical term protection |
| 🌐 **Technical Translation** | `modules.nlp` | EN→AR translation with code-block protection |
| 🏷️ **Named Entity Recognition** | `modules.nlp` | Extract entities (PERSON, ORG, LOC) from Arabic/English text |
| 📊 **Text Classification** | `modules.nlp` | Classify documents by category using AraBERT |
| 🗂️ **File Organization** | `modules.security` | Auto-organize files by content analysis & extension |
| 🔒 **Code Protection** | `modules.security` | Protect source code from unauthorized modification |
| 📦 **Archive Handling** | `modules.security` | Handle password-protected archives |
| 🛡️ **Security Scanning** | `modules.security` | Scan files for sensitive data patterns |
| 💾 **SQLite Database** | `database.py` | WAL-mode database with full-text search & export |
| 🎯 **Streamlit UI** | `app.py` | Full Arabic RTL web interface with 6 functional tabs |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     OmniFile AI Processor                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Streamlit   │  │   FastAPI    │  │    Gradio    │      │
│  │   Web UI 🌐   │  │   API ⚡     │  │   UI 🎨      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│  ┌──────┴──────────────────┴──────────────────┴───────┐      │
│  │              Config (config.py)                      │      │
│  │         OmniFileConfig Dataclass                     │      │
│  └──────┬──────────────────┬──────────────────┬───────┘      │
│         │                  │                  │               │
│  ┌──────┴──────┐  ┌───────┴──────┐  ┌───────┴──────┐      │
│  │   Vision     │  │   NLP        │  │   Security    │      │
│  │   Module     │  │   Module     │  │   Module      │      │
│  │              │  │              │  │               │      │
│  │ • PDFProc    │  │ • Translator │  │ • FileOrg     │      │
│  │ • OCR Engine │  │ • NER        │  │ • CodeProt    │      │
│  │ • ImgPreproc │  │ • SpellCorr  │  │ • FileScan    │      │
│  │ • TextRecon  │  │ • LangDetect │  │ • Archive     │      │
│  │              │  │ • TextClass  │  │ • Backup      │      │
│  └──────┬──────┘  └───────┬──────┘  └───────┬──────┘      │
│         │                  │                  │               │
│  ┌──────┴──────────────────┴──────────────────┴───────┐      │
│  │              Database (database.py)                  │      │
│  │           SQLite WAL + FileLock                      │      │
│  └──────┬──────────────────┬──────────────────┬───────┘      │
│         │                  │                  │               │
│  ┌──────┴──────┐  ┌───────┴──────┐  ┌───────┴──────┐      │
│  │  Documents   │  │  OCR/NER     │  │  History      │      │
│  │  Tables      │  │  Results     │  │  & Logs       │      │
│  └─────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌───────────────────────────────────────────────────┐      │
│  │  Storage: Local / Google Drive / HuggingFace Hub  │      │
│  │  Compute: CPU / CUDA GPU / Google Colab T4        │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Google Colab (Recommended for GPU)

```bash
# 1. Clone the repository
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor

# 2. Install dependencies
!pip install -r requirements.txt

# 3. Install Tesseract OCR
!apt-get install -y tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng

# 4. Connect Google Drive
from google.colab import drive
drive.mount('/content/drive')

# 5. Run the app
!streamlit run app.py &>/dev/null &
# Or use pyngrok for public URL
from pyngrok import ngrok
public_url = ngrok.connect(8501)
print(f"🌐 App URL: {public_url}")
```

### Local Installation (Linux/macOS)

```bash
# 1. Clone the repository
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Tesseract OCR (Linux)
sudo pacman -S tesseract tesseract-data-ara tesseract-data-eng  # Arch/Manjaro
# sudo apt-get install -y tesseract-ocr tesseract-ocr-ara       # Ubuntu/Debian
# brew install tesseract tesseract-lang                          # macOS

# 5. Run the app
streamlit run app.py
```

### Docker

```bash
# Build
docker build -t omnifile-ai .

# Run with GPU
docker run --gpus all -p 8501:8501 omnifile-ai

# Run without GPU
docker run -p 8501:8501 omnifile-ai
```

---

## 📁 Project Structure

```
omnifile-ai-processor/
├── app.py                          # Streamlit web application (main UI)
├── config.py                       # Centralized configuration (OmniFileConfig)
├── database.py                     # SQLite database module (OmniFileDB)
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .gitignore                      # Git ignore rules
├── __init__.py                     # Package init with metadata
│
├── modules/
│   ├── __init__.py
│   │
│   ├── vision/                     # Computer Vision & OCR
│   │   ├── __init__.py
│   │   ├── ocr_engine.py           # Multi-engine OCR (TrOCR+EasyOCR+Tesseract)
│   │   ├── pdf_processor.py        # PDF extraction (PyMuPDF + pdfplumber)
│   │   ├── image_preprocessor.py   # Image enhancement (CLAHE, denoise, deskew)
│   │   └── text_reconstructor.py   # RTL text reconstruction from word boxes
│   │
│   ├── nlp/                        # NLP & Translation
│   │   ├── __init__.py
│   │   ├── translator.py           # EN→AR technical translation
│   │   ├── spell_corrector.py      # Arabic & English spell correction
│   │   ├── entity_extractor.py     # Named Entity Recognition (NER)
│   │   ├── text_classifier.py      # Document classification
│   │   ├── language_detector.py    # Automatic language detection
│   │   └── correction_dict.json    # Custom correction dictionary
│   │
│   └── security/                   # File Management & Security
│       ├── __init__.py
│       ├── file_organizer.py       # Auto file organization
│       ├── code_protector.py       # Source code protection
│       ├── file_scanner.py         # Security scanning
│       ├── archive_handler.py      # Password-protected archives
│       └── backup_manager.py       # Backup & version management
│
├── database/                       # SQLite database files (auto-created)
├── data/
│   ├── raw/                        # Raw input files
│   │   ├── pdfs/
│   │   ├── images/
│   │   └── archives/
│   ├── processed/                  # Processed outputs
│   └── exports/                    # Exported data (JSON, etc.)
├── models_cache/                   # Cached ML models
├── logs/                           # Application logs
├── backups/                        # Database backups
└── notebooks/                      # Jupyter notebooks
```

---

## 🔧 Module Descriptions

### 🖥️ `modules.vision` — Computer Vision & OCR

| Component | Class | Description |
|-----------|-------|-------------|
| OCR Engine | `OCREngine` | Unified OCR with 3 engines and auto-fallback |
| PDF Processor | `PDFProcessor` | PDF text/image/table extraction |
| Image Preprocessor | `ImagePreprocessor` | CLAHE, denoising, deskewing, binarization |
| Text Reconstructor | `TextReconstructor` | RTL-aware text assembly from word boxes |

**Key Features:**
- Lazy model loading (models load only when first used)
- Graceful degradation (falls back to next engine on failure)
- Batch processing support
- GPU acceleration with automatic device detection

### 📝 `modules.nlp` — NLP & Translation

| Component | Class | Description |
|-----------|-------|-------------|
| Translator | `TechnicalTranslator` | EN→AR translation with 100+ technical glossary terms |
| Spell Corrector | `SpellCorrector` | Bilingual correction with code-term protection |
| Entity Extractor | `EntityExtractor` | NER for Arabic (PERSON, ORG, LOC, DATE) |
| Text Classifier | `TextClassifier` | Document categorization using AraBERT |
| Language Detector | `LanguageDetector` | Auto language detection (50+ languages) |

**Key Features:**
- Code-block protection in translation (variables, functions, URLs stay intact)
- Translation caching (MD5-based) for performance
- Customizable glossary for domain-specific terms
- Document-level chunked translation

### 🔒 `modules.security` — File Management & Security

| Component | Class | Description |
|-----------|-------|-------------|
| File Organizer | `FileOrganizer` | Auto-classify and sort files by extension & content |
| Code Protector | `CodeProtector` | Hash-based source code integrity verification |
| File Scanner | `FileScanner` | Detect sensitive data patterns (passwords, tokens) |
| Archive Handler | `ArchiveHandler` | Handle encrypted ZIP/RAR/TAR archives |
| Backup Manager | `BackupManager` | Automated backup with version tracking |

**Key Features:**
- Magic bytes detection for extensionless files
- 150+ file extension mappings across 8 categories
- Dry-run mode for safe preview
- Atomic operations with conflict resolution

### 💾 `database.py` — SQLite Database

| Table | Purpose |
|-------|---------|
| `documents` | Core document metadata and text |
| `ocr_results` | Per-page, per-word OCR output |
| `translations` | Source/target translation pairs |
| `entities` | Named entities with positions |
| `corrections_log` | Manual/auto correction audit trail |
| `processing_history` | Full processing pipeline log |

**Key Features:**
- WAL mode for concurrent read performance
- FileLock-based thread safety
- 18 optimized indexes
- JSON export and SQLite backup
- Automatic cleanup of old records

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python 3.12+ |
| **UI Framework** | Streamlit 1.28+, Gradio 4.0+ |
| **API** | FastAPI, Uvicorn |
| **OCR** | TrOCR, EasyOCR, Tesseract |
| **PDF** | PyMuPDF (fitz), pdf2image, pdfplumber |
| **Image** | Pillow, OpenCV |
| **NLP Models** | Helsinki-NLP/opus-mt-en-ar, AraBERT, TrOCR |
| **ML Framework** | PyTorch 2.1+, PEFT, Transformers |
| **Database** | SQLite (WAL mode) |
| **Search** | Whoosh (full-text search) |
| **File Locking** | FileLock |
| **Cloud** | HuggingFace Hub, Google Colab, pyngrok |
| **VCS** | GitPython |
| **Evaluation** | jiwer (WER/CER), TensorBoard |

---

## 👨‍💻 Author

**Dr. Abdulmalek**
- 📧 [GitHub](https://github.com/DrAbdulmalek)
- 🤗 [HuggingFace](https://huggingface.co/DrAbdulmalek)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🗺️ Roadmap v2.0

- [ ] **Web App Deployment** — Docker + Cloud hosting (Railway/Fly.io)
- [ ] **REST API** — Full CRUD API with authentication
- [ ] **Fine-Tuning Pipeline** — LoRA-based model customization
- [ ] **Arabic Handwriting Dataset** — Custom training dataset on HuggingFace
- [ ] **Real-Time Processing** — WebSocket support for live OCR
- [ ] **Multi-User Support** — User accounts and project isolation
- [ ] **Plugin System** — Extensible architecture for community plugins
- [ ] **Mobile App** — React Native companion app
- [ ] **Voice Input** — Arabic speech-to-text for dictation
- [ ] **Batch Processing Queue** — Celery/Redis for large-scale processing
- [ ] **Document Comparison** — Diff tool for document versions
- [ ] **Form Extraction** — Structured data extraction from forms

---

<div align="center">

**Built with ❤️ by Dr. Abdulmalek**

⭐ If you find this project useful, please give it a star!

</div>
