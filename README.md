---
title: OmniFile AI Processor
emoji: 🧠
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

<div align="center">

# 🧠 OmniFile AI Processor v5.0.0

**نظام ذكاء اصطناعي متكامل لمعالجة الملفات والنصوص والخط اليدوي**
**A Comprehensive AI System for File Processing, Text Analysis & Handwriting Recognition**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI Tests](https://img.shields.io/github/actions/workflow/status/DrAbdulmalek/OmniFile_Processor/ci.yml?branch=main&label=CI%20Tests)](https://github.com/DrAbdulmalek/OmniFile_Processor/actions/workflows/ci.yml)
[![HF Spaces](https://img.shields.io/badge/🤗-HuggingFace%20Spaces-orange)](https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr)
[![GitHub](https://img.shields.io/badge/GitHub-DrAbdulmalek-181717?logo=github)](https://github.com/DrAbdulmalek/OmniFile_Processor)

<p>
  <b>Version:</b> v5.0.0 &nbsp;|&nbsp;
  <b>Status:</b> ✅ CI-Verified
</p>

[🌐 Live Demo (HF Spaces)](https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr) &nbsp;|&nbsp;
[🧪 HF Lab Space](https://huggingface.co/spaces/DrAbdulmalek/omnifile-processor-lab) &nbsp;|&nbsp;
[📘 Documentation](docs/USER_GUIDE.md) &nbsp;|&nbsp;
[🧩 Dependency Profiles](docs/DEPENDENCY_PROFILES.md) &nbsp;|&nbsp;
[📓 Colab Debug Notebook](notebooks/OmniFile_Processor_Colab_Debug.ipynb) &nbsp;|&nbsp;
[🗂️ Prioritized Suggestions](docs/PRIORITIZED_SUGGESTIONS.md) &nbsp;|&nbsp;
[🐛 Report Bug](https://github.com/DrAbdulmalek/OmniFile_Processor/issues) &nbsp;|&nbsp;
[💡 Suggestions](SUGGESTIONS.md)

</div>

---

## 👨‍💻 About the Author | عن المؤلف

<table>
  <tr>
    <td align="center" width="150">
      <img src="docs/author.png" alt="Dr Abdulmalek Tamer Al-husseini" width="130" height="130" style="border-radius: 50%; object-fit: cover;" />
    </td>
    <td>
      <h3>Dr Abdulmalek Tamer Al-husseini</h3>
      <p>
        <b>📍 Location:</b> Homs, Syria<br>
        <b>📧 Email:</b> <a href="mailto:Abdulmalek.husseini@gmail.com">Abdulmalek.husseini@gmail.com</a><br>
        <b>🐙 GitHub:</b> <a href="https://github.com/DrAbdulmalek">DrAbdulmalek</a><br>
        <b>🤗 HuggingFace:</b> <a href="https://huggingface.co/DrAbdulmalek">DrAbdulmalek</a>
      </p>
    </td>
  </tr>
</table>

---

## 📖 Description | الوصف

OmniFile AI Processor is a production-ready, multimodal AI system that integrates **six projects** into a unified platform for document intelligence:

**OmniFile_Processor** + **HandwrittenOCR** + **handwriting-ocr** + **arabic-ocr-pro** + **advanced-ocr** + **OCR-Enhancer**

> نظام ذكاء اصطناعي متقدم يجمع ستة مشاريع في منصة واحدة لمعالجة الملفات والخط اليدوي. يدعم العربية والإنجليزية والألمانية مع وحدات متخصصة للرؤية الحاسوبية ومعالجة اللغة والأمان والتصدير.

---

## ✨ Features | المميزات

### 🔍 Computer Vision & OCR (وحدة الرؤية الحاسوبية)
1. **Multi-Engine OCR** — 4 engines (TrOCR, EasyOCR, Tesseract, PaddleOCR) with intelligent engine selection
2. **Result Fusion** — 4 strategies: highest confidence, weighted average, voting, longest text
3. **Advanced Preprocessing** — CLAHE, deskew, denoise, Otsu thresholding, ONNX Runtime acceleration
4. **Layout Analysis** — Automatic detection of tables, headers, footers, and document structure
5. **Table Extraction** — Hough line detection + contour analysis for structured data extraction

### 🗣️ Natural Language Processing (وحدة معالجة اللغة)
6. **Multilingual Spell Correction** — Arabic, English, German with user-learning capability (186+ Arabic corrections)
7. **RTL Text Processing** — Full Arabic reshaping + BiDi support with 40+ normalization mappings
8. **Mixed-Text Handling** — Arabic/English/numbers with medical term protection
9. **Translation Engine** — Helsinki-NLP/opus-mt supporting 6 language pairs
10. **AI Summarization** — BART (facebook/bart-large-cnn) + Arabic (UAE-Code/mbart-summarization-ar)
11. **Entity Extraction & Text Classification** — BERT-based NER with 6-category classification

### 🤖 AI Enhancement (وحدة الذكاء الاصطناعي)
12. **GPT & Gemini Refinement** — Context-aware OCR correction with block-type-specific prompts
13. **SSIM Pattern Matching** — Self-learning from corrected word images with SQLite pattern database

### 🌐 AI Gateway (وحدة بوابة الذكاء الاصطناعي)
14. **Universal AI Model Proxy** — Drop-in proxy server compatible with Messages API protocol, routes to 8+ providers (DeepSeek, NVIDIA NIM, OpenRouter, Ollama, LM Studio, llama.cpp, Kimi, Wafer)
15. **Multi-Provider Routing** — Intelligent model routing with per-tier selection (Opus/Sonnet/Haiku levels) and automatic fallback
16. **Streaming SSE** — Full Server-Sent Events streaming with thinking block support and tool call conversion
17. **Request Optimization** — Fast-path optimizations including quota mock, prefix detection, title/suggestion skip
18. **Rate Limiting & Concurrency** — Configurable per-provider rate limits, concurrency control, and timeout management

### 📤 Multi-Format Export (وحدة التصدير)
19. **6 Export Formats** — DOCX (RTL support), HTML, searchable PDF, Excel, JSON (with BBox), TXT (UTF-8 BOM)

### 🔒 Security & Privacy (وحدة الأمان)
20. **PII Detection** — Presidio-based sensitive data scanning + detect-secrets
21. **File Encryption** — Fernet (AES-128) with folder support
22. **Code Protection** — Prevents spell correction inside code blocks
23. **Audit Logging** — File + Redis audit trail with rate limiting (slowapi + Nginx)

### 📊 Evaluation (وحدة التقييم)
24. **CER/WER Metrics** — OCR accuracy evaluation with Arabic normalization + Levenshtein distance
25. **Quality Grading** — A+ to F with actionable recommendations

### 🖥️ Multiple Interfaces (واجهات المستخدم)
26. **4 UIs** — Streamlit (6 tabs), Gradio (7 tabs), React + shadcn/ui (dark/light), CLI, PyQt6 desktop
27. **FastAPI Backend** — Full REST API with Swagger documentation

### 🚀 Scalability & Deployment (التحجيم والنشر)
28. **Docker + Compose** — One-command deployment with all services
29. **Kubernetes Ready** — Complete K8s manifests with HPA (2-10 pods auto-scaling)
30. **Celery + Redis** — Asynchronous task processing for heavy workloads

---

## 🚀 Quick Start | التشغيل السريع

### Option 1: HuggingFace Spaces (Recommended for Demo)

The project is deployed and available at:
👉 **Production demo:** [https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr](https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr)

👉 **Experimental lab space:** [https://huggingface.co/spaces/DrAbdulmalek/omnifile-processor-lab](https://huggingface.co/spaces/DrAbdulmalek/omnifile-processor-lab)

To deploy your own instance:

```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
pip install -r requirements-hf.txt
python -m src.gradio_ui
```

### Option 2: Local Installation (Linux / macOS / Windows)

```bash
# Clone the repository
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# Install dependencies
pip install -r requirements-full.txt          # Everything (~6-8 GB, ~15-30 min)

# Or install in layers:
# pip install -r requirements-core.txt          # Minimum (~1.5 GB, ~3 min)
# pip install -r requirements-core.txt -r requirements-ocr.txt   # + OCR engines
# pip install -r requirements-core.txt -r requirements-nlp.txt   # + NLP

# Run with your preferred interface
streamlit run app.py          # Streamlit UI (6 tabs)
python -m src.gradio_ui       # Gradio UI (7 tabs)
python main.py                # CLI interface
cd frontend && npm install && npm run dev  # React Frontend
```

### Option 3: Docker Compose (Full Stack)

```bash
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
docker-compose up -d

# Access:
# API Docs:    http://localhost:5001/docs
# Streamlit:   http://localhost:7860
# React:       http://localhost:3000
# Nginx Proxy: http://localhost
```

### Option 3.5: Mobile Review → Training Data

```bash
python mobile_review/server.py --host 0.0.0.0 --port 5000
# بعد المراجعة والحفظ:
python mobile_review/server.py --export-dataset --export-output mobile_review/dataset/review_dataset

# أو عبر الأداة مباشرة:
python tools/build_training_data.py --corrections mobile_review/ocr_corrected.json --output dataset/review_dataset
```

### Option 4: Google Colab

يفضَّل استخدام الدفتر الجاهز:
👉 **[notebooks/OmniFile_Processor_Colab_Debug.ipynb](notebooks/OmniFile_Processor_Colab_Debug.ipynb)**

```python
!git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
%cd OmniFile_Processor
!apt-get update -qq
!apt-get install -y -qq poppler-utils tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng libgl1
!pip install -r requirements-colab.txt
!python hf_app.py
```

> للمزيد عن فروق التثبيت، راجع [docs/DEPENDENCY_PROFILES.md](docs/DEPENDENCY_PROFILES.md).

### Option 5: AI Gateway (Universal Model Proxy)

The OmniFile AI Gateway provides a universal proxy for routing AI model requests to multiple providers:

```bash
# Clone and install gateway dependencies
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor
pip install -r requirements-gateway.txt

# Configure your provider (edit modules/ai/gateway/.env)
cp modules/ai/gateway/.env.example modules/ai/gateway/.env

# Start the gateway
bash scripts/start_gateway.sh

# Or start manually:
python -m uvicorn modules.ai.gateway.server:app --host 0.0.0.0 --port 8082
```

**Supported Providers:** DeepSeek, NVIDIA NIM, OpenRouter, Ollama, LM Studio, llama.cpp, Kimi, Wafer

---

## 🧪 Benchmark & Review Utilities

```bash
# Benchmark OCR engines on a folder of images
python tools/benchmark_ocr.py --images examples/ --output artifacts/ocr_benchmark

# Optional ground truth comparison
python tools/benchmark_ocr.py --images examples/ --ground-truth examples/ground_truth.json --output artifacts/ocr_benchmark
```

## 📁 Project Structure | هيكل المشروع

> **ملاحظة معمارية — Architecture Note:**
> يوجد في المشروع نظامان متوازيان:
> - **`modules/`** — البنية النظرية الموسّعة: وحدات منظّمة بوضوح (vision, nlp, security, export, ai, evaluation) مع نماذج Pydantic v2. هذه هي البنية المستقبلية المقصودة للمشروع.
> - **`src/`** — محرك HandwrittenOCR العملي: يحتوي على التطبيق الفعلي المُستخدَم في واجهة Gradio (`src/gradio_ui.py`) وHF Spaces. يشمل TrOCR Batch, LoRA Fine-tuning, Active Learning, وStudy Guide.
> - **الملفات الجذرية** (`app.py`, `database.py`, `config.py`) — طبقة التكامل التي تربط بين البنية والمحركات.
>
> **الخيار المتبنّى حالياً:** `src/` هو الكود العملي الفعّال لواجهة Gradio وHF Spaces، بينما `modules/` يمثل البنية النظرية المنظمة للمشروع الموسّع. التحويل التدريجي (migration) من `src/` إلى `modules/` سيتم على مراحل عبر Pull Requests مستقلة.

```
OmniFile_Processor/
├── app.py                          # Main Streamlit UI
├── config.py                       # Central configuration v4.1.1
├── database.py                     # SQLite database layer
├── main.py                         # Local / CLI entry point
├── tasks.py                        # Celery async tasks
├── requirements.txt                # Full dependencies (legacy)
├── requirements-core.txt           # Core only (~1.5 GB)
├── requirements-ocr.txt            # OCR engines layer
├── requirements-nlp.txt            # NLP layer
├── requirements-full.txt           # Everything (~6-8 GB)
├── requirements-hf.txt             # HuggingFace Spaces (minimal)
├── Dockerfile                      # Docker image
├── docker-compose.yml              # Full stack orchestration
├── nginx.conf                      # Nginx load balancer
├── LICENSE                         # MIT License
│
├── modules/
│   ├── core/                       # Core data models
│   │   └── structure.py            #   Pydantic v2 models
│   │
│   ├── vision/                     # Computer Vision & OCR
│   │   ├── ocr_engine.py           #   4 OCR engines + ONNX + Quantization
│   │   ├── image_preprocessor.py   #   CLAHE + Denoise + Deskew + Otsu
│   │   ├── pdf_processor.py        #   Multi-format PDF processing
│   │   ├── text_reconstructor.py   #   RTL/LTR sentence reconstruction
│   │   ├── result_fusion.py        #   4 fusion strategies
│   │   ├── layout_analyzer.py      #   Layout analysis (tables, headers)
│   │   └── table_extractor.py      #   Table extraction (Hough + contours)
│   │
│   ├── nlp/                        # Natural Language Processing
│   │   ├── spell_corrector.py      #   3-language correction + learning
│   │   ├── translator.py           #   Helsinki-NLP translation
│   │   ├── summarizer.py           #   BART summarization
│   │   ├── entity_extractor.py     #   BERT-based NER
│   │   ├── language_detector.py    #   Language detection
│   │   ├── text_classifier.py      #   6-category classification
│   │   ├── arabic_rtl.py           #   Full RTL processing
│   │   ├── mixed_text.py           #   Arabic/English mixed text
│   │   ├── ai_corrector.py         #   GPT-based correction
│   │   ├── arabic_nlp_utils.py     #   Semantic similarity for Arabic OCR
│   │   └── correction_dict.json    #   186+ Arabic corrections
│   │
│   ├── ai/                         # AI Enhancement
│   │   ├── pattern_matcher.py      #   SSIM pattern matching
│   │   ├── pattern_db.py           #   SQLite pattern database
│   │   ├── gemini_refiner.py       #   Gemini AI refinement
│   │   └── gateway/                #   OmniFile AI Gateway (universal proxy)
│   │       ├── server.py           #     ASGI entry point
│   │       ├── api/                #     FastAPI routes & auth
│   │       ├── config/             #     Provider catalog & settings
│   │       ├── core/               #     SSE & protocol helpers
│   │       ├── providers/          #     8 provider backends
│   │       └── pool/               #     Account pool & health management
│   │
│   ├── security/                   # Security & Privacy
│   │   ├── file_scanner.py         #   Security scanning
│   │   ├── sensitive_data_scanner.py # PII detection (Presidio)
│   │   ├── encryption.py           #   Fernet encryption (AES-128)
│   │   ├── code_protector.py       #   Code block protection
│   │   ├── file_organizer.py       #   Auto file organization
│   │   ├── archive_handler.py      #   Archive management
│   │   ├── backup_manager.py       #   Backup management
│   │   ├── audit_logger.py         #   Audit logging
│   │   └── secure_file_handler.py  #   Safe file handling
│   │
│   ├── export/                     # Multi-Format Export
│   │   ├── exporter.py             #   DOCX/HTML/PDF/JSON/TXT/Excel
│   │   └── layout_preserving.py    #   DOCX export with visual layout preservation
│   │
│   └── evaluation/                 # Evaluation & Metrics
│       └── metrics.py              #   CER/WER + quality grading
│
├── frontend/                       # React + shadcn/ui Web App
│   ├── src/
│   │   ├── App.jsx                 #   Main application
│   │   ├── components/             #   UI components
│   │   │   ├── FileUpload.jsx
│   │   │   ├── ProcessingOptions.jsx
│   │   │   └── ResultsDisplay.jsx
│   │   └── services/api.js         #   API client
│   └── package.json
│
├── backend/                        # FastAPI Backend
│   └── main.py                     #   REST API endpoints
│
├── data/
│   └── arabic_fixes.json           # 186 Arabic corrections
├── data_seed/
│   └── correction_dict_seed.json   # Seed data
├── artifacts/
│   └── correction_dict.json        # Learned corrections
│
├── src/                            # HandwrittenOCR Engine
├── mobile/                         # Static PWA (offline review)
├── mobile_review/                  # Flask server (remote team review)
│   ├── server.py                  #   REST API review server
│   ├── templates/review.html      #   Touch-friendly review UI
│   └── README.md                  #   mobile/ vs mobile_review/ guide
├── tests/                          # pytest test suite (13 files)
├── .github/workflows/              # CI/CD
│   ├── ci.yml                     #   Tests on push/PR
│   └── release.yml                #   Auto-release on tags
├── notebooks/                      # Jupyter Notebooks
│   ├── OmniFile_Gradio_Debugger.ipynb  #   Gradio interactive debugger (Colab-ready)
├── docs/                           # Documentation
│   ├── TESTING_GUIDE.md          #   Testing & development guide
│   ├── API_DOCS.md
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
├── k8s/                            # Kubernetes manifests
│   ├── namespace.yaml
│   ├── backend.yaml
│   ├── celery.yaml
│   ├── redis.yaml
│   ├── nginx.yaml
│   ├── hpa.yaml
│   └── storage.yaml
└── examples/                       # Usage examples
    ├── ocr_basic.py
    ├── nlp_pipeline.py
    └── evaluation_example.py
```

---

## 🧩 Module Descriptions | وصف الوحدات

### 1. 🎯 `modules/core/` — Core Data Models

The foundational layer defining all shared data structures using **Pydantic v2**. Provides type-safe models for OCR results, processing options, document metadata, and inter-module communication.

| File | Description |
|------|-------------|
| `structure.py` | Pydantic v2 models for OCRResult, ProcessingOptions, Document, BoundingBox, and all shared types |

---

### 2. 👁️ `modules/vision/` — Computer Vision & OCR Engine

The heart of the system. Handles image preprocessing, OCR with 4 engines, result fusion, PDF processing, layout analysis, table extraction, and text reconstruction.

| File | Description |
|------|-------------|
| `ocr_engine.py` | Multi-engine OCR (TrOCR, EasyOCR, Tesseract, PaddleOCR) with ONNX Runtime & INT8 quantization |
| `image_preprocessor.py` | CLAHE, Gaussian denoise, deskew (Hough), Otsu thresholding, adaptive binarization |
| `pdf_processor.py` | PyMuPDF-based PDF processing with pdf2image fallback |
| `text_reconstructor.py` | RTL/LTR sentence reconstruction with language-aware ordering |
| `result_fusion.py` | 4 fusion strategies: highest confidence, weighted average, voting, longest text |
| `layout_analyzer.py` | Document layout analysis — tables, headers, footers, sections |
| `table_extractor.py` | Table extraction using Hough lines + contour analysis |

---

### 3. 🗣️ `modules/nlp/` — Natural Language Processing

Multilingual text processing including spell correction, translation, summarization, entity extraction, text classification, and Arabic RTL handling.

| File | Description |
|------|-------------|
| `spell_corrector.py` | 3-language spell correction (AR, EN, DE) with user learning & Python keyword protection |
| `translator.py` | Helsinki-NLP/opus-mt machine translation (6 language pairs) |
| `summarizer.py` | BART summarization (English + Arabic) |
| `entity_extractor.py` | BERT-based Named Entity Recognition |
| `language_detector.py` | Automatic language detection (AR, EN, DE) |
| `text_classifier.py` | 6-category text classification |
| `arabic_rtl.py` | Full RTL processing — arabic_reshaper + python-bidi + 40+ normalization rules |
| `mixed_text.py` | Arabic/English/number mixed text handler with medical term protection |
| `ai_corrector.py` | GPT-based OCR correction with context awareness |
| `correction_dict.json` | 186+ common Arabic OCR error corrections |

---

### 4. 🔒 `modules/security/` — Security & Privacy

Comprehensive security module for PII detection, encryption, code protection, file organization, backup management, and audit logging.

| File | Description |
|------|-------------|
| `file_scanner.py` | File security scanning and validation |
| `sensitive_data_scanner.py` | PII detection using Microsoft Presidio + detect-secrets |
| `encryption.py` | Fernet symmetric encryption (AES-128) with folder support |
| `code_protector.py` | Prevents spell correction inside code blocks (Python, JS, etc.) |
| `file_organizer.py` | Automatic file organization by type and content |
| `archive_handler.py` | ZIP archive creation/extraction with integrity checks |
| `backup_manager.py` | Automatic and manual backup management |
| `audit_logger.py` | File + Redis audit trail with statistics |
| `secure_file_handler.py` | Path traversal prevention + safe tempfile handling |

---

### 5. 🤖 `modules/ai/` — AI Enhancement

Advanced AI capabilities including self-learning pattern matching, Gemini-based refinement, and a universal AI model gateway.

| File | Description |
|------|-------------|
| `pattern_matcher.py` | SSIM-based visual pattern matching — learns from corrected word images |
| `pattern_db.py` | SQLite database for storing and retrieving visual OCR patterns |
| `gemini_refiner.py` | Google Gemini API integration for context-aware OCR refinement |
| `gateway/` | **OmniFile AI Gateway** — Universal proxy for routing AI model requests to multiple providers (see below) |

#### 🌐 `modules/ai/gateway/` — OmniFile AI Gateway

A universal AI model proxy that intercepts Messages API requests and routes them to alternative providers. Supports 8 provider backends with automatic format conversion and SSE streaming.

| Subdirectory | Description |
|-------------|-------------|
| `api/` | FastAPI application layer — routes, auth, model routing, request optimization |
| `api/models/` | Pydantic request/response models for the Messages API protocol |
| `api/web_tools/` | Local web search and fetch handling with SSRF protection |
| `config/` | Central settings, provider catalog, logging configuration |
| `core/` | Protocol helpers — SSE formatting, message conversion, token estimation |
| `core/anthropic/` | Native Messages API support — content blocks, thinking tags, tool parsing |
| `providers/` | Provider transport implementations — OpenAI-compatible and native protocols |
| `providers/deepseek/` | DeepSeek provider (native Messages API) |
| `providers/nvidia_nim/` | NVIDIA NIM provider (OpenAI-compatible) |
| `providers/open_router/` | OpenRouter provider (native Messages API) |
| `providers/ollama/` | Ollama local provider (native Messages API) |
| `providers/lmstudio/` | LM Studio local provider (native Messages API) |
| `providers/llamacpp/` | llama.cpp local provider (native Messages API) |
| `providers/kimi/` | Kimi/Moonshot provider (OpenAI-compatible) |
| `providers/wafer/` | Wafer provider (native Messages API) |
| `server.py` | ASGI entry point for the gateway proxy |
| `pool/` | **Advanced Pool Management** — Account pooling, rate limit fallback, conversation reuse, health scoring |

##### 🔄 `modules/ai/gateway/pool/` — Advanced Pool Management

Intelligent multi-account management system with automatic failover, rate limit distribution, and conversation context reuse.

| File | Description |
|------|-------------|
| `account_pool.py` | **AccountPool** — Multi-account rotation with priority ordering, LRU selection, concurrency control, and automatic failover after consecutive failures |
| `rate_limit_fallback.py` | **RateLimitFallbackManager** — Smart model fallback when rate-limited: auto-detects effort tiers (low/medium/high/xhigh/max), picks same-provider alternatives first, then cross-provider |
| `conversation_pool.py` | **ConversationPool** — Multi-turn conversation reuse via stable fingerprinting: normalizes dynamic tokens (dates, UUIDs, CWDs), TTL-based LRU eviction (500 entries, 30 min default) |
| `health_scorer.py` | **ProviderHealthScorer** — Weighted health scoring (0.0-1.0) based on success rate, latency percentiles (p50/p95), error type tracking, and consecutive failure streaks |

---

### 6. 📤 `modules/export/` — Multi-Format Export

Export processed documents to 6 different formats with proper RTL support.

| File | Description |
|------|-------------|
| `exporter.py` | Export to DOCX (RTL bidi), HTML (`dir="rtl"`), searchable PDF (invisible text), Excel (RTL alignment), JSON (full structure with BBox), TXT (UTF-8 BOM) |

---

### 7. 📊 `modules/evaluation/` — Evaluation & Metrics

OCR accuracy evaluation with Arabic-aware normalization.

| File | Description |
|------|-------------|
| `metrics.py` | CER/WER computation, Arabic text normalization, Levenshtein distance (zero dependencies), quality grading (A+ to F) |

---

## 🔗 API Documentation | توثيق API

The FastAPI backend exposes the following REST endpoints. Full interactive documentation is available at `/docs` (Swagger UI) when the backend is running.

### Base URL
```
http://localhost:5001/api/v1
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ocr/process` | Process an image/PDF file with OCR |
| `POST` | `/ocr/process-batch` | Batch process multiple files |
| `GET` | `/ocr/result/{task_id}` | Get OCR result by task ID |
| `POST` | `/nlp/correct` | Spell-correct text (AR/EN/DE) |
| `POST` | `/nlp/translate` | Translate text between languages |
| `POST` | `/nlp/summarize` | Summarize text |
| `POST` | `/nlp/entities` | Extract named entities |
| `POST` | `/nlp/classify` | Classify text into categories |
| `POST` | `/export/{format}` | Export results to DOCX/HTML/PDF/JSON/TXT/Excel |
| `POST` | `/security/scan` | Scan file for PII and security issues |
| `POST` | `/security/encrypt` | Encrypt a file |
| `POST` | `/security/decrypt` | Decrypt a file |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/metrics` | System performance metrics |

> 📖 For the complete API reference with request/response schemas, see [docs/API_DOCS.md](docs/API_DOCS.md) or access the Swagger UI at `/docs`.

---

## 📸 Screenshots | لقطات الشاشة

<!-- TODO: Add actual screenshots -->

| Streamlit UI | Gradio UI | React Frontend |
|:---:|:---:|:---:|
| ![Streamlit](docs/screenshots/streamlit.png) | ![Gradio](docs/screenshots/gradio.png) | ![React](docs/screenshots/react.png) |
| *6-tab interface* | *7-tab interface* | *Dark/Light mode* |

| OCR Processing | Arabic RTL | Table Extraction |
|:---:|:---:|:---:|
| ![OCR](docs/screenshots/ocr.png) | ![RTL](docs/screenshots/rtl.png) | ![Tables](docs/screenshots/tables.png) |
| *Multi-engine OCR* | *Full RTL support* | *Structured data* |

> 📝 Screenshots will be added in a future update. For now, try the [live demo](https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr) to see the application in action.
>
> 📋 See [CHANGELOG.md](CHANGELOG.md) for the complete version history.

---

## 📊 Project Statistics | إحصائيات المشروع

| Metric | Value |
|--------|-------|
| Python Files | 155+ |
| Lines of Code | ~40,000+ |
| Total Files | 230+ |
| OCR Engines | 4 (TrOCR, EasyOCR, Tesseract, PaddleOCR) |
| Fusion Strategies | 4 |
| Supported Languages | 3 (EN, AR, DE) |
| Export Formats | 6 (DOCX, HTML, PDF, JSON, TXT, Excel) |
| Test Files | 13 |
| Merged Projects | 6 |
| Security Modules | 9 |
| NLP Capabilities | 10 |
| AI Gateway Providers | 8 (DeepSeek, NIM, OpenRouter, Ollama, LM Studio, llama.cpp, Kimi, Wafer) |
| API Endpoints | 14+ |

---

## 🌍 Supported Languages | اللغات المدعومة

| Language | Code | RTL Support | OCR | Spell Check | Translation |
|----------|------|:-----------:|:---:|:-----------:|:-----------:|
| 🇸🇦 العربية (Arabic) | `ar` | ✅ | ✅ | ✅ | ✅ |
| 🇬🇧 English | `en` | ❌ | ✅ | ✅ | ✅ |
| 🇩🇪 Deutsch (German) | `de` | ❌ | ✅ | ✅ | ✅ |

---

## 🤝 Contributing | المساهمة

Contributions are welcome! Please follow these steps:

### كيف تساهم / How to Contribute

1. **Fork** the repository
2. **Clone** your fork locally
   ```bash
   git clone https://github.com/your-username/OmniFile_Processor.git
   cd OmniFile_Processor
   ```
3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** and ensure tests pass
   ```bash
   pip install -r requirements-full.txt          # Everything (~6-8 GB, ~15-30 min)

# Or install in layers:
# pip install -r requirements-core.txt          # Minimum (~1.5 GB, ~3 min)
# pip install -r requirements-core.txt -r requirements-ocr.txt   # + OCR engines
# pip install -r requirements-core.txt -r requirements-nlp.txt   # + NLP
   pytest tests/ -v
   ```
5. **Commit** with a descriptive message
   ```bash
   git commit -m "feat: add your feature description"
   ```
6. **Push** to your fork
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** against the `main` branch

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all new functions and classes
- Write tests for new features (place in `tests/`)
- Update the relevant documentation in `docs/`
- Use type hints throughout your code
- Ensure RTL handling is tested for any text-related changes

---

## 📜 License | الترخيص

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Dr Abdulmalek Tamer Al-husseini — Homs, Syria

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

See [LICENSE](LICENSE) for the full text.

---

## 🔗 Links | الروابط

| Resource | Link |
|----------|------|
| 🐙 **GitHub Repository** | [https://github.com/DrAbdulmalek/OmniFile_Processor](https://github.com/DrAbdulmalek/OmniFile_Processor) |
| 🤗 **HuggingFace Spaces** | [https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr](https://huggingface.co/spaces/DrAbdulmalek/handwriting-ocr) |
| 📚 **User Guide** | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) |
| 👨‍💻 **Developer Guide** | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) |
| 🧪 **Testing Guide** | [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) |
| 📡 **API Documentation** | [docs/API_DOCS.md](docs/API_DOCS.md) |
| 💡 **Suggestions** | [SUGGESTIONS.md](SUGGESTIONS.md) |
| 📋 **License** | [LICENSE](LICENSE) |

---

<div align="center">

**Built with ❤️ by Dr Abdulmalek Tamer Al-husseini**
*📍 Homs, Syria &nbsp;|&nbsp; 📧 Abdulmalek.husseini@gmail.com*

⭐ If you find this project useful, please give it a star on [GitHub](https://github.com/DrAbdulmalek/OmniFile_Processor)!

</div>
