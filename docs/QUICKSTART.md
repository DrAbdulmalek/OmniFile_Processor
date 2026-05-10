# Quick Start Guide - 5 Minutes

## Step 1: Setup (2 minutes)

```bash
# Clone
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Step 2: Setup Data (1 minute)

```bash
# Generate test data
make test-env
# or: python scripts/setup_test_env.py
```

## Step 3: First Test (1 minute)

```bash
# Basic test
make test-basic
```

## Step 4: Interactive Trial (1 minute)

```bash
# Test with real image
python -c "
from interactive_learning import InteractiveLearningSystem
from pathlib import Path

system = InteractiveLearningSystem(learning_mode=False)

# Process image from sample data
layout = system.process_page('test_data/images/simple_text.jpg')
print(f'Found {len(system._all_words())} words')

# Render HTML
output = system.render_with_layout(format='html')
print(f'Output: {output}')
"
```

## Step 5: Interactive Learning (optional - time varies)

```bash
# Full teaching mode
python -c "
from interactive_learning import InteractiveLearningSystem

system = InteractiveLearningSystem(learning_mode=True)
system.process_page('test_data/images/handwritten.jpg')

# Opens Tkinter UI for interactive correction
# system.teaching_mode(ui_type='desktop')
"
```

## Directory Structure After Setup

```
OmniFile_Processor/
├── test_data/
│   ├── images/           # Sample images
│   │   ├── simple_text.jpg
│   │   ├── with_table.jpg
│   │   ├── with_diagram.jpg
│   │   └── mixed_content.jpg
│   ├── output/           # Test outputs
│   └── models/           # Saved models
├── test_logs/            # Logs
└── test_config.json      # Configuration
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make test-basic` | Basic tests |
| `make test-segmentation` | Table and diagram detection tests |
| `make test-interactive` | Interactive mode tests |
| `make test-all` | All tests |
| `make dev-test` | Quick dev test |
| `make dev-clean` | Clean up |

## Troubleshooting

**Problem:** `ModuleNotFoundError`
**Solution:**
```bash
pip install -e .
# or: pip install -e ./interactive_learning
```

**Problem:** `CUDA out of memory`
**Solution:**
```python
system = InteractiveLearningSystem(device="cpu")  # Use CPU
```

**Problem:** Model won't load
**Solution:**
```bash
# Manual download
python -c "
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
"
```

## Next Steps

1. **Try your images**: Place images in `test_data/images/` and try `system.process_page()`
2. **Interactive correction**: Try `system.teaching_mode()` with a real interface
3. **Training**: After 10+ corrections, run `system.learn_from_corrections(force=True)`
4. **Deployment**: Use `make docker-up` for the full version

## Support

- [GitHub Issues](https://github.com/DrAbdulmalek/OmniFile_Processor/issues)
- [Discord](https://discord.gg/omnifile)
- contact@omnifile.app
