# OmniFile AI Processor - API Documentation

## Base URL

```
http://localhost:5001
```

Interactive docs available at:
- Swagger UI: `http://localhost:5001/docs`
- ReDoc: `http://localhost:5001/redoc`

---

## Endpoints

### 1. Health Check

**GET** `/health`

Response:
```json
{
  "status": "healthy",
  "engines": [...],
  "uptime": 1234567890.123
}
```

### 2. Available Engines

**GET** `/engines`

Response:
```json
{
  "engines": [
    {"name": "EasyOCR", "available": true, "enabled": true, "loaded": false},
    {"name": "TrOCR", "available": true, "enabled": true, "loaded": false},
    {"name": "Tesseract", "available": true, "enabled": true, "loaded": true},
    {"name": "PaddleOCR", "available": false, "enabled": false, "loaded": false}
  ]
}
```

### 3. System Configuration

**GET** `/api/config`

Response:
```json
{
  "supported_languages": ["en", "ar", "de"],
  "enable_summarization": true,
  "enable_translation": true,
  "dark_mode": true,
  "ocr_engines": ["trocr", "easyocr", "tesseract", "paddleocr"]
}
```

### 4. OCR Processing

**POST** `/api/ocr/process`

Content-Type: `multipart/form-data`

Parameters:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | File | Yes | - | Image or PDF file |
| languages | string | No | "en,ar" | Comma-separated language codes |
| engines | string | No | "easyocr,trocr" | Comma-separated engine names |
| preprocess | boolean | No | true | Apply image preprocessing |

Response:
```json
{
  "success": true,
  "text": "Extracted text here...",
  "confidence": 0.95,
  "languages": ["en", "ar"],
  "engines": ["easyocr", "trocr"],
  "filename": "document.png"
}
```

### 5. Spell Correction

**POST** `/api/ocr/correct`

Content-Type: `application/json`

Request:
```json
{
  "text": "helloo world testt",
  "lang": "en"
}
```

Response:
```json
{
  "success": true,
  "original_text": "helloo world testt",
  "corrected_text": "hello world test",
  "corrections": [
    {"original": "helloo", "corrected": "hello", "position": 0},
    {"original": "testt", "corrected": "test", "position": 13}
  ],
  "total_corrections": 2
}
```

### 6. Translation

**POST** `/api/nlp/translate`

Content-Type: `application/json`

Request:
```json
{
  "text": "Hello world",
  "source_lang": "en",
  "target_lang": "ar"
}
```

Response:
```json
{
  "success": true,
  "original_text": "Hello world",
  "translated_text": "مرحبا بالعالم",
  "source_lang": "en",
  "target_lang": "ar",
  "model": "Helsinki-NLP/opus-mt"
}
```

### 7. Summarization

**POST** `/api/nlp/summarize`

Content-Type: `application/json`

Request:
```json
{
  "text": "Long text to summarize...",
  "lang": "auto",
  "max_length": 130,
  "min_length": 30
}
```

Response:
```json
{
  "success": true,
  "original_text": "Long text...",
  "summary": "Summary text...",
  "lang": "en"
}
```

### 8. OCR Evaluation (CER/WER)

**POST** `/api/evaluate`

Content-Type: `application/json`

Request:
```json
{
  "reference_text": "The correct text",
  "ocr_text": "The ocr text"
}
```

Response:
```json
{
  "success": true,
  "cer": 0.15,
  "wer": 0.2,
  "accuracy": 85.0,
  "quality_grade": "B+",
  "recommendations": []
}
```

### 9. AI Text Improvement

**POST** `/api/ai/improve`

Content-Type: `multipart/form-data`

Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| text | string | Yes | Text to improve |
| language | string | No | Language code (default: "ar") |
| context | string | No | Additional context for correction |

### 10. Batch Processing

**POST** `/api/batch/process`

Content-Type: `multipart/form-data`

Parameters:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| files | File[] | Yes | Multiple image/PDF files |
| languages | string | No | Comma-separated language codes |

### 11. Task Status

**GET** `/api/tasks/{task_id}`

Response:
```json
{
  "status": "completed",
  "total": 5,
  "completed": 5,
  "results": [...]
}
```

---

## Supported Languages

| Code | Language | OCR | Spell Check | Translation | Summarization |
|------|----------|-----|-------------|-------------|---------------|
| en | English | Yes | Yes | Yes | Yes (BART) |
| ar | Arabic | Yes | Yes | Yes | Yes (mBART) |
| de | German | Yes | Yes | Yes | Yes (mT5) |

## Error Codes

| Status | Description |
|--------|-------------|
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (task/resource) |
| 413 | File Too Large (max 50MB) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (AI features require API key) |
