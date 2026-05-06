# استخدام صورة Python رسمية
FROM python:3.10-slim

# تعيين مجلد العمل
WORKDIR /app

# تثبيت التبعيات النظام
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    libtesseract-dev \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات التبعيات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# تعريض المنفذ
EXPOSE 5001

# تشغيل الخادم
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
