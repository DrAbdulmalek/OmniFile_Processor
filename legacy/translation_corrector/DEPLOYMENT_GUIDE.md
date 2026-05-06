# 🚀 دليل النشر الشامل
# Complete Deployment Guide

دليل خطوة بخطوة لنشر نظام معالجة الترجمات العربية على منصات مختلفة

---

## 📋 المحتويات

1. [النشر على Hugging Face Spaces](#1-النشر-على-hugging-face-spaces)
2. [النشر على GitHub](#2-النشر-على-github)
3. [النشر على خادم Linux](#3-النشر-على-خادم-linux)
4. [النشر باستخدام Docker](#4-النشر-باستخدام-docker)
5. [استكشاف الأخطاء](#5-استكشاف-الأخطاء)

---

## 1. النشر على Hugging Face Spaces

### 1.1 إنشاء Space جديد

1. **تسجيل الدخول:**
   - اذهب إلى https://huggingface.co
   - قم بتسجيل الدخول أو إنشاء حساب جديد

2. **إنشاء Space:**
   - اذهب إلى https://huggingface.co/spaces
   - اضغط على زر **"Create new Space"**
   - املأ المعلومات:
     - **Owner**: اسم المستخدم أو المنظمة
     - **Space name**: `arabic-translation-processor` (أو أي اسم تريده)
     - **License**: MIT
     - **Select the Space SDK**: **Gradio**
     - **Space hardware**: CPU (basic) - مجاني
     - **Visibility**: Public أو Private

3. **استنساخ المستودع:**
```bash
# استنساخ Space الجديد
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# إضافة الملفات
cp /path/to/app.py .
cp /path/to/requirements.txt .
cp /path/to/README.md .
cp /path/to/.gitignore .

# رفع الملفات
git add .
git commit -m "Initial deployment"
git push
```

### 1.2 إعداد المتغيرات البيئية

1. اذهب إلى صفحة Space الخاص بك
2. اضغط على **Settings** (⚙️)
3. اذهب إلى قسم **Variables and secrets**
4. أضف Secret جديد:
   - **Name**: `HF_TOKEN`
   - **Value**: [احصل عليه من https://huggingface.co/settings/tokens]
   - **Description**: Hugging Face API Token for dataset access
5. احفظ التغييرات

### 1.3 التحقق من النشر

- انتظر حتى يكتمل البناء (Build)
- سيظهر الرابط: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
- اختبر الواجهة وتأكد من عملها

### 1.4 تحديث Space

```bash
# إجراء تعديلات
# ...

# رفع التحديثات
git add .
git commit -m "Update: description of changes"
git push
```

---

## 2. النشر على GitHub

### 2.1 إنشاء مستودع جديد

1. **إنشاء المستودع:**
   - اذهب إلى https://github.com/new
   - Repository name: `arabic-translation-unified`
   - Description: نظام متكامل لمعالجة الترجمات العربية
   - Visibility: Public
   - ✅ Add a README file (سنستبدله)
   - ✅ Add .gitignore (Python)
   - ✅ Choose a license (MIT)

2. **استنساخ ورفع الملفات:**
```bash
# استنساخ المستودع
git clone https://github.com/YOUR_USERNAME/arabic-translation-unified.git
cd arabic-translation-unified

# نسخ جميع الملفات
cp -r /path/to/project/* .

# رفع الملفات
git add .
git commit -m "Initial commit: Complete unified system"
git push origin main
```

### 2.2 إعداد GitHub Actions (CI/CD) - اختياري

إنشاء `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/
```

### 2.3 إضافة Badges

أضف في `README.md`:

```markdown
[![GitHub](https://img.shields.io/github/license/YOUR_USERNAME/arabic-translation-unified)](https://github.com/YOUR_USERNAME/arabic-translation-unified/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97-Hugging%20Face-yellow)](https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME)
```

---

## 3. النشر على خادم Linux

### 3.1 إعداد الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت المتطلبات الأساسية
sudo apt install -y python3.9 python3.9-venv python3-pip git nginx

# إنشاء مستخدم للتطبيق
sudo useradd -m -s /bin/bash arabic-translator
sudo su - arabic-translator
```

### 3.2 تثبيت التطبيق

```bash
# استنساخ المشروع
cd ~
git clone https://github.com/YOUR_USERNAME/arabic-translation-unified.git
cd arabic-translation-unified

# إنشاء بيئة افتراضية
python3.9 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# إعداد المتغيرات البيئية
cp .env.example .env
nano .env  # أدخل HF_TOKEN الخاص بك
```

### 3.3 إعداد Systemd Service

إنشاء `/etc/systemd/system/arabic-translator.service`:

```ini
[Unit]
Description=Arabic Translation Processor
After=network.target

[Service]
Type=simple
User=arabic-translator
WorkingDirectory=/home/arabic-translator/arabic-translation-unified
Environment="PATH=/home/arabic-translator/arabic-translation-unified/venv/bin"
EnvironmentFile=/home/arabic-translator/arabic-translation-unified/.env
ExecStart=/home/arabic-translator/arabic-translation-unified/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# تفعيل وتشغيل الخدمة
sudo systemctl enable arabic-translator
sudo systemctl start arabic-translator
sudo systemctl status arabic-translator
```

### 3.4 إعداد Nginx كـ Reverse Proxy

إنشاء `/etc/nginx/sites-available/arabic-translator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # أو عنوان IP

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Gradio
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# تفعيل الموقع
sudo ln -s /etc/nginx/sites-available/arabic-translator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.5 إعداد SSL (اختياري لكن موصى به)

```bash
# تثبيت Certbot
sudo apt install certbot python3-certbot-nginx

# الحصول على شهادة SSL
sudo certbot --nginx -d your-domain.com

# التجديد التلقائي
sudo systemctl enable certbot.timer
```

---

## 4. النشر باستخدام Docker

### 4.1 إنشاء Dockerfile

إنشاء `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# تعيين مجلد العمل
WORKDIR /app

# نسخ المتطلبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الملفات
COPY app.py .
COPY README.md .

# إنشاء مستخدم غير root
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

# تحديد المنفذ
EXPOSE 7860

# تشغيل التطبيق
CMD ["python", "app.py"]
```

### 4.2 إنشاء docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: arabic-translator
    ports:
      - "7860:7860"
    environment:
      - HF_TOKEN=${HF_TOKEN}
      - PORT=7860
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7860"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 4.3 بناء وتشغيل

```bash
# بناء الصورة
docker build -t arabic-translator:latest .

# تشغيل الحاوية
docker run -d \
  --name arabic-translator \
  -p 7860:7860 \
  -e HF_TOKEN=your_token_here \
  --restart unless-stopped \
  arabic-translator:latest

# أو باستخدام docker-compose
echo "HF_TOKEN=your_token_here" > .env
docker-compose up -d
```

### 4.4 إدارة الحاوية

```bash
# عرض السجلات
docker logs -f arabic-translator

# إيقاف
docker stop arabic-translator

# إعادة التشغيل
docker restart arabic-translator

# حذف
docker rm -f arabic-translator
```

---

## 5. استكشاف الأخطاء

### المشاكل الشائعة والحلول

#### 1. خطأ: HF_TOKEN not found

**الحل:**
```bash
# تأكد من وجود المتغير البيئي
echo $HF_TOKEN

# إضافته في .env
echo "HF_TOKEN=your_token_here" >> .env

# إعادة تشغيل التطبيق
```

#### 2. خطأ: ModuleNotFoundError

**الحل:**
```bash
# تحديث pip
pip install --upgrade pip

# إعادة تثبيت المتطلبات
pip install -r requirements.txt --force-reinstall
```

#### 3. خطأ: Port already in use

**الحل:**
```bash
# العثور على العملية
sudo lsof -i :7860

# إيقاف العملية
sudo kill -9 PID

# أو تغيير المنفذ في .env
echo "PORT=7861" >> .env
```

#### 4. بطء المعالجة

**الحلول:**
- زيادة `batch_size`
- استخدام خادم أقوى
- تفعيل التخزين المؤقت
- تقليل عدد القواعد المطبقة

#### 5. خطأ في الاتصال بـ Hugging Face

**الحل:**
```bash
# التحقق من الاتصال
curl https://huggingface.co

# التحقق من صلاحية التوكن
curl -H "Authorization: Bearer $HF_TOKEN" \
  https://huggingface.co/api/whoami-v2
```

### سجلات التشخيص

#### Systemd
```bash
sudo journalctl -u arabic-translator -f
```

#### Docker
```bash
docker logs -f arabic-translator
```

#### Nginx
```bash
sudo tail -f /var/log/nginx/error.log
```

---

## 📊 مراقبة الأداء

### استخدام htop
```bash
sudo apt install htop
htop
```

### استخدام Prometheus + Grafana (متقدم)

إضافة مراقبة متقدمة:
```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 🔒 أمان النشر

### توصيات الأمان

1. **لا تشارك HF_TOKEN علناً**
2. **استخدم HTTPS في الإنتاج**
3. **حدّث التطبيق بانتظام**
4. **استخدم Firewall**:
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```
5. **راقب السجلات بانتظام**

---

## 📞 الدعم

إذا واجهت مشاكل:
- 📖 [التوثيق الكامل](https://github.com/DrAbdulmalek/arabic-translation-unified/wiki)
- 🐛 [فتح Issue](https://github.com/DrAbdulmalek/arabic-translation-unified/issues)
- 💬 [منتدى النقاش](https://github.com/DrAbdulmalek/arabic-translation-unified/discussions)

---

**نهاية الدليل** ✅

<div align="center">

**صُنع بـ ❤️ للغة العربية**

</div>
