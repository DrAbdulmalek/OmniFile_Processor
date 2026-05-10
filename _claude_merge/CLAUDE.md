# Claude Merge Task — دمج دفاتر Jupyter Notebook

> **Objective:** Merge 24 extracted Jupyter notebooks into a single, production-ready `.ipynb` file,
> then integrate any unique features found back into the main project codebase.

---

## 1. Context — سياق المشروع

This is the **OmniFile_Processor** project: an Arabic Handwriting OCR system with spell correction,
AI gateway, and multi-model support. The repo has ~310 Python files / 79,634 lines.

### Project Structure (key directories)

```
OmniFile_Processor/
├── modules/              # Main module package
│   ├── core/             # spell_checker.py (HybridSpellChecker v7.0), word_trainer.py
│   ├── ai/               # AI gateway (multi-model routing)
│   ├── vision/           # OCR engines
│   ├── nlp/              # Arabic NLP utilities
│   ├── export/           # Exporters (DOCX, XLSX, HTML, PDF, Markdown)
│   ├── evaluation/       # CER/WER metrics
│   └── security/         # Encryption, PII scanner, audit
├── src/                  # Legacy/src modules (recognition, correction, gradio_ui, etc.)
├── hf_app.py             # Main HuggingFace Spaces app
├── app.py                # Main application
├── config.py             # Configuration
├── database.py           # OmniFileDB (WAL, 7 indexes, thread-safe)
├── notebooks/            # Existing official notebooks
└── _claude_merge/        # ← YOU ARE HERE
    ├── CLAUDE.md         # ← This file (instructions for you)
    ├── extracted_notebooks/  # 24 .ipynb files to merge
    └── output/           # Put the result here
```

### Key Technical Details

- **Spell Checking**: `modules/core/spell_checker.py` — HybridSpellChecker v7.0
  - Auto language detection (ar/en/de/mixed)
  - Protected words (technical + Python keywords)
  - Digit recognition (O→0, I→1, etc.)
  - Correction learning via WordCorrectionDB

- **Database**: `database.py` — OmniFileDB with WAL mode, 7 indexes, thread-safe

- **OCR**: TrOCR + EasyOCR + Tesseract ensemble via `src/recognition.py`

- **Gradio UI**: `src/gradio_ui.py` — main web interface

- **Config**: `config.py` — OmniFileConfig dataclass

---

## 2. Task — المهمة

### Phase 1: Analyze All 24 Notebooks

Read every `.ipynb` in `extracted_notebooks/` and create a **feature matrix**:

| Notebook | Size | Cells | OCR Engines | Spell Check | UI | Unique Features | Status |
|----------|------|-------|-------------|-------------|-----|-----------------|--------|

#### Notebook Priority Analysis:

**Tier 1 — Most Feature-Rich (use as primary base):**
1. `Arabic_OCR_v5_Final_Enhanced.ipynb` (245KB) — CorrectionRule dataclass, dict calibration, visual indicators, 8-tab Gradio
2. `Arabic_OCR_v5_deepseek.ipynb` (105KB) — Cleanest structure, page-by-page processing, SmartMigrator
3. `OmniFile_v500_Colab.ipynb` (245KB) — EngineRouter, SmartSuggestions (AraBERT), CloudSyncManager, Security suite
4. `Arabic_OCR_v5_Final.ipynb` (160KB) — Most code cells (50), SmartMigrator (8 projects), API server support

**Tier 2 — Important unique features:**
5. `HandwrittenOCR_Integrated_Monitoring_Colab.ipynb` (67KB) — Monitoring system, 3-table DB, health snapshots, deskew
6. `Arabic_OCR_Gradio_Pro.ipynb` (74KB) — First Gradio UI, auto-export, XLSX per-page sheets, progress callbacks
7. `HandwrittenOCR_Colab_zai.ipynb` (64KB) — Modular architecture, 7-tab Gradio, WER/CER metrics, study guide
8. `Another copy of HandwrittenOCR.ipynb` (791KB) — Undo stack, PDF export (FPDF), Top-k TrOCR beam search

**Tier 3 — Reference/older versions:**
9-15. `Arabic_OCR_Ultimate.ipynb`, `HandwrittenOCR_Final_claude.ipynb`, `deepseek_json_20260425_99ea0a.ipynb`, `HandwrittenOCR(1).ipynb`, `HandwrittenOCR.ipynb`, `HandwrittenOCR(2).ipynb`, `HandwrittenOCR_Colab.ipynb`

