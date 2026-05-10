# =============================================================================
# OmniFile Makefile
# =============================================================================
#
# أوامر سهلة للتطوير والنشر

.PHONY: help install dev test lint format clean build docker-up docker-down deploy test-env test-basic test-segmentation test-interactive test-all test-coverage test-performance dev-setup dev-test dev-clean

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# =============================================================================
# Help
# =============================================================================
help: ## عرض هذه المساعدة
        @echo "$(BLUE)OmniFile HTR System$(NC)"
        @echo "===================="
        @echo ""
        @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Development
# =============================================================================
install: ## تثبيت dependencies
        @echo "$(BLUE)تثبيت dependencies...$(NC)"
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

dev: install ## إعداد بيئة التطوير
        @echo "$(BLUE)إعداد بيئة التطوير...$(NC)"
        pre-commit install
        cp .env.example .env
        @echo "$(GREEN)✅ جاهز للتطوير!$(NC)"

# =============================================================================
# Testing
# =============================================================================
test: ## تشغيل جميع الاختبارات
        @echo "$(BLUE)تشغيل الاختبارات...$(NC)"
        pytest tests/ -v --tb=short

test-cov: ## تشغيل الاختبارات مع coverage
        @echo "$(BLUE)تشغيل الاختبارات مع coverage...$(NC)"
        pytest tests/ -v --cov=api_server_v2 --cov=training --cov-report=html --cov-report=term

test-api: ## اختبار API فقط
        @echo "$(BLUE)اختبار API...$(NC)"
        pytest tests/api/ -v

test-training: ## اختبار التدريب فقط
        @echo "$(BLUE)اختبار التدريب...$(NC)"
        pytest tests/training/ -v

# =============================================================================
# Testing & Development Scripts
# =============================================================================
test-env: ## إعداد بيئة الاختبار
        @echo "$(BLUE)Setting up test environment...$(NC)"
        python scripts/setup_test_env.py
        @echo "$(GREEN)Test environment ready$(NC)"

test-basic: test-env ## الاختبار الأساسي
        @echo "$(BLUE)Running basic tests...$(NC)"
        python scripts/test_basic.py

test-segmentation: test-env ## اختبار التقسيم
        @echo "$(BLUE)Running segmentation tests...$(NC)"
        python scripts/test_segmentation.py

test-interactive: test-env ## اختبار الوضع التفاعلي
        @echo "$(BLUE)Running interactive tests...$(NC)"
        python scripts/test_interactive.py

test-all: test-env ## جميع الاختبارات التدريجية
        @echo "$(BLUE)Running all script tests...$(NC)"
        @echo "$(YELLOW)1. Basic tests$(NC)"
        @python scripts/test_basic.py || true
        @echo ""
        @echo "$(YELLOW)2. Segmentation tests$(NC)"
        @python scripts/test_segmentation.py || true
        @echo ""
        @echo "$(YELLOW)3. Interactive tests$(NC)"
        @python scripts/test_interactive.py || true
        @echo ""
        @echo "$(GREEN)All test suites completed$(NC)"

test-coverage: test-env ## الاختبار مع التغطية
        @echo "$(BLUE)Running tests with coverage...$(NC)"
        pytest tests/ scripts/test_*.py \
                --cov=interactive_learning \
                --cov-report=html:test_data/output/coverage \
                --cov-report=term

test-performance: test-env ## اختبار الأداء
        @echo "$(BLUE)Running performance tests...$(NC)"
        python -c "
import time
from interactive_learning import InteractiveLearningSystem
import cv2
import numpy as np

system = InteractiveLearningSystem(learning_mode=False)

times = []
for i in range(5):
    img = np.ones((400, 800, 3), dtype=np.uint8) * 255
    cv2.putText(img, f'Test {i}', (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (0,0,0), 3)
    start = time.time()
    system.process_page_from_array(img)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f'  Run {i+1}: {elapsed:.2f}s')

print(f'Average: {sum(times)/len(times):.2f}s')
print(f'Min: {min(times):.2f}s')
print(f'Max: {max(times):.2f}s')
"

