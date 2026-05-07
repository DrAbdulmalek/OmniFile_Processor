# Forgetting Prevention Guide
# Data mixing strategy for preventing catastrophic forgetting in OCR training.

## Key Concepts

### 1. Data Mixing (data_mixing.py)
Automatically mixes old and new training data using L1 distance metrics.
- Default mix ratio: 0.2 (20% old data)
- Safety ceiling: 0.7 (max 70% old data)

### 2. Logistic Mixing (logistic_mixing.md)
Smooth transitions using logistic function:
- Low drift: minimal old data needed
- High drift: proportionally more old data
- Safety ceiling prevents excessive old data

### 3. Drift Reset Threshold
When drift exceeds threshold:
- Archives current cycle
- Resets drift metrics
- Creates fresh baseline snapshot

### 4. Baseline Snapshot (baseline_snapshot.json)
Stratified sample permanently preserved (5% of data).
Ensures model never forgets fundamental patterns.

### 5. Unsloth Pipeline (unsloth_pipeline.py)
Fast training in ~12 minutes on Colab:
- 4-bit quantization
- LoRA fine-tuning
- Optimized for Arabic OCR

### 6. Decay Tracker (decay_tracker.py)
Dynamic confidence decay with model alignment factor.
