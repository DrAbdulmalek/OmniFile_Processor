# ============================================
# justfile for OmniFile Processor - Training
# ============================================

set dotenv-load := false

# Default: show available recipes
default:
    @just --list

# --- Testing ---
test: test-htr test-integration test-e2e

test-htr:
    python -m pytest tests/test_htr.py -v --tb=short

test-training:
    python -m pytest tests/test_training.py -v --tb=short

test-integration:
    python -m pytest tests/test_integration.py -v --tb=short

test-e2e:
    python -m pytest tests/test_e2e.py -v --tb=short

# --- Data Preparation ---
prepare-data raw_dir="training/data/raw":
    python training/scripts/prepare_htr_dataset.py \
        --config training/configs/trocr_lora_arabic.yaml \
        --raw-data-dir {{raw_dir}} \
        --output-dir training/data/processed \
        --create-hf

generate-synthetic num_samples="5000":
    python training/scripts/generate_synthetic_data.py \
        --config training/configs/trocr_lora_arabic.yaml \
        --output-dir training/data/synthetic \
        --num-samples {{num_samples}}

merge-data ratio="0.3":
    python training/scripts/generate_synthetic_data.py \
        --merge-with training/data/processed/train \
        --synthetic-ratio {{ratio}}

# --- Training ---
train checkpoint="":
    python training/scripts/train_trocr_lora.py \
        --config training/configs/trocr_lora_arabic.yaml \
        --processed-dir training/data/processed

evaluate checkpoint="training/outputs/trocr_lora_arabic/best_model":
    python training/scripts/evaluate_checkpoint.py \
        --checkpoint {{checkpoint}} \
        --test-dir training/data/processed/test \
        --config training/configs/trocr_lora_arabic.yaml

active-learn checkpoint="training/outputs/trocr_lora_arabic/best_model":
    python training/scripts/active_learning_pipeline.py \
        --config training/configs/trocr_lora_arabic.yaml \
        --checkpoint {{checkpoint}} \
        --unlabeled-pool training/data/unlabeled

# --- Docker ---
build-docker:
    docker build -f Dockerfile.training -t omnifile/training:latest .

run-docker: build-docker
    docker run --gpus all \
        -v $(PWD)/training/data:/app/training/data \
        -v $(PWD)/training/outputs:/app/training/outputs \
        --shm-size=8g omnifile/training:latest

# --- Cleanup ---
clean:
    rm -rf training/outputs/* training/logs/*
    rm -rf training/data/processed/* training/data/synthetic/*
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

# --- Full Pipeline ---
pipeline: prepare-data train evaluate
    @echo "Training pipeline complete!"
