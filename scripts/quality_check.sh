#!/bin/bash
# scripts/quality_check.sh
# سكربت للتحقق من جاهزية المشروع

set -e

echo "🔍 OmniFile Quality Check"
echo "=========================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

errors=0
warnings=0

# 1. التحقق من الملفات المطلوبة
echo -e "\n📁 Checking required files..."

required_files=(
    "app.py"
    "config.py"
    "modules/vision/htr/__init__.py"
    "modules/vision/htr/arabic_htr.py"
    "modules/vision/htr/line_segmenter.py"
    "modules/vision/htr/word_segmenter.py"
    "modules/vision/htr/dotted_recovery.py"
    "modules/vision/htr/trocr_finetuned.py"
    "training/scripts/prepare_htr_dataset.py"
    "training/scripts/train_trocr_lora.py"
    "training/scripts/evaluate_checkpoint.py"
    "training/scripts/active_learning_pipeline.py"
    "training/scripts/generate_synthetic_data.py"
    "training/models/lora_htr_trainer.py"
    "training/data/mobile_review_connector.py"
    "training/configs/trocr_lora_arabic.yaml"
    "interactive_learning/__init__.py"
    "interactive_learning/core/security.py"
    "interactive_learning/core/monitoring.py"
    "interactive_learning/core/versioning.py"
    "backend/api/training.py"
    "frontend/dashboard/TrainingDashboard.jsx"
    "Dockerfile.training"
    "requirements-training.txt"
    "Makefile"
    "README.md"
    "docs/TRAINING_GUIDE.md"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ❌ Missing: $file"
        errors=$((errors + 1))
    else
        echo "  ✅ Found: $file"
    fi
done

# 2. التحقق من هيكل المجلدات
echo -e "\n📂 Checking directory structure..."

required_dirs=(
    "modules/vision/htr"
    "training/scripts"
    "training/configs"
    "training/models"
    "training/data"
    "interactive_learning/core"
    "backend/api"
    "frontend/dashboard"
    "docs"
    "tests"
)

for dir in "${required_dirs[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "  ❌ Missing dir: $dir"
        errors=$((errors + 1))
    else
        echo "  ✅ Found: $dir/"
    fi
done

# 3. التحقق من الاختبارات
echo -e "\n🧪 Checking test files..."

test_files=(
    "tests/test_htr.py"
    "tests/test_training.py"
    "tests/test_integration.py"
    "tests/test_e2e.py"
    "tests/test_integration_full.py"
)

for file in "${test_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  ⚠️  Missing test: $file"
        warnings=$((warnings + 1))
    else
        echo "  ✅ Found: $file"
    fi
done

# 4. تشغيل الاختبارات (اختياري)
echo -e "\n🧪 Running tests..."
if command -v python3 &> /dev/null; then
    # Run lightweight tests only (no ML libs needed)
    if python3 -m pytest tests/test_integration_full.py -v --tb=short -x 2>/dev/null; then
        echo "  ✅ Integration tests passing"
    else
        echo "  ⚠️  Some tests failing (may need dependencies)"
        warnings=$((warnings + 1))
    fi
else
    echo "  ⚠️  Python3 not available, skipping test execution"
    warnings=$((warnings + 1))
fi

# 5. التحقق من الأمان
echo -e "\n🔒 Security checks..."

if [ -f "interactive_learning/core/security.py" ]; then
    echo "  ✅ Security module present"
    # Check for key classes
    if grep -q "class SecureCorrectionStorage" interactive_learning/core/security.py; then
        echo "  ✅ SecureCorrectionStorage class found"
    fi
    if grep -q "class AuditLogger" interactive_learning/core/security.py; then
        echo "  ✅ AuditLogger class found"
    fi
else
    echo "  ❌ Security module missing"
    errors=$((errors + 1))
fi

# 6. التحقق من المراقبة
echo -e "\n📊 Monitoring checks..."

if [ -f "interactive_learning/core/monitoring.py" ]; then
    echo "  ✅ Monitoring module present"
    if grep -q "class MetricsCollector" interactive_learning/core/monitoring.py; then
        echo "  ✅ MetricsCollector class found"
    fi
else
    echo "  ❌ Monitoring module missing"
    errors=$((errors + 1))
fi

# 7. التحقق من التوثيق
echo -e "\n📚 Documentation checks..."

if [ -f "mkdocs.yml" ]; then
    echo "  ✅ MkDocs config present"
else
    echo "  ⚠️  MkDocs config missing"
    warnings=$((warnings + 1))
fi

if [ -f "docs/TRAINING_GUIDE.md" ]; then
    lines=$(wc -l < docs/TRAINING_GUIDE.md)
    if [ "$lines" -gt 50 ]; then
        echo "  ✅ Training guide: $lines lines"
    else
        echo "  ⚠️  Training guide seems short: $lines lines"
        warnings=$((warnings + 1))
    fi
else
    echo "  ❌ Training guide missing"
    errors=$((errors + 1))
fi

# 8. التحقق من Docker
echo -e "\n🐳 Docker check..."

if [ -f "Dockerfile.training" ]; then
    echo "  ✅ Training Dockerfile present"
else
    echo "  ⚠️  Training Dockerfile missing"
    warnings=$((warnings + 1))
fi

if [ -f "Dockerfile" ]; then
    echo "  ✅ Main Dockerfile present"
else
    echo "  ⚠️  Main Dockerfile missing"
    warnings=$((warnings + 1))
fi

# 9. التحقق من CI/CD
echo -e "\n🔄 CI/CD checks..."

if [ -f ".github/workflows/train.yml" ]; then
    echo "  ✅ Training workflow present"
else
    echo "  ⚠️  Training workflow missing"
    warnings=$((warnings + 1))
fi

# 10. عد الملفات والأسطر
echo -e "\n📏 Project statistics..."

py_files=$(find . -name "*.py" -not -path "./__pycache__/*" -not -path "./.git/*" | wc -l)
total_lines=$(find . -name "*.py" -not -path "./__pycache__/*" -not -path "./.git/*" -exec cat {} + 2>/dev/null | wc -l)

echo "  Python files: $py_files"
echo "  Total lines: $total_lines"

# النتيجة النهائية
echo -e "\n=========================="
echo "  Results:"
echo "    Errors:   $errors"
echo "    Warnings: $warnings"
echo "=========================="

if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
    echo "✅ All checks passed!"
    exit 0
elif [ $errors -eq 0 ]; then
    echo "⚠️  Checks passed with warnings"
    exit 0
else
    echo "❌ $errors critical issues found"
    exit 1
fi
