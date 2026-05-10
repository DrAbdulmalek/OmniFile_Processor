# معالجة دفعة من الملفات

## نظرة عامة

يوضح هذا المثال كيفية معالجة مجموعة من الملفات تلقائياً باستخدام Batch Manager مع متابعة التقدم في الوقت الحقيقي.

## المثال 1: معالجة دفعة بسيطة

```python
from backend.batch_manager import BatchManager, BatchConfig

manager = BatchManager(storage_dir="./batch_data")

# إنشاء دفعة
batch = manager.create_batch(
    name="فاتورة مارس 2024",
    config=BatchConfig(
        ocr_engine="trocr",
        language="ar",
        auto_correct=True,
    )
)

# إضافة ملفات
manager.add_files(batch.batch_id, [
    "./invoices/inv_001.pdf",
    "./invoices/inv_002.pdf",
    "./invoices/inv_003.png",
])

# معالجة مع متابعة التقدم
def on_progress(file_id, progress, message):
    print(f"  [{file_id}] {progress}% - {message}")

summary = manager.process_batch(batch.batch_id, progress_callback=on_progress)
print(f"النتيجة: {summary}")

# تصدير النتائج
path = manager.export_results(batch.batch_id, output_format="json")
```

## المثال 2: إعادة معالجة الملفات الفاشلة

```python
# إعادة محاولة الملفات الفاشلة فقط
result = manager.retry_failed(batch.batch_id)

# أو تصدير قائمة الفاشلة للمراجعة اليدوية
for f in batch.files:
    if f["status"] == "failed":
        print(f"فشل: {f['filename']} - {f['error']}")
```

## المثال 3: المعالجة عبر API

```bash
# إنشاء دفعة
curl -X POST http://localhost:8000/api/batch \
  -H "Content-Type: application/json" \
  -d '{"name": "Batch 1", "config": {"ocr_engine": "trocr", "language": "ar"}}'

# رفع ملفات
curl -X POST http://localhost:8000/api/batch/BATCH_ID/files \
  -F "files=@file1.pdf" \
  -F "files=@file2.png"

# بدء المعالجة
curl -X POST http://localhost:8000/api/batch/BATCH_ID/process
```
