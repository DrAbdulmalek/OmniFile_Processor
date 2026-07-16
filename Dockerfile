FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements-hf.txt .
RUN pip install --no-cache-dir -r requirements-hf.txt

# Copy all project files
COPY . .

# Expose Gradio default port
EXPOSE 7860

# Health check
HEALTHCHECK CMD curl -f http://localhost:7860/ || exit 1

# Run Gradio HF Spaces app
CMD ["python", "hf_app.py"]