**Tier 4 — Utility/launcher notebooks:**
16-24. `Untitled*.ipynb`, `Copy of HandwrittenOCR.ipynb`, `HandwrittenOCR_Final.ipynb` (broken), `Untitled2.ipynb` (OmniFile launcher), `Untitled3.ipynb` (OmniFile launcher with patching)

### Phase 2: Merge into Single Notebook

Create `_claude_merge/output/OmniFile_Unified_Colab.ipynb` with these requirements:

#### Structure (cells in order):

```
[MD] Title + Features Table + Instructions

[Code 1]  Install — apt-get (poppler, tesseract) + pip (all packages)
[Code 2]  Imports — all dependencies
[Code 3]  Config — centralized dataclass with all parameters
[Code 4]  Logging + Monitoring — RotatingFileHandler, JSONL events, health snapshots
[Code 5]  FileLock — cross-platform file locking
[Code 6]  Database — SQLite with 3 tables (handwriting_data, processing_runs, review_events)
[Code 7]  SmartMigrator — import from 8+ old project folders
[Code 8]  Preprocessing — deskew, CLAHE, denoise, adaptive threshold, crop_safe
[Code 9]  OCREngine — TrOCR + EasyOCR + Tesseract ensemble class
[Code 10] Spell Checking + CorrectionRule — smart dictionary with metadata
[Code 11] Checkpoint — save/load/clear JSON checkpoints
[Code 12] Document Processing — page-by-page with memory management
[Code 13] Export — CSV, XLSX, JSONL, TXT, PDF report, correction rules backup
[Code 14] Sentence Reconstruction — Y-proximity grouping, RTL support
[Code 15] WER/CER Metrics — jiwer-based + matplotlib visualization
[Code 16] Active Learning — correction counting, training triggers
[Code 17] LoRA Fine-tuning — PEFT with TensorBoard, Albumentations
[Code 18] Study Guide — HTML with RTL, Mermaid diagrams, flashcards
[Code 19] Bilingual Vocab — Arabic-English vocabulary extraction
[Code 20] Gradio UI callbacks — all event handlers
[Code 21] build_app() — 8-tab Gradio Blocks UI + launch
[Code 22] Manual launch — for non-Colab use
```

#### Mandatory Features to Include:

| Feature | Source Notebook | Implementation Notes |
|---------|----------------|---------------------|
| 3-engine OCR ensemble | All Tier 1 | TrOCR (beam search) + EasyOCR + Tesseract |
| CorrectionRule dataclass | v5 Enhanced | confidence, usage_count, votes, contexts, status, flagged |
| Dict calibration | v5 Enhanced | auto_calibrate_dict_thresholds() using statistics |
| Visual priority indicators | v5 Enhanced | calculate_rule_indicator() → red/yellow/green/hourglass |
| Page-by-page processing | v5 DeepSeek | Memory-efficient, max_pages_in_memory |
| FileLock | v5 Enhanced | fcntl-based, multi-device safety |
| SmartMigrator (8 projects) | v5 Final/DeepSeek | scan → import → optional delete |
| Deskew | Monitoring | minAreaRect angle detection |
| Auto-export (5 formats) | Gradio Pro | CSV + XLSX (per-page) + JSONL + TXT + PDF |
| WER/CER + charts | ZAI Colab | jiwer + matplotlib pie/bar |
| LoRA Fine-tuning | All | PEFT, TensorBoard, Albumentations augmentation |
| Study Guide + HTML RTL | v5 DeepSeek | dir="rtl", print CSS, Mermaid, flashcards |
| Bilingual vocab extraction | Claude | Arabic/English detection per word |
| Undo stack | Another copy | word_undo() with dict rollback |
| Copy raw text | v5 Enhanced | word_copy_raw() button |
| Monitoring system | Monitoring | JSONL events, RotatingFileHandler, health snapshots |
| Active Learning | All | count_corrections, should_trigger_training |
| 8-tab Gradio UI | v5 Enhanced | Processing, Word Review, Sentence Review, Dashboard, Fine-tuning, Study Guide, Dictionary, Settings |
| Progress callbacks | Gradio Pro | gr.Progress() for long operations |
| Resume support | v5 DeepSeek | Skip already-processed pages |