# =============================================================================
# Development Helpers
# =============================================================================
dev-setup: ## إعداد بيئة التطوير الكاملة
        @echo "$(BLUE)Setting up development environment...$(NC)"
        make install
        make test-env
        pre-commit install || echo "pre-commit not installed"
        @echo "$(GREEN)Development environment ready$(NC)"

dev-test: ## اختبار سريع أثناء التطوير
        @echo "$(BLUE)Quick development test...$(NC)"
        python -c "
from interactive_learning import InteractiveLearningSystem
print('Import successful')
system = InteractiveLearningSystem(learning_mode=False)
print('System initialized')
"

dev-clean: ## تنظيف ملفات التطوير
        @echo "$(BLUE)Cleaning development files...$(NC)"
        rm -rf test_data/temp_*
        rm -rf __pycache__ .pytest_cache
        find . -name '*.pyc' -delete
        @echo "$(GREEN)Cleaned$(NC)"

# =============================================================================
# Code Quality
# =============================================================================
lint: ## فحص الكود
        @echo "$(BLUE)فحص الكود...$(NC)"
        flake8 api_server_v2/ training/ --count --statistics
        mypy api_server_v2/ training/ --ignore-missing-imports

format: ## تنسيق الكود
        @echo "$(BLUE)تنسيق الكود...$(NC)"
        black api_server_v2/ training/ tests/
        isort api_server_v2/ training/ tests/

format-check: ## التحقق من التنسيق
        @echo "$(BLUE)التحقق من التنسيق...$(NC)"
        black --check api_server_v2/ training/ tests/
        isort --check-only api_server_v2/ training/ tests/

# =============================================================================
# Docker
# =============================================================================
docker-build: ## بناء Docker images
        @echo "$(BLUE)بناء Docker images...$(NC)"
        docker build -t omnifile/api:latest -f deployment/docker/Dockerfile.api .
        docker build -t omnifile/training:latest -f deployment/docker/Dockerfile.training .

docker-up: ## تشغيل Docker Compose
        @echo "$(BLUE)تشغيل Docker Compose...$(NC)"
        docker-compose -f deployment/docker/docker-compose.yml up -d

docker-down: ## إيقاف Docker Compose
        @echo "$(BLUE)إيقاف Docker Compose...$(NC)"
        docker-compose -f deployment/docker/docker-compose.yml down

docker-logs: ## عرض logs
        @echo "$(BLUE)عرض logs...$(NC)"
        docker-compose -f deployment/docker/docker-compose.yml logs -f

# =============================================================================
# Kubernetes
# =============================================================================
k8s-deploy: ## نشر على Kubernetes
        @echo "$(BLUE)نشر على Kubernetes...$(NC)"
        kubectl apply -f deployment/k8s/namespace.yaml
        kubectl apply -f deployment/k8s/
        kubectl wait --for=condition=ready pod -l app=omnifile-api --timeout=300s

k8s-delete: ## حذف من Kubernetes
        @echo "$(RED)حذف من Kubernetes...$(NC)"
        kubectl delete namespace omnifile

k8s-logs: ## عرض logs من Kubernetes
        @echo "$(BLUE)عرض logs...$(NC)"
        kubectl logs -l app=omnifile-api -n omnifile --tail=100 -f

k8s-port-forward: ## Port forward للـ API
        @echo "$(BLUE)Port forward...$(NC)"
        kubectl port-forward svc/omnifile-api 8000:80 -n omnifile

# =============================================================================
# Training
# =============================================================================
train-local: ## تدريب محلي
        @echo "$(BLUE)تدريب محلي...$(NC)"
        python -m training.scripts.train_trocr_lora --config config/training/default.yaml

train-docker: ## تدريب في Docker
        @echo "$(BLUE)تدريب في Docker...$(NC)"
        docker run --gpus all -it \
                -v $(PWD)/data:/workspace/data \
                -v $(PWD)/outputs:/workspace/outputs \
                omnifile/training:latest

train-sagemaker: ## تدريب على SageMaker
        @echo "$(BLUE)تدريب على SageMaker...$(NC)"
        python training/cloud/aws_sagemaker.py $(DATASET_PATH)

train-vertex: ## تدريب على Vertex AI
        @echo "$(BLUE)تدريب على Vertex AI...$(NC)"
        python training/cloud/google_vertex.py $(DATASET_PATH)

