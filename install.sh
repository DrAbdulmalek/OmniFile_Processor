#!/bin/bash
# =============================================================================
# install.sh — المثبت الذكي لـ OmniFile Processor
# =============================================================================
# يكتشف بيئتك ويقترح التثبيت المناسب
# الاستخدام: bash install.sh [خيار]
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"

# =============================================================================
# Helper functions
# =============================================================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  OmniFile Processor — Installer${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

detect_python() {
    if command -v python3.11 &> /dev/null; then
        echo "python3.11"
    elif command -v python3.10 &> /dev/null; then
        echo "python3.10"
    elif command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        return 1
    fi
}

detect_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        echo "cuda"
    elif command -v rocm-smi &> /dev/null; then
        echo "rocm"
    else
        echo "cpu"
    fi
}

detect_platform() {
    case "$(uname -s)" in
        Linux*)     echo "linux" ;;
        Darwin*)    echo "macos" ;;
        MINGW*)     echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

create_venv() {
    PYTHON=$(detect_python)
    if [ -z "$PYTHON" ]; then
        print_error "Python 3.10+ not found. Please install it first."
        exit 1
    fi

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        $PYTHON -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment created at $VENV_DIR"
    else
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
    fi
}

install_requirements() {
    local files="$@"
    echo -e "${BLUE}Installing: ${files}${NC}"

    for file in $files; do
        if [ -f "$PROJECT_ROOT/$file" ]; then
            pip install -r "$PROJECT_ROOT/$file" --quiet
            print_success "Installed $file"
        else
            print_warning "File not found: $file"
        fi
    done
}

verify_installation() {
    echo ""
    echo -e "${BLUE}Verifying installation...${NC}"

    local errors=0

    python -c "import numpy; print(f'  NumPy: {numpy.__version__}')" 2>/dev/null || errors=$((errors+1))
    python -c "import PIL; print(f'  Pillow: {PIL.__version__}')" 2>/dev/null || errors=$((errors+1))
    python -c "import gradio; print(f'  Gradio: {gradio.__version__}')" 2>/dev/null || print_warning "  Gradio: not installed (optional)"

    # Check OCR engines
    python -c "import easyocr; print(f'  EasyOCR: installed')" 2>/dev/null || print_warning "  EasyOCR: not installed"
    python -c "import paddleocr; print(f'  PaddleOCR: installed')" 2>/dev/null || print_warning "  PaddleOCR: not installed"
    python -c "import transformers; print(f'  Transformers: {transformers.__version__}')" 2>/dev/null || print_warning "  Transformers: not installed"

    # Check GPU
    local gpu=$(detect_gpu)
    echo -e "  GPU: ${gpu}"

    if [ $errors -eq 0 ]; then
        print_success "Core installation verified!"
    else
        print_warning "Some optional components are missing"
    fi
}

# =============================================================================
# Main menu
# ============================================================================

print_header

echo ""
echo -e "${YELLOW}Detected environment:${NC}"
echo "  Platform: $(detect_platform)"
echo "  Python:   $(detect_python || echo 'not found')"
echo "  GPU:      $(detect_gpu)"
echo ""

# Parse arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: bash install.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  1 | base       Basic interface only (~500 MB)"
    echo "  2 | ocr        Base + OCR engines (~2.5 GB)"
    echo "  3 | full       Everything (~6.5 GB)"
    echo "  4 | dev        Full + development tools"
    echo "  5 | deploy     Base + deployment tools"
    echo "  --help         Show this help"
    echo ""
    echo "Examples:"
    echo "  bash install.sh 2        # OCR setup"
    echo "  bash install.sh full     # Full installation"
    exit 0
fi

CHOICE="${1:-}"

if [ -z "$CHOICE" ]; then
    echo "Select installation type:"
    echo "  1) Base only (interface, no OCR) — ~500 MB"
    echo "  2) Base + OCR — ~2.5 GB"
    echo "  3) Full (all features) — ~6.5 GB"
    echo "  4) Developer (full + dev tools)"
    echo "  5) Deployment (production)"
    echo ""
    read -p "Enter choice [1-5]: " CHOICE
fi

# Create venv first
create_venv

# Upgrade pip
pip install --upgrade pip setuptools wheel --quiet

case "$CHOICE" in
    1|base)
        echo -e "${BLUE}Installing base packages...${NC}"
        install_requirements "requirements-base.txt"
        ;;
    2|ocr)
        echo -e "${BLUE}Installing OCR packages...${NC}"
        install_requirements "requirements-base.txt" "requirements-ocr-basic.txt"
        ;;
    3|full)
        echo -e "${BLUE}Installing all packages (this may take 15-30 min)...${NC}"
        install_requirements "requirements-base.txt" "requirements-ocr-basic.txt" "requirements-ocr-advanced.txt" "requirements-nlp-arabic.txt" "requirements-ai-gateway.txt"
        ;;
    4|dev)
        echo -e "${BLUE}Installing developer packages...${NC}"
        install_requirements "requirements-base.txt" "requirements-ocr-basic.txt" "requirements-ocr-advanced.txt" "requirements-nlp-arabic.txt" "requirements-ai-gateway.txt" "requirements-deployment.txt"
        if [ -f "requirements-dev.txt" ]; then
            install_requirements "requirements-dev.txt"
        fi
        ;;
    5|deploy)
        echo -e "${BLUE}Installing deployment packages...${NC}"
        install_requirements "requirements-base.txt" "requirements-ocr-basic.txt" "requirements-deployment.txt"
        ;;
    *)
        print_error "Invalid choice: $CHOICE"
        echo "Run 'bash install.sh --help' for options"
        exit 1
        ;;
esac

verify_installation

echo ""
print_success "Installation complete!"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  source .venv/bin/activate"
echo "  python -m modules.ui.gradio_app    # Launch web interface"
echo "  make help                           # See all commands"