#### Known Bugs in Original Notebooks (MUST FIX):

1. **v5 Enhanced**: `etrics_out` typo → should be `metrics_out`
2. **v5 Enhanced**: f-string `{verified/total_words:.1%} if total_words else 0:.1%}` — conditional outside format spec
3. **OmniFile_v500**: Hardcoded GitHub token (SECURITY ISSUE)
4. **v5 DeepSeek**: `plot_metrics_fig()` referenced but never defined
5. **v5 DeepSeek**: `create_backup()` referenced but never defined
6. **Gradio Pro**: `crop_safe` has `imgax(0,y)` typo → should be `img[max(0,y)...]`
7. **Gradio Pro**: `sent_save()` walrus operator `len(idx := ...)` — idx is int, not list
8. **Gradio Pro**: Missing `[` bracket in finetune inputs
9. **HandwrittenOCR_Final.ipynb**: BROKEN — references 10+ undefined functions
10. **All ipywidgets notebooks**: FEEDBACK_CSV header handling bug

### Phase 3: Integrate New Features into Main Project

After creating the unified notebook, check for features NOT yet in the main codebase:

#### Compare notebook features vs main project modules:

- If `CorrectionRule` dataclass doesn't exist in `modules/core/` → create `modules/core/correction_rules.py`
- If `SmartMigrator` with 8-project support is better than `src/migration.py` → update migration
- If monitoring health snapshots don't exist → add to `src/logger.py`
- If dict calibration doesn't exist → add to `modules/core/word_trainer.py`
- If bilingual vocab extraction doesn't exist → add to `src/export.py`
- If page-by-page processing isn't in `src/pdf_processor.py` → add it
- If study guide HTML with RTL/Mermaid is improved → update `src/study_guide.py`

#### For each new feature found:
1. Create or update the appropriate module file
2. Maintain backward compatibility (don't break existing imports)
3. Add docstrings (98% coverage target)
4. Add type hints (74% coverage target)
5. Update `__init__.py` exports if needed

### Phase 4: Clean Up

1. **Delete** all files in `_claude_merge/extracted_notebooks/` after successful merge
2. **Keep** only:
   - `_claude_merge/CLAUDE.md` (rename to `_claude_merge/README.md`)
   - `_claude_merge/output/OmniFile_Unified_Colab.ipynb`
3. **Commit** changes with descriptive message
4. **Do NOT** modify existing working code unless adding new features

---

## 3. Output Expected — المخرجات المتوقعة

### Primary Output:
- `_claude_merge/output/OmniFile_Unified_Colab.ipynb` — Single merged notebook
  - Self-contained (works on Google Colab with just `!pip install`)
  - All bugs fixed
  - 8-tab Gradio UI
  - All features from all 24 notebooks
  - Arabic comments and documentation
  - ~2000-3000 lines of code

### Secondary Output (if new features found):
- New or updated module files in `modules/` or `src/`
- Updated `CHANGELOG.md` entry

### Cleanup:
- `extracted_notebooks/` folder emptied (files deleted)
- Only `output/` and this README remain

---

## 4. Quality Checklist — معايير الجودة

- [ ] No syntax errors — notebook can execute top-to-bottom
- [ ] All 31+ key functions defined (no undefined references)
- [ ] All 6 key classes defined (Config, OCREngine, HandwritingDB, CorrectionRule, SmartMigrator, FileLock)
- [ ] Gradio UI has exactly 8 tabs, all connected
- [ ] No hardcoded secrets/tokens
- [ ] Arabic text properly handled (RTL, reshaping, bidi)
- [ ] Memory management: page-by-page processing, FP16 option, cache clearing
- [ ] Error handling: try/except around OCR, DB, file operations
- [ ] Colab compatible: `IN_COLAB` detection, Drive mount, share=True
- [ ] Backward compatible: doesn't break existing project imports

---

## 5. Notes — ملاحظات

- The project language is **Arabic** — maintain Arabic comments, UI labels, and documentation
- This is a **free, non-profit, open-source** project
- Developer: Dr. Abdulmalek Tamer Al-husseini
- GitHub: https://github.com/DrAbdulmalek/OmniFile_Processor
- Target: Google Colab + HuggingFace Spaces deployment
- والله من وراء القصد