train-azure: ## تدريب على Azure ML
        @echo "$(BLUE)تدريب على Azure ML...$(NC)"
        python training/cloud/azure_ml.py $(DATASET_PATH)

# =============================================================================
# Reports
# =============================================================================
report: ## توليد تقرير
        @echo "$(BLUE)توليد تقرير...$(NC)"
        python training/reports/generate_report.py $(CHECKPOINT_DIR)

# =============================================================================
# Mobile App
# =============================================================================
mobile-install: ## تثبيت تطبيق الموبايل
        @echo "$(BLUE)تثبيت تطبيق الموبايل...$(NC)"
        cd mobile_review_v2 && npm install

mobile-start: ## تشغيل تطبيق الموبايل
        @echo "$(BLUE)تشغيل تطبيق الموبايل...$(NC)"
        cd mobile_review_v2 && npx expo start

mobile-build-android: ## بناء APK
        @echo "$(BLUE)بناء APK...$(NC)"
        cd mobile_review_v2 && npx expo build:android

mobile-build-ios: ## بناء IPA
        @echo "$(BLUE)بناء IPA...$(NC)"
        cd mobile_review_v2 && npx expo build:ios

# =============================================================================
# Database
# =============================================================================
db-migrate: ## ترحيل قاعدة البيانات
        @echo "$(BLUE)ترحيل قاعدة البيانات...$(NC)"
        alembic upgrade head

db-rollback: ## التراجع عن الترحيل
        @echo "$(YELLOW)التراجع عن الترحيل...$(NC)"
        alembic downgrade -1

db-reset: ## إعادة تعيين قاعدة البيانات
        @echo "$(RED)إعادة تعيين قاعدة البيانات...$(NC)"
        alembic downgrade base
        alembic upgrade head

# =============================================================================
# Utilities
# =============================================================================
clean: ## تنظيف الملفات المؤقتة
        @echo "$(BLUE)تنظيف...$(NC)"
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete
        find . -type f -name "*.pyo" -delete
        find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        rm -rf .pytest_cache/ .mypy_cache/ htmlcov/ dist/ build/
        rm -rf logs/*.log

clean-all: clean ## تنظيف شامل
        @echo "$(RED)تنظيف شامل...$(NC)"
        rm -rf node_modules/
        rm -rf mobile_review_v2/node_modules/
        docker system prune -f

env: ## إنشاء ملف .env
        @echo "$(BLUE)إنشاء .env...$(NC)"
        cp .env.example .env
        @echo "$(GREEN)✅ تم إنشاء .env - قم بتحريره!$(NC)"

# =============================================================================
# Documentation
# =============================================================================
docs-serve: ## تشغيل docs محلياً
        @echo "$(BLUE)تشغيل docs...$(NC)"
        mkdocs serve

docs-build: ## بناء docs
        @echo "$(BLUE)بناء docs...$(NC)"
        mkdocs build

docs-deploy: ## نشر docs
        @echo "$(BLUE)نشر docs...$(NC)"
        mkdocs gh-deploy

# =============================================================================
# Release
# =============================================================================
version: ## عرض الإصدار الحالي
        @echo "$(BLUE)الإصدار:$(NC)"
        @python -c "import api_server_v2; print(api_server_v2.__version__)"

bump-patch: ## رفع patch version
        @echo "$(BLUE)رفع patch version...$(NC)"
        bumpversion patch

bump-minor: ## رفع minor version
        @echo "$(BLUE)رفع minor version...$(NC)"
        bumpversion minor

bump-major: ## رفع major version
        @echo "$(BLUE)رفع major version...$(NC)"
        bumpversion major

# =============================================================================
# Monitoring
# =============================================================================
logs: ## عرض logs
        @echo "$(BLUE)عرض logs...$(NC)"
        tail -f logs/*.log

metrics: ## عرض المقاييس
        @echo "$(BLUE)عرض المقاييس...$(NC)"
        curl -s http://localhost:8000/metrics | grep -E "^(cer|wer|accuracy|latency)"

health: ## فحص الصحة
        @echo "$(BLUE)فحص الصحة...$(NC)"
        curl -s http://localhost:8000/health | python -m json.tool
