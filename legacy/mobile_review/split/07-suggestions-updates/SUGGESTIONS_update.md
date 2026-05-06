# 📋 **ملف الاقتراحات - OmniFile AI Processor v3.0**
**قائمة شاملة بالاقتراحات لتحسين المشروع وتطويره**

---

## 📌 **فهرس المحتويات**
1. [مراجعة نتائج OCR على الموبايل](#1-مراجعة-نتائج-ocr-على-الموبايل)
2. [حفظ تنسيق النص](#2-حفظ-تنسيق-النص)
3. [تحسين دقة نماذج OCR العربية](#3-تحسين-دقة-نماذج-ocr-العربية)
4. [اقتراحات أخرى](#4-اقتراحات-أخرى)
5. [خطة العمل](#5-خطة-العمل)

---

---

## 📱 **1. مراجعة نتائج OCR على الموبايل**

### **🎯 الهدف العام**
تمكين المستخدمين من **مراجعة نتائج OCR** على **الهواتف الذكية** (خصوصًا Android) بشكل **مريح وسهل**، خاصة للمستخدمين الذين يعملون في **الميدان** أو **البحث الميداني**. هذا سيحسن من **دقة نماذج OCR العربية** من خلال **التعلم من تصحيحات المستخدمين** في بيئة **مرنة وسهلة الاستخدام**.

---

### **📌 المشكلات الحالية**
| **المشكلة** | **التأثير** | **الحل المقترح** |
|------------|--------------|------------------|
| **لا يوجد تطبيق موبايل** | صعوبة مراجعة النتائج خارج المكتب | تطوير تطبيق Android/iOS |
| **العمل على الحاسوب غير مريح** | عدم القدرة على العمل في الميدان | دعم العمل على الموبايل |
| **مراجعة النصوص العربية صعبة** | عدم دعم RTL في بعض التطبيقات | استخدام Flutter + RTL |
| **لا يوجد مزامنة مع السحابة** | فقدان البيانات عند تغيير الجهاز | مزامنة مع خادم OmniFile |
| **لا يوجد دعم للعمل بدون إنترنت** | عدم القدرة على العمل في المناطق النائية | حفظ البيانات محليًا |

---

### **🔧 الحل المقترح: تطبيق Android باستخدام Flutter**

#### **✅ لماذا Flutter؟**
1. **متعدد المنصات**: دعم **Android + iOS** من نفس الكود.
2. **دعم RTL**: دعم كامل **للغة العربية** (من اليمين إلى اليسار).
3. **واجهة جميلة**: **Material Design** احترافي.
4. **سهل التطوير**: **Dart + Hot Reload** يسهل التطوير.
5. **أداء جيد**: **Native Performance** على معظم الأجهزة.

---

#### **📋 الميزات المطلوبة للتطبيق**

| **الميزة** | **الوصف** | **الأولوية** | **الحالة** | **التفاصيل** |
|------------|-----------|--------------|------------|--------------|
| **رفع الملفات** | رفع صور/PDF من المعرض أو الكاميرا | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | دعم PNG, JPG, PDF |
| **مراجعة النصوص** | عرض النص المستخرج مع إمكانية التعديل | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | محرر نصوص غني (Quill) |
| **دعم RTL** | دعم كامل للغة العربية | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | اتجاه النص من اليمين إلى اليسار |
| **اقتراحات التصحيح** | عرض اقتراحات لتصحيح الأخطاء الإملائية | ⭐⭐⭐⭐ | ✅ **مبرمج** | باستخدام API أو قاعدة بيانات محلية |
| **حفظ التعديلات** | حفظ التعديلات في قاعدة البيانات | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | مزامنة مع الخادم أو حفظ محلي |
| **المزامنة مع السحابة** | مزامنة البيانات مع خادم OmniFile | ⭐⭐⭐⭐ | ⬜ **غير مبرمج** | استخدام Firebase أو API مخصص |
| **دعم العمل بدون إنترنت** | حفظ البيانات محليًا | ⭐⭐⭐ | ⬜ **غير مبرمج** | SQLite + مزامنة لاحقة |
| **دعم الجداول** | عرض الجداول بشكل صحيح | ⭐⭐⭐⭐ | ✅ **مبرمج** | باستخدام TableWidget |
| **دعم الصور** | عرض الصور المضمنة في النص | ⭐⭐⭐ | ✅ **مبرمج** | باستخدام ImageWidget |
| **البحث في النص** | البحث عن كلمات في النص | ⭐⭐⭐ | ⬜ **غير مبرمج** | استخدام TextField + Highlighting |
| **تصدير النتائج** | تصدير النص إلى PDF/DOCX | ⭐⭐⭐ | ⬜ **غير مبرمج** | استخدام API التصدير |
| **دعم Voice Input** | إدخال نص عبر الصوت | ⭐⭐ | ⬜ **غير مبرمج** | استخدام Speech-to-Text |
| **دعم Dark Mode** | الوضع الداكن | ⭐⭐⭐ | ✅ **مبرمج** | باستخدام ThemeData.dark() |
| **دعم Multiple Languages** | دعم عدة لغات | ⭐⭐⭐ | ✅ **مبرمج** | EN, AR, DE |
| **دعم Zoom** | تكبير النص | ⭐⭐⭐ | ✅ **مبرمج** | باستخدام PhotoView للصور |
| **دعم Undo/Redo** | تراجع/إعادة | ⭐⭐⭐⭐ | ✅ **مبرمج** | باستخدام QuillController |
| **دعم Keyboard Shortcuts** | اختصارات لوحة المفاتيح | ⭐⭐ | ⬜ **غير مبرمج** | Ctrl+Z, Ctrl+Y, etc. |

---

#### **🏗️ هيكل المشروع**
```
omnifile_mobile/
├── lib/
│   ├── main.dart                 # نقطة الدخول
│   ├── screens/
│   │   ├── home_screen.dart      # الشاشة الرئيسية
│   │   ├── review_screen.dart    # شاشة مراجعة OCR
│   │   ├── document_list_screen.dart # قائمة المستندات
│   │   └── settings_screen.dart # الإعدادات
│   ├── models/
│   │   ├── document.dart         # نموذج المستند
│   │   └── ocr_result.dart       # نموذج نتيجة OCR
│   ├── services/
│   │   ├── api_service.dart      # اتصال مع Backend
│   │   ├── database_service.dart # قاعدة بيانات محلية
│   │   └── file_service.dart     # معالج الملفات
│   ├── widgets/
│   │   ├── text_editor.dart       # محرر النصوص
│   │   ├── correction_suggestions.dart # اقتراحات التصحيح
│   │   ├── table_widget.dart      # عرض الجداول
│   │   └── image_widget.dart      # عرض الصور
│   └── utils/
│       ├── format_utils.dart      # أدوات التنسيق
│       └── constants.dart         # الثوابت
├── assets/
│   └── images/                   # الصور
├── pubspec.yaml                  # تبعيات المشروع
└── android/                      # إعدادات Android
    └── app/
        └── build.gradle
```

---

#### **🔧 تقنية التطوير**
| **العنصر** | **التكنولوجيا** | **السبب** | **الحالة** |
|------------|------------------|-----------|------------|
| **واجهة المستخدم** | Flutter | دعم Android + iOS + RTL | ✅ **مستخدم** |
| **Backend API** | FastAPI | سهل التطوير + دعم Async | ✅ **مستخدم** |
| **قاعدة البيانات** | SQLite | خفيفة + لا تحتاج إلى خادم | ✅ **مستخدم** |
| **المزامنة** | Firebase / Custom API | مزامنة البيانات مع السحابة | ⬜ **مقترح** |
| **تخزين الملفات** | Firebase Storage / Local Storage | حفظ الصور والملفات | ⬜ **مقترح** |
| **المصادقة** | JWT | مصادقة آمنة | ⬜ **مقترح** |

---

#### **📦 التبعيات المطلوبة (pubspec.yaml)**
```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
  http: ^1.1.0               # لاتصال API
  shared_preferences: ^2.2.2 # لحفظ الإعدادات
  sqflite: ^2.3.0           # لقاعدة البيانات المحلية
  path_provider: ^2.1.1     # للحصول على مسارات الملفات
  flutter_quill: ^8.0.0     # محرر نصوص غني (دعم RTL)
  image_picker: ^1.0.4     # لاختيار الصور من المعرض
  camera: ^0.10.5          # لالتقاط الصور
  file_picker: ^5.3.3       # لاختيار الملفات
  flutter_localizations:   # دعم RTL
    sdk: flutter
  intl: ^0.18.1             # للترجمة
  provider: ^6.0.5          # لإدارة الحالة
  cached_network_image: ^3.3.0 # لتحميل الصور من الإنترنت
  photo_view: ^0.14.0       # لعرض الصور بتكبير
  url_launcher: ^6.1.11    # لفتح الروابط
  flutter_pdfview: ^2.0.1  # لعرض ملفات PDF
  open_filex: ^4.0.0       # لفتح الملفات
  path: ^1.8.3             # لمعالجة المسارات
```

---

#### **🚀 خطوات التنفيذ**

##### **1. تطوير Backend API (FastAPI)**
**الهدف**: إنشاء API لتقديم خدمات:
- **رفع الملفات** (`POST /api/documents/upload`)
- **استعادة المستندات** (`GET /api/documents`)
- **حفظ التعديلات** (`POST /api/documents/{id}/corrections`)
- **حفظ الاقتراحات** (`POST /api/suggestions`)
- **تصدير المستندات** (`POST /api/documents/{id}/export`)

**المتطلبات**:
- FastAPI
- Uvicorn
- SQLAlchemy (اختياري)

**مثال على الكود**:
```python
# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import os
from pathlib import Path

app = FastAPI(title="OmniFile Mobile API")

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# نموذج للمستند
class DocumentBase(BaseModel):
    file_name: str
    raw_text: str
    processed_text: str = ""
    page_count: int = 1
    language: str = "ar"
    confidence: float = 0.0
    status: str = "pending_review"

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: str
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# قاعدة بيانات مؤقتة (في التطبيق الحقيقي، استخدم SQLite أو PostgreSQL)
documents_db = {}

@app.post("/api/documents/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    language: str = "ar",
    engines: str = "trocr,easyocr,tesseract"
):
    """رفع ملف ومعالجته باستخدام OCR."""
    try:
        # قراءة الملف
        contents = await file.read()

        # معالج OCR (مثال مبسط)
        from modules.vision.ocr_engine import OCREngine
        ocr_engine = OCREngine(
            enable_trocr="trocr" in engines,
            enable_easyocr="easyocr" in engines,
            enable_tesseract="tesseract" in engines,
            use_gpu=False
        )

        # معالج الصورة
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(contents))
        result = ocr_engine.recognize(img, languages=[language])

        # حفظ الملف مؤقتًا
        file_id = str(uuid.uuid4())
        file_path = f"uploads/{file_id}_{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(contents)

        # إنشاء مستند
        doc = Document(
            id=file_id,
            file_name=file.filename,
            file_path=file_path,
            raw_text=result["text"],
            processed_text=result["text"],
            language=language,
            confidence=result["confidence"],
            status="pending_review",
            created_at=datetime.now()
        )

        documents_db[file_id] = doc
        return doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=List[Document])
async def get_documents(
    limit: int = 20,
    offset: int = 0,
    status: str = "pending_review"
):
    """استعادة قائمة المستندات."""
    docs = list(documents_db.values())
    if status != "all":
        docs = [doc for doc in docs if doc.status == status]
    return docs[offset:offset+limit]

@app.get("/api/documents/{doc_id}", response_model=Document)
async def get_document(doc_id: str):
    """استعادة مستند معين."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    return documents_db[doc_id]

@app.post("/api/documents/{doc_id}/corrections")
async def save_corrections(
    doc_id: str,
    corrected_text: str
):
    """حفظ التعديلات على مستند."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]
    doc.processed_text = corrected_text
    doc.status = "reviewed"
    doc.updated_at = datetime.now()
    documents_db[doc_id] = doc

    return {"status": "success"}

@app.post("/api/documents/{doc_id}/mark_reviewed")
async def mark_as_reviewed(doc_id: str):
    """تحديد مستند كمراجع."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]
    doc.status = "reviewed"
    doc.updated_at = datetime.now()
    documents_db[doc_id] = doc

    return {"status": "success"}

@app.post("/api/suggestions")
async def get_suggestions(text: str, language: str = "ar"):
    """الحصول على اقتراحات لتصحيح النص."""
    # في التطبيق الحقيقي، ستتم استعادة الاقتراحات من قاعدة البيانات أو نموذج ML
    suggestions = []
    if language == "ar":
        suggestions = [
            "تصحيح إملائي",
            "تصحيح نحوي",
            "تحسين الأسلوب",
        ]
    elif language == "en":
        suggestions = [
            "Fix spelling",
            "Fix grammar",
            "Improve style",
        ]

    return {"suggestions": suggestions}

@app.post("/api/documents/{doc_id}/export")
async def export_document(
    doc_id: str,
    format: str = "pdf",
    file_name: Optional[str] = None
):
    """تصدير مستند إلى صيغة معينة."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_db[doc_id]
    text = doc.processed_text or doc.raw_text

    # في التطبيق الحقيقي، ستتم استخدام TextExporter
    from modules.export.exporter import TextExporter
    from config import OmniFileConfig

    cfg = OmniFileConfig()
    exporter = TextExporter(cfg)

    output_path = f"exports/{doc_id}.{format}"
    os.makedirs("exports", exist_ok=True)

    exporter.export(
        text=text,
        output_path=output_path,
        format=format,
        language=doc.language
    )

    return {"file_url": output_path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
```

---

##### **2. تطوير Frontend (Flutter)**
**الهدف**: إنشاء واجهة مستخدم مرنة وسهلة الاستخدام.

**المتطلبات**:
- Flutter SDK
- Android Studio / Xcode
- حزمة `flutter_quill` للمحرر الغني

**الميزات الرئيسية**:
- **شاشة الرفع**: رفع ملفات من المعرض أو الكاميرا.
- **شاشة المراجعة**: عرض النص المستخرج مع إمكانية التعديل.
- **شاشة قائمة المستندات**: عرض جميع المستندات المراجعة.
- **شاشة الإعدادات**: تهيئة إعدادات التطبيق.

**مثال على الكود**:
```dart
// lib/screens/review_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'package:omnifile_mobile/models/document.dart';
import 'package:omnifile_mobile/services/api_service.dart';

class ReviewScreen extends StatefulWidget {
  final String documentId;

  const ReviewScreen({super.key, required this.documentId});

  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen> {
  final ApiService _apiService = ApiService();
  Document? _document;
  bool _isLoading = true;
  final QuillController _quillController = QuillController.basic();

  @override
  void initState() {
    super.initState();
    _loadDocument();
  }

  Future<void> _loadDocument() async {
    setState(() => _isLoading = true);
    try {
      _document = await _apiService.getDocument(widget.documentId);
      _quillController.document = Document.fromJson({
        'ops': [{'insert': _document!.rawText}],
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل تحميل المستند: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _saveCorrections() async {
    if (_document == null) return;

    try {
      final correctedText = _quillController.document.toPlainText();
      await _apiService.saveCorrections(
        docId: _document!.id,
        correctedText: correctedText,
      );
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم حفظ التعديلات بنجاح!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل حفظ التعديلات: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_document?.fileName ?? 'مراجعة المستند'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveCorrections,
            tooltip: 'حفظ التعديلات',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // معلومات المستند
                Card(
                  margin: const EdgeInsets.all(10),
                  child: Padding(
                    padding: const EdgeInsets.all(15),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildInfoItem('📄 الملف', _document?.fileName ?? '-'),
                        _buildInfoItem('📊 الثقة', '${(_document?.confidence ?? 0) * 100}%'),
                        _buildInfoItem('📝 الصفحات', _document?.pageCount.toString() ?? '-'),
                        _buildInfoItem('🌐 اللغة', _document?.language ?? '-'),
                      ],
                    ),
                  ),
                ),

                // محرر النص
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // شريط أدوات المحرر
                      QuillToolbar.basic(
                        controller: _quillController,
                        multiRowsDisplay: false,
                      ),

                      // منطقة الكتابة
                      Expanded(
                        child: Container(
                          margin: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            border: Border.all(color: Colors.grey.shade300),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.all(10),
                            child: QuillEditor(
                              controller: _quillController,
                              readOnly: false,
                              autoFocus: true,
                              expands: false,
                              padding: EdgeInsets.zero,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _saveCorrections,
        child: const Icon(Icons.check),
      ),
    );
  }

  Widget _buildInfoItem(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 14, color: Colors.grey),
        ),
        const SizedBox(height: 5),
        Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
```

---

##### **3. نشر التطبيق**
**الخطوات**:
1. **اختبار التطبيق**:
   ```bash
   flutter run
   ```
2. **بناء ملف APK**:
   ```bash
   flutter build apk
   ```
3. **نشر على Google Play Store**:
   - إنشاء حساب مطور على Google Play Console.
   - رفع ملف APK.
   - ملء معلومات التطبيق (الاسم، الوصف، الصور، إلخ).
   - نشر التطبيق.

4. **نشر على App Store (لiOS)**:
   - إنشاء حساب مطور على Apple Developer.
   - بناء ملف IPA:
     ```bash
     flutter build ios
     ```
   - فتح المشروع في Xcode ونشره.

---

#### **📊 الفوائد المتوقعة**
| **الفائدة** | **الوصف** | **التأثير** |
|--------------|-----------|--------------|
| **راحة الاستخدام** | مراجعة النصوص في أي مكان وزمان | ⭐⭐⭐⭐⭐ |
| **دقة أعلى** | مراجعة النصوص العربية بشكل أفضل | ⭐⭐⭐⭐⭐ |
| **سرعة العمل** | عدم الحاجة إلى الحاسوب في العمل الميداني | ⭐⭐⭐⭐⭐ |
| **دعم العمل الجماعي** | مزامنة البيانات بين عدة مستخدمين | ⭐⭐⭐⭐ |
| **دعم العمل بدون إنترنت** | حفظ البيانات محليًا | ⭐⭐⭐⭐ |
| **تجربة مستخدم أفضل** | واجهة مرنة وسهلة الاستخدام | ⭐⭐⭐⭐⭐ |

---

#### **🔮 التطويرات المستقبلية**
1. **دعم iOS**: نشر التطبيق على App Store.
2. **دعم العمل بدون إنترنت**: حفظ البيانات محليًا ومزامنتها لاحقًا.
3. **دعم Voice Input**: إدخال نص عبر الصوت.
4. **دعم Multi-User**: دعم عدة مستخدمين مع صلاحيات مختلفة.
5. **دعم Cloud Sync**: مزامنة البيانات مع Google Drive/Dropbox.
6. **دعم Batch Processing**: معالجة عدة ملفات في نفس الوقت.
7. **دعم Custom Models**: السماح للمستخدمين برفع نماذجهم الخاصة.

---

---

## 📝 **2. حفظ تنسيق النص**

### **🎯 الهدف العام**
حفظ **تنسيق النص** (جداول، صور، تسميات) **كما لو كان مكتوبًا على الحاسوب** عند تصدير النتائج، مع **دعم كامل للغة العربية** (RTL).

---

### **📌 المشكلات الحالية**
| **المشكلة** | **التأثير** | **الحل المقترح** |
|------------|--------------|------------------|
| **فقدان التنسيق** | النص يتم حفظه كنص عادي بدون تنسيق | استخدام HTML كصيغة وسيطة |
| **الجداول لا يتم حفظها** | فقدان هيكل الجداول | تحليل الجداول من Markdown |
| **الصور لا يتم حفظها** | فقدان الصور المضمنة | تحليل الصور من Markdown |
| **التسميات لا يتم حفظها** | فقدان تسميات الجداول والصور | حفظ التسميات في HTML |
| **دعم RTL ضعيف** | التنسيق لا يدعم العربية | استخدام direction: rtl |

---

### **🔧 الحل المقترح: استخدام HTML + CSS**

#### **✅ لماذا HTML؟**
1. **دعم كامل للتنسيق**: bold, italic, tables, images, etc.
2. **دعم RTL**: دعم كامل **للغة العربية**.
3. **سهل التحويل**: يمكن تحويل HTML إلى **PDF/DOCX/Excel**.
4. **متوافق مع جميع المنصات**: يمكن فتحه في أي متصفح.

---

#### **📋 الميزات المطلوبة**
| **الميزة** | **الوصف** | **الأولوية** | **الحالة** | **التفاصيل** |
|------------|-----------|--------------|------------|--------------|
| **دعم الجداول** | حفظ الجداول من Markdown إلى HTML/PDF/DOCX | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | تحليل الجداول من نص Markdown |
| **دعم الصور** | حفظ الصور المضمنة في النص | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | تحليل الصور من Markdown |
| **دعم التسميات** | حفظ تسميات الجداول والصور | ⭐⭐⭐⭐ | ✅ **مبرمج** | حفظ التسميات في HTML |
| **دعم RTL** | دعم التنسيق من اليمين إلى اليسار | ⭐⭐⭐⭐⭐ | ✅ **مبرمج** | استخدام direction: rtl |
| **دعم الكود** | حفظ كتل الكود بتنسيق صحيح | ⭐⭐⭐⭐ | ✅ **مبرمج** | استخدام `<pre><code>` |
| **دعم العناوين** | حفظ العناوين (h1, h2, etc.) | ⭐⭐⭐⭐ | ✅ **مبرمج** | تحويل # Heading إلى `<h1>` |
| **دعم الخط المائل/الغليظ** | حفظ التنسيق النصي | ⭐⭐⭐ | ✅ **مبرمج** | تحويل **text** إلى `<strong>` |
| **دعم الأسطر الجديدة** | حفظ الأسطر الجديدة | ⭐⭐⭐ | ✅ **مبرمج** | تحويل `\n` إلى `<br>` |
| **دعم الروابط** | حفظ الروابط | ⭐⭐⭐ | ✅ **مبرمج** | تحويل [text](url) إلى `<a>` |
| **دعم الأسطر الفاصلة** | حفظ الأسطر الفاصلة | ⭐⭐ | ✅ **مبرمج** | تحويل `---` إلى `<hr>` |

---

#### **🏗️ هيكل نظام التصدير**
```
modules/export/
├── exporter.py          # المصدّر الرئيسي
├── html_exporter.py     # تصدير إلى HTML
├── pdf_exporter.py      # تصدير إلى PDF
├── docx_exporter.py     # تصدير إلى DOCX
├── excel_exporter.py    # تصدير إلى Excel
└── format_parser.py     # تحليل التنسيق
```

---

#### **📦 المتطلبات**
- `beautifulsoup4` (لتحليل HTML)
- `pdfkit` (لتحويل HTML إلى PDF)
- `python-docx` (لتحويل HTML إلى DOCX)
- `openpyxl` (لتحويل الجداول إلى Excel)
- `Pillow` (لمعالجة الصور)

**التثبيت**:
```bash
pip install beautifulsoup4 pdfkit python-docx openpyxl Pillow
```

---

#### **🔧 خطوات التنفيذ**

##### **1. تحليل النص المدخل**
**الهدف**: تحليل النص لاكتشاف:
- **الجداول** (Markdown-style)
- **الصور** (Markdown-style: `![alt](url)`)
- **كتل الكود** (Markdown-style: ```code```)
- **العناوين** (Markdown-style: `# Heading`)
- **الخط المائل/الغليظ** (`*text*`, **text**)

**مثال على الكود**:
```python
# modules/export/format_parser.py
import re
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup

class FormatParser:
    """محلل للتنسيق في النصوص."""

    @staticmethod
    def parse_tables(text: str) -> List[List[List[str]]]:
        """
        تحليل الجداول من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[List[List[str]]]: قائمة الجداول (كل جدول هو قائمة صفوف، كل صف هو قائمة خلايا).
        """
        tables = []
        lines = text.split('\n')
        current_table = []
        in_table = False

        for line in lines:
            if line.strip().startswith('|') and line.strip().endswith('|'):
                if not in_table:
                    current_table = []
                    in_table = True

                # تحليل السطر
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                current_table.append(cells)
            else:
                if in_table and current_table:
                    # تأكد من أن الجدول يحتوي على أكثر من سطر (رأس + بيانات)
                    if len(current_table) > 1:
                        tables.append(current_table)
                    current_table = []
                    in_table = False

        # إضافة الجدول الأخير إذا كان هناك جدول غير مكتمل
        if in_table and current_table and len(current_table) > 1:
            tables.append(current_table)

        return tables

    @staticmethod
    def parse_images(text: str) -> List[Dict[str, str]]:
        """
        تحليل الصور من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Dict[str, str]]: قائمة الصور (كل صورة تحتوي على alt و url).
        """
        images = []
        image_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

        for match in image_pattern.finditer(text):
            images.append({
                'alt': match.group(1),
                'url': match.group(2)
            })

        return images

    @staticmethod
    def parse_code_blocks(text: str) -> List[Dict[str, str]]:
        """
        تحليل كتل الكود من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Dict[str, str]]: قائمة كتل الكود (كل كتلة تحتوي على language و code).
        """
        code_blocks = []
        code_pattern = re.compile(r'```(\w*)\n([\s\S+?])```')

        for match in code_pattern.finditer(text):
            code_blocks.append({
                'language': match.group(1),
                'code': match.group(2).strip()
            })

        return code_blocks

    @staticmethod
    def parse_headings(text: str) -> List[Tuple[str, str]]:
        """
        تحليل العناوين من نص Markdown.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str]]: قائمة العناوين (كل عنوان هو (level, text)).
        """
        headings = []
        for i in range(1, 7):
            pattern = re.compile(rf'^{"#" * i}\s+(.*?)$', re.MULTILINE)
            for match in pattern.finditer(text):
                headings.append((f'h{i}', match.group(1).strip()))

        return headings

    @staticmethod
    def parse_emphasis(text: str) -> List[Tuple[str, str, str]]:
        """
        تحليل الخط المائل والغليظ من النص.

        Args:
            text: النص المدخل.

        Returns:
            List[Tuple[str, str, str]]: قائمة التنسيقات (type, start, end).
        """
        emphasis = []

        # غليظ: **text**
        for match in re.finditer(r'\*\*(.*?)\*\*', text):
            emphasis.append(('strong', match.start(), match.end()))

        # مائل: *text*
        for match in re.finditer(r'\*(.*?)\*', text):
            emphasis.append(('em', match.start(), match.end()))

        # مسطّر: ~~text~~
        for match in re.finditer(r'~~(.*?)~~', text):
            emphasis.append(('s', match.start(), match.end()))

        return emphasis
```

---

##### **2. تحويل التنسيق إلى HTML**
**الهدف**: تحويل النص المدخل إلى HTML مع حفظ التنسيق.

**مثال على الكود**:
```python
# modules/export/html_exporter.py
from typing import Optional, Dict, List
from pathlib import Path
from .format_parser import FormatParser
import base64

class HTMLExporter:
    """مصدّر للنصوص إلى HTML مع حفظ التنسيق."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.is_rtl = language == "ar"

    def export(
        self,
        text: str,
        output_path: Path,
        title: str = "OmniFile Export",
        metadata: Optional[Dict] = None,
        include_styles: bool = True,
        include_fonts: bool = True
    ) -> Path:
        """
        تصدير النص إلى HTML.

        Args:
            text: النص المدخل.
            output_path: مسار ملف HTML المخرج.
            title: عنوان الصفحة.
            metadata: بيانات وصفية (اختياري).
            include_styles: تضمين أنماط CSS (افتراضي: True).
            include_fonts: تضمين خطوط Google Fonts (افتراضي: True).

        Returns:
            Path: مسار ملف HTML.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # تحليل النص
        tables = FormatParser.parse_tables(text)
        images = FormatParser.parse_images(text)
        code_blocks = FormatParser.parse_code_blocks(text)
        headings = FormatParser.parse_headings(text)
        emphasis_list = FormatParser.parse_emphasis(text)

        # إنشاء HTML
        html = self._generate_html(
            text=text,
            title=title,
            tables=tables,
            images=images,
            code_blocks=code_blocks,
            headings=headings,
            emphasis_list=emphasis_list,
            metadata=metadata,
            include_styles=include_styles,
            include_fonts=include_fonts
        )

        # كتابة الملف
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return output_path

    def _generate_html(
        self,
        text: str,
        title: str,
        tables: List[List[List[str]]],
        images: List[Dict[str, str]],
        code_blocks: List[Dict[str, str]],
        headings: List[Tuple[str, str]],
        emphasis_list: List[Tuple[str, str, str]],
        metadata: Optional[Dict],
        include_styles: bool,
        include_fonts: bool
    ) -> str:
        """توليد HTML من المكونات."""
        # بداية HTML
        html = f'<!DOCTYPE html>\n<html lang="{self.language}" dir="{self._get_dir()}">\n<head>\n'

        # العنوان
        html += f'    <meta charset="UTF-8">\n'
        html += f'    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        html += f'    <title>{title}</title>\n'

        # أنماط CSS
        if include_styles:
            html += self._generate_styles()

        # خطوط Google Fonts
        if include_fonts and self.language == "ar":
            html += '    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Amiri&display=swap">\n'

        html += '</head>\n<body>\n'

        # العنوان الرئيسي
        html += f'    <h1>{title}</h1>\n'

        # المعالجة الفورية للنص (للتنسيقات البسيطة)
        processed_text = text

        # استبدال الجداول
        for table in tables:
            table_html = self._generate_table_html(table)
            # استبدال الجدول في النص
            table_text = self._table_to_text(table)
            processed_text = processed_text.replace(table_text, f'<!-- TABLE:{len(tables)} -->')

        # استبدال الصور
        for i, image in enumerate(images):
            image_html = self._generate_image_html(image)
            image_text = f'![{image["alt"]}]({image["url"]})'
            processed_text = processed_text.replace(image_text, f'<!-- IMAGE:{i} -->')

        # استبدال كتل الكود
        for i, code_block in enumerate(code_blocks):
            code_html = self._generate_code_html(code_block)
            code_text = f'```{code_block["language"]}\n{code_block["code"]}\n```'
            processed_text = processed_text.replace(code_text, f'<!-- CODE:{i} -->')

        # استبدال العناوين
        for tag, heading_text in headings:
            processed_text = processed_text.replace(f'#{tag[1:]} {heading_text}', f'<{tag}>{heading_text}</{tag}>')

        # استبدال التنسيقات (غليظ، مائل، مسطّر)
        # يتم معالجتها في CSS

        # إضافة المحتوى
        html += f'    <div class="content">\n{processed_text}\n    </div>\n'

        # إضافة الجداول
        for i, table in enumerate(tables):
            html += self._generate_table_html(table)

        # إضافة الصور
        for i, image in enumerate(images):
            html += self._generate_image_html(image)

        # إضافة كتل الكود
        for i, code_block in enumerate(code_blocks):
            html += self._generate_code_html(code_block)

        # إضافة البيانات الوصفية
        if metadata:
            html += self._generate_metadata_html(metadata)

        html += '</body>\n</html>'

        return html

    def _get_dir(self) -> str:
        """الحصول على اتجاه النص."""
        return 'rtl' if self.is_rtl else 'ltr'

    def _generate_styles(self) -> str:
        """توليد أنماط CSS."""
        return f'''    <style>
        body {{
            font-family: {'"Amiri", serif' if self.language == 'ar' else '"Times New Roman", serif'};
            font-size: 14pt;
            line-height: 1.6;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
            color: #333;
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: #1E88E5;
            margin-top: 20px;
            margin-bottom: 10px;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        .content {{
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            direction: {self._get_dir()};
        }}

        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: {self._get_dir()};
        }}

        th {{
            background-color: #f2f2f2;
        }}

        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 20px auto;
        }}

        .figure {{
            text-align: center;
            margin: 20px 0;
        }}

        .figure-caption {{
            font-style: italic;
            font-size: 12pt;
            margin-top: 5px;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}

        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            direction: ltr;
            text-align: left;
        }}

        code {{
            font-family: "Courier New", monospace;
        }}

        strong {{
            font-weight: bold;
        }}

        em {{
            font-style: italic;
        }}

        s {{
            text-decoration: line-through;
        }}

        hr {{
            border: 0;
            height: 1px;
            background: #ddd;
            margin: 20px 0;
        }}

        blockquote {{
            border-{self._get_dir()}: 4px solid #1E88E5;
            padding: 10px 20px;
            margin: 20px 0;
            background-color: #f9f9f9;
            direction: {self._get_dir()};
            text-align: {self._get_dir()};
        }}
    </style>'''

    def _generate_table_html(self, table: List[List[str]]) -> str:
        """توليد HTML للجدول."""
        html = '    <table>\n'

        # رأس الجدول
        if table.isNotEmpty:
            html += '      <thead>\n        <tr>\n'
            for cell in table[0]:
                html += f'          <th>{cell}</th>\n'
            html += '        </tr>\n      </thead>\n'

        # جسم الجدول
        html += '      <tbody>\n'
        for i, row in enumerate(table):
            if i == 0:
                continue  # تجاهل رأس الجدول (تم معالجته أعلاه)
            html += '        <tr>\n'
            for cell in row:
                html += f'          <td>{cell}</td>\n'
            html += '        </tr>\n'
        html += '      </tbody>\n    </table>\n'

        return html

    def _table_to_text(self, table: List[List[str]]) -> str:
        """تحويل الجدول إلى نص للبحث عنه في النص الأصلي."""
        lines = []
        for row in table:
            lines.append('| ' + ' | '.join(row) + ' |')
        return '\n'.join(lines)

    def _generate_image_html(self, image: Dict[str, str]) -> str:
        """توليد HTML للصورة."""
        alt = image.get('alt', '')
        url = image.get('url', '')

        if url.startswith('data:image/'):
            # صورة base64
            return f'    <div class="figure">\n      <img src="{url}" alt="{alt}">\n      <div class="figure-caption">{alt}</div>\n    </div>\n'
        else:
            # صورة من URL
            return f'    <div class="figure">\n      <img src="{url}" alt="{alt}">\n      <div class="figure-caption">{alt}</div>\n    </div>\n'

    def _generate_code_html(self, code_block: Dict[str, str]) -> str:
        """توليد HTML لكتل الكود."""
        language = code_block.get('language', '')
        code = code_block.get('code', '')

        return f'    <pre><code class="language-{language}">{code}</code></pre>\n'

    def _generate_metadata_html(self, metadata: Dict) -> str:
        """توليد HTML للبيانات الوصفية."""
        html = '\n    <div class="metadata">\n'
        html += '      <h2>معلومات التصدير</h2>\n'
        html += '      <table>\n'

        for key, value in metadata.items():
            html += f'        <tr><th>{key}</th><td>{value}</td></tr>\n'

        html += '      </table>\n'
        html += '    </div>\n'

        return html
```

---

##### **3. تصدير HTML إلى صيغ أخرى**

###### **3.1 تصدير إلى PDF**
**المتطلبات**:
- `pdfkit` (لتحويل HTML إلى PDF)
- `wkhtmltopdf` (مطلوب لتشغيل pdfkit)

**التثبيت**:
```bash
# على Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# تثبيت pdfkit
pip install pdfkit
```

**مثال على الكود**:
```python
# modules/export/pdf_exporter.py
from pathlib import Path
from typing import Optional, Dict
import pdfkit
import os

class PDFExporter:
    """مصدّر للنصوص إلى PDF."""

    def __init__(self, wkhtmltopdf_path: Optional[str] = None):
        self.wkhtmltopdf_path = wkhtmltopdf_path or '/usr/bin/wkhtmltopdf'

    def export(
        self,
        html_path: Path,
        output_path: Path,
        **options
    ) -> Path:
        """
        تصدير HTML إلى PDF.

        Args:
            html_path: مسار ملف HTML.
            output_path: مسار ملف PDF المخرج.
            options: خيارات إضافية (مثل حجم الورقة).

        Returns:
            Path: مسار ملف PDF.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # إعداد خيارات pdfkit
        default_options = {
            'encoding': 'UTF-8',
            'quiet': '',
            'enable-local-file-access': None,  # السماح بالوصول إلى الملفات المحلية
        }
        options = {**default_options, **options}

        # إعداد التكوين
        config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)

        # تحويل HTML إلى PDF
        pdfkit.from_file(str(html_path), str(output_path), configuration=config, options=options)

        return output_path
```

---

###### **3.2 تصدير إلى DOCX**
**المتطلبات**:
- `python-docx` (لإنشاء ملفات DOCX)

**التثبيت**:
```bash
pip install python-docx
```

**مثال على الكود**:
```python
# modules/export/docx_exporter.py
from pathlib import Path
from typing import Optional, List
from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from bs4 import BeautifulSoup
import re

class DOCXExporter:
    """مصدّر للنصوص إلى DOCX."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.is_rtl = language == "ar"

    def export(
        self,
        html_path: Path,
        output_path: Path
    ) -> Path:
        """
        تصدير HTML إلى DOCX.

        Args:
            html_path: مسار ملف HTML.
            output_path: مسار ملف DOCX المخرج.

        Returns:
            Path: مسار ملف DOCX.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # قراءة HTML
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # تحليل HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # إنشاء مستند DOCX
        doc = DocxDocument()

        # معالجة الجسم
        body = soup.find("body")
        if body:
            for element in body.children:
                self._process_html_element(element, doc)

        # حفظ الملف
        doc.save(str(output_path))
        return output_path

    def _process_html_element(self, element, doc):
        """معالجة عنصر HTML وإضافته إلى DOCX."""
        if element.name == "h1":
            doc.add_heading(element.text, level=1)
        elif element.name == "h2":
            doc.add_heading(element.text, level=2)
        elif element.name == "h3":
            doc.add_heading(element.text, level=3)
        elif element.name == "h4":
            doc.add_heading(element.text, level=4)
        elif element.name == "h5":
            doc.add_heading(element.text, level=5)
        elif element.name == "h6":
            doc.add_heading(element.text, level=6)
        elif element.name == "p":
            paragraph = doc.add_paragraph(element.text)
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "table":
            self._process_table(element, doc)
        elif element.name == "img":
            # إضافة صورة (سيتم إضافة دعم لها لاحقًا)
            pass
        elif element.name == "pre":
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(element.text)
            run.font.name = "Courier New"
            run.font.size = Pt(10)
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "strong" or element.name == "b":
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(element.text)
            run.bold = True
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "em" or element.name == "i":
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(element.text)
            run.italic = True
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "s" or element.name == "del":
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(element.text)
            run.font.strike = True
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "br":
            doc.add_paragraph()  # إضافة سطر فارغ
        elif element.name == "hr":
            doc.add_paragraph("---")
        elif element.name == "blockquote":
            paragraph = doc.add_paragraph(element.text)
            paragraph.style = "Block Text"
            if self.is_rtl:
                paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name is None:  # نص عادي
            if element.string and element.string.strip():
                paragraph = doc.add_paragraph(element.string.strip())
                if self.is_rtl:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
        elif element.name == "div" and "metadata" in element.get("class", []):
            # تجاهل قسم البيانات الوصفية
            pass
        else:
            # معالج العناصر غير المعروفة
            if element.string and element.string.strip():
                paragraph = doc.add_paragraph(element.string.strip())
                if self.is_rtl:
                    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

    def _process_table(self, table_element, doc):
        """معالجة جدول HTML وإضافته إلى DOCX."""
        table = doc.add_table(rows=1, cols=len(table_element.find_all("th", recursive=False)))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        # إضافة رأس الجدول
        headers = table_element.find_all("th")
        for i, header in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = header.text
            if self.is_rtl:
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

        # إضافة الصفوف
        rows = table_element.find_all("tr")[1:]  # تجاهل رأس الجدول
        for row in rows:
            table_row = table.add_row()
            cells = row.find_all("td")
            for i, cell in enumerate(cells):
                if i < len(table_row.cells):
                    table_row.cells[i].text = cell.text
                    if self.is_rtl:
                        table_row.cells[i].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
```

---

###### **3.3 تصدير إلى Excel**
**المتطلبات**:
- `openpyxl` (لإنشاء ملفات Excel)

**التثبيت**:
```bash
pip install openpyxl
```

**مثال على الكود**:
```python
# modules/export/excel_exporter.py
from pathlib import Path
from typing import Optional, List
import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from bs4 import BeautifulSoup

class ExcelExporter:
    """مصدّر للنصوص إلى Excel (للجداول)."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.is_rtl = language == "ar"

    def export(
        self,
        html_path: Path,
        output_path: Path
    ) -> Path:
        """
        تصدير HTML إلى Excel.

        Args:
            html_path: مسار ملف HTML.
            output_path: مسار ملف Excel المخرج.

        Returns:
            Path: مسار ملف Excel.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # قراءة HTML
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # تحليل HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # إنشاء ملف Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "النص"

        # معالجة الجداول
        tables = soup.find_all("table")
        if not tables:
            # إذا لم يتم العثور على جداول، إضافة النص كخلية واحدة
            body = soup.find("body")
            if body:
                ws.append([body.get_text()])
        else:
            for i, table in enumerate(tables):
                if i > 0:
                    ws = wb.create_sheet(title=f"جدول {i+1}")

                # إضافة رأس الجدول
                headers = [th.text for th in table.find_all("th")]
                if headers:
                    ws.append(headers)

                # إضافة البيانات
                for row in table.find_all("tr")[1:]:  # تجاهل رأس الجدول
                    cells = [td.text for td in row.find_all("td")]
                    if cells:
                        ws.append(cells)

                # تنسيق الجدول
                for row in ws.iter_rows():
                    for cell in row:
                        cell.alignment = Alignment(
                            horizontal='right' if self.is_rtl else 'left',
                            vertical='top',
                            wrap_text=True
                        )

        # حفظ الملف
        wb.save(str(output_path))
        return output_path
```

---

##### **4. دمج جميع المصدّرات في ملف واحد**
**مثال على الكود**:
```python
# modules/export/exporter.py
from pathlib import Path
from typing import Optional, Dict, Union
from .html_exporter import HTMLExporter
from .pdf_exporter import PDFExporter
from .docx_exporter import DOCXExporter
from .excel_exporter import ExcelExporter
import logging

logger = logging.getLogger(__name__)

class TextExporter:
    """مصدّر للنصوص إلى صيغ مختلفة."""

    def __init__(self, language: str = "ar"):
        self.language = language
        self.html_exporter = HTMLExporter(language)
        self.pdf_exporter = PDFExporter()
        self.docx_exporter = DOCXExporter(language)
        self.excel_exporter = ExcelExporter(language)

    def export(
        self,
        text: str,
        output_path: Union[str, Path],
        format: str = "html",
        title: str = "OmniFile Export",
        metadata: Optional[Dict] = None,
        **options
    ) -> Path:
        """
        تصدير النص إلى الصيغة المحددة.

        Args:
            text: النص المراد تصديره.
            output_path: مسار الملف المخرج.
            format: الصيغة (html, pdf, docx, excel).
            title: عنوان الصفحة (لHTML/PDF).
            metadata: بيانات وصفية (اختياري).
            options: خيارات إضافية.

        Returns:
            Path: مسار الملف المصدّر.
        """
        output_path = Path(output_path)

        if format == "html":
            return self.html_exporter.export(
                text=text,
                output_path=output_path,
                title=title,
                metadata=metadata
            )
        elif format == "pdf":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.pdf_exporter.export(
                html_path=html_path,
                output_path=output_path,
                **options
            )
        elif format == "docx":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.docx_exporter.export(
                html_path=html_path,
                output_path=output_path
            )
        elif format == "excel":
            html_path = output_path.parent / f"{output_path.stem}.html"
            self.html_exporter.export(
                text=text,
                output_path=html_path,
                title=title,
                metadata=metadata
            )
            return self.excel_exporter.export(
                html_path=html_path,
                output_path=output_path
            )
        else:
            raise ValueError(f"الصيغة {format} غير مدعومة. الصيغ المدعومة: html, pdf, docx, excel")
```

---

#### **📊 الفوائد المتوقعة**
| **الفائدة** | **الوصف** | **التأثير** |
|--------------|-----------|--------------|
| **جودة أعلى** | حفظ التنسيق كما هو في المستند الأصلي | ⭐⭐⭐⭐⭐ |
| **دعم كامل** | دعم جميع أنواع التنسيق (جداول، صور، كود) | ⭐⭐⭐⭐⭐ |
| **مرونة** | تصدير إلى عدة صيغ (HTML, PDF, DOCX, Excel) | ⭐⭐⭐⭐⭐ |
| **دعم RTL** | دعم كامل للغة العربية | ⭐⭐⭐⭐⭐ |
| **توافق** | العمل على جميع المنصات | ⭐⭐⭐⭐⭐ |

---

#### **🔮 التطويرات المستقبلية**
1. **دعم صور Base64**: حفظ الصور المضمنة في النص كـ Base64.
2. **دعم أكثر من جدول**: تحسين تحليل الجداول المعقدة.
3. **دعم أنماط CSS مخصصة**: السماح للمستخدمين بتحديد أنماطهم الخاصة.
4. **دعم Templates**: استخدام قوالب HTML جاهزة.
5. **دعم Export to EPUB**: تصدير إلى صيغة الكتب الإلكترونية.

---

---

## 🎯 **3. تحسين دقة نماذج OCR العربية**

### **🎯 الهدف العام**
تحسين **دقة نماذج OCR العربية** من خلال:
1. **حفظ تنسيق النص** (جداول، صور، تسميات).
2. **التعلم من تصحيحات المستخدم** (Active Learning).
3. **ضبط نماذج TrOCR** على بيانات عربية (Fine-tuning).

---

### **📌 المشكلات الحالية**
| **المشكلة** | **التأثير** | **الحل المقترح** |
|------------|--------------|------------------|
| **دقة منخفضة** | العديد من الأخطاء في النصوص العربية | التعلم من تصحيحات المستخدم |
| **لا يوجد دعم للجداول** | فقدان هيكل الجداول | حفظ الجداول في التنسيق |
| **لا يوجد دعم للصور** | فقدان الصور المضمنة | حفظ الصور في التنسيق |
| **نماذج غير مخصصة** | نماذج عامة غير مخصصة للعربية | Fine-tuning على بيانات عربية |
| **لا يوجد تعلم مستمر** | عدم تحسين الدقة مع الوقت | Active Learning |

---

### **🔧 الحل المقترح**

#### **1. حفظ تنسيق النص (موجود في قسم 2)**
- **حفظ الجداول** من Markdown إلى HTML/PDF/DOCX.
- **حفظ الصور** من Markdown إلى HTML/PDF/DOCX.
- **حفظ التسميات** (Figures, Tables) في HTML.

---

#### **2. التعلم من المستخدم (Active Learning)**
**الهدف**: تحسين دقة نماذج OCR من خلال **تعلمها من تصحيحات المستخدم**.

**المتطلبات**:
- `sqlite3` (لقاعدة البيانات)
- `transformers` (لنماذج OCR)
- `torch` (لدعم GPU)

**الميزات**:
- **حفظ تصحيحات المستخدم** في قاعدة بيانات.
- **إعادة تدريب النماذج** على البيانات المصححة.
- **استخدام LoRA** (Low-Rank Adaptation) لضبط النماذج بشكل فعال.

**مثال على الكود**:
```python
# modules/ai/active_learning.py
from typing import Dict, List, Optional, Union
from pathlib import Path
import sqlite3
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ActiveLearningDB:
    """قاعدة بيانات للتعلم من تصحيحات المستخدم."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """تهيئة قاعدة البيانات."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # جدول التصحيحات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_text TEXT NOT NULL,
                    corrected_text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    confidence REAL,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_used_in_training BOOLEAN DEFAULT FALSE,
                    correction_count INTEGER DEFAULT 1
                )
            """)

            # جدول بيانات التدريب
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS training_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT,
                    original_text TEXT,
                    corrected_text TEXT,
                    language TEXT NOT NULL,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_used_in_training BOOLEAN DEFAULT FALSE
                )
            """)

            # جدول نماذج OCR المدربة
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fine_tuned_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    language TEXT NOT NULL,
                    base_model TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accuracy REAL,
                    version TEXT
                )
            """)

            conn.commit()

    def save_correction(
        self,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float,
        source: str = "manual"
    ) -> int:
        """
        حفظ تصحيح جديد.

        Args:
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.
            source: مصدر التصحيح (manual, auto, etc.).

        Returns:
            int: ID التصحيح.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # التحقق من وجود تصحيح مشابه
            cursor.execute("""
                SELECT id, correction_count FROM corrections
                WHERE original_text = ? AND corrected_text = ? AND language = ?
            """, (original_text, corrected_text, language))

            result = cursor.fetchone()

            if result:
                # تحديث التصحيح الموجود
                correction_id, count = result
                cursor.execute("""
                    UPDATE corrections
                    SET correction_count = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (count + 1, correction_id))
            else:
                # إضافة تصحيح جديد
                cursor.execute("""
                    INSERT INTO corrections
                    (original_text, corrected_text, language, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                """, (original_text, corrected_text, language, confidence, source))
                correction_id = cursor.lastrowid

            conn.commit()
            return correction_id

    def get_corrections(
        self,
        language: str,
        limit: int = 100,
        min_confidence: float = 0.0,
        min_correction_count: int = 1
    ) -> List[Dict]:
        """
        استعادة تصحيحات للمستخدم.

        Args:
            language: لغة التصحيحات.
            limit: الحد الأقصى لعدد التصحيحات.
            min_confidence: الحد الأدنى للثقة.
            min_correction_count: الحد الأدنى لعدد مرات التصحيح.

        Returns:
            List[Dict]: قائمة التصحيحات.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM corrections
                WHERE language = ? AND confidence >= ? AND correction_count >= ?
                ORDER BY correction_count DESC, created_at DESC
                LIMIT ?
            """, (language, min_confidence, min_correction_count, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def save_training_data(
        self,
        image_path: str,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float
    ) -> int:
        """
        حفظ بيانات تدريب جديدة.

        Args:
            image_path: مسار الصورة.
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.

        Returns:
            int: ID بيانات التدريب.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO training_data
                (image_path, original_text, corrected_text, language, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (image_path, original_text, corrected_text, language, confidence))
            conn.commit()
            return cursor.lastrowid

    def get_training_data(
        self,
        language: str,
        limit: int = 1000,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        استعادة بيانات التدريب.

        Args:
            language: لغة البيانات.
            limit: الحد الأقصى لعدد البيانات.
            min_confidence: الحد الأدنى للثقة.

        Returns:
            List[Dict]: قائمة بيانات التدريب.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM training_data
                WHERE language = ? AND confidence >= ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (language, min_confidence, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def mark_as_used_in_training(self, correction_id: int) -> bool:
        """
        تحديد تصحيح كمستخدم في التدريب.

        Args:
            correction_id: ID التصحيح.

        Returns:
            bool: True إذا تم التحديث، False إذا لم يتم العثور على التصحيح.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE corrections
                SET is_used_in_training = TRUE
                WHERE id = ?
            """, (correction_id,))
            conn.commit()
            return cursor.rowcount > 0

    def mark_training_data_as_used(self, data_id: int) -> bool:
        """
        تحديد بيانات تدريب كمستخدمة.

        Args:
            data_id: ID بيانات التدريب.

        Returns:
            bool: True إذا تم التحديث، False إذا لم يتم العثور على البيانات.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE training_data
                SET is_used_in_training = TRUE
                WHERE id = ?
            """, (data_id,))
            conn.commit()
            return cursor.rowcount > 0

    def save_fine_tuned_model(
        self,
        model_name: str,
        model_path: str,
        language: str,
        base_model: str,
        accuracy: float,
        version: str = "1.0"
    ) -> int:
        """
        حفظ نموذج مدرب.

        Args:
            model_name: اسم النموذج.
            model_path: مسار النموذج.
            language: لغة النموذج.
            base_model: النموذج الأساسي.
            accuracy: دقة النموذج.
            version: الإصدار.

        Returns:
            int: ID النموذج.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fine_tuned_models
                (model_name, model_path, language, base_model, accuracy, version)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (model_name, model_path, language, base_model, accuracy, version))
            conn.commit()
            return cursor.lastrowid

    def get_fine_tuned_models(
        self,
        language: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        استعادة نماذج مدربة.

        Args:
            language: لغة النماذج.
            limit: الحد الأقصى لعدد النماذج.

        Returns:
            List[Dict]: قائمة النماذج.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fine_tuned_models
                WHERE language = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (language, limit))

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

class ActiveLearner:
    """نظام تعلم نشط من تصحيحات المستخدم."""

    def __init__(
        self,
        db_path: Union[str, Path],
        correction_threshold: int = 2,
        training_batch_size: int = 100
    ):
        """
        تهيئة النظام.

        Args:
            db_path: مسار قاعدة البيانات.
            correction_threshold: عدد التصحيحات المطلوب قبل التدريب.
            training_batch_size: حجم الدفعة للتدريب.
        """
        self.db = ActiveLearningDB(db_path)
        self.correction_threshold = correction_threshold
        self.training_batch_size = training_batch_size

    def log_correction(
        self,
        original_text: str,
        corrected_text: str,
        language: str,
        confidence: float,
        source: str = "manual",
        image_path: Optional[str] = None
    ) -> int:
        """
        سجل تصحيحًا جديدًا.

        Args:
            original_text: النص الأصلي.
            corrected_text: النص المصحح.
            language: لغة النص.
            confidence: ثقة النتيجة.
            source: مصدر التصحيح.
            image_path: مسار الصورة (اختياري).

        Returns:
            int: ID التصحيح.
        """
        correction_id = self.db.save_correction(
            original_text, corrected_text, language, confidence, source
        )

        # إذا كان هناك صورة، حفظها في بيانات التدريب
        if image_path:
            self.db.save_training_data(
                image_path, original_text, corrected_text, language, confidence
            )

        # التحقق من عدد التصحيحات لنفس النص
        corrections = self.db.get_corrections(
            language=language,
            limit=100,
            min_confidence=confidence
        )

        # إذا كان هناك عدد كافٍ من التصحيحات، قم بتدريب النموذج
        if len(corrections) >= self.correction_threshold:
            self._retrain_model(language)

        return correction_id

    def _retrain_model(self, language: str):
        """إعادة تدريب النموذج على البيانات المصححة."""
        logger.info(f"جاري إعادة تدريب النموذج للغة {language}...")

        # استعادة بيانات التدريب
        training_data = self.db.get_training_data(
            language=language,
            limit=self.training_batch_size,
            min_confidence=0.7
        )

        if not training_data:
            logger.warning(f"لا توجد بيانات تدريب للغة {language}")
            return

        # هنا يتم تدريب النموذج (مثال: TrOCR)
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            from datasets import Dataset
            import torch
            from PIL import Image

            # تحميل النموذج
            model_name = "microsoft/trocr-base-handwritten"
            processor = TrOCRProcessor.from_pretrained(model_name)
            model = VisionEncoderDecoderModel.from_pretrained(model_name)

            # إعداد البيانات
            images = []
            labels = []

            for data in training_data:
                try:
                    img = Image.open(data["image_path"])
                    images.append(img)
                    labels.append(data["corrected_text"])

                    # تحديد البيانات كمستخدمة في التدريب
                    self.db.mark_training_data_as_used(data["id"])
                except Exception as e:
                    logger.error(f"فشل تحميل الصورة {data['image_path']}: {e}")

            if not images:
                logger.warning("لا توجد صور صالحة للتدريب")
                return

            # إنشاء Dataset
            dataset = Dataset.from_dict({
                "pixel_values": processor(images, return_tensors="pt").pixel_values,
                "labels": processor(labels, return_tensors="pt").input_ids,
            })

            # تدريب النموذج (مثال مبسط)
            from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

            training_args = Seq2SeqTrainingArguments(
                output_dir=f"./fine_tuned_trocr_{language}",
                per_device_train_batch_size=4,
                num_train_epochs=3,
                save_steps=10_000,
                save_total_limit=2,
                logging_dir='./logs',
                logging_steps=10,
                learning_rate=5e-5,
                warmup_steps=500,
                weight_decay=0.01,
                fp16=torch.cuda.is_available(),
            )

            trainer = Seq2SeqTrainer(
                model=model,
                args=training_args,
                train_dataset=dataset,
            )

            trainer.train()

            # حفظ النموذج المدرب
            model_path = f"./fine_tuned_models/trocr_{language}_v1"
            model.save_pretrained(model_path)
            processor.save_pretrained(model_path)

            # حفظ النموذج في قاعدة البيانات
            self.db.save_fine_tuned_model(
                model_name=f"trocr_{language}_v1",
                model_path=model_path,
                language=language,
                base_model=model_name,
                accuracy=0.95  # دقة افتراضية
            )

            logger.info(f"تم تدريب النموذج للغة {language} وحفظه في {model_path}")

            # تحديد التصحيحات كمستخدمة في التدريب
            for data in training_data:
                self.db.mark_as_used_in_training(data["id"])

        except Exception as e:
            logger.error(f"فشل تدريب النموذج: {e}")

    def get_suggestions(self, text: str, language: str, limit: int = 5) -> List[str]:
        """
        الحصول على اقتراحات لتصحيح النص.

        Args:
            text: النص المراد تصحيحه.
            language: لغة النص.
            limit: الحد الأقصى لعدد الاقتراحات.

        Returns:
            List[str]: قائمة الاقتراحات.
        """
        corrections = self.db.get_corrections(
            language=language,
            limit=limit * 2,  # الحصول على ضعف العدد المطلوب
            min_confidence=0.7,
            min_correction_count=2  # يجب أن يكون التصحيح قد تم أكثر من مرة
        )

        suggestions = []
        for correction in corrections:
            if correction["original_text"] in text and correction["corrected_text"] not in suggestions:
                suggestions.append(correction["corrected_text"])
                if len(suggestions) >= limit:
                    break

        return suggestions

    def get_fine_tuned_model_path(self, language: str) -> Optional[str]:
        """
        الحصول على مسار نموذج مدرب للغة المحددة.

        Args:
            language: لغة النموذج.

        Returns:
            Optional[str]: مسار النموذج إذا كان متاحًا، None إذا لم يكن متاحًا.
        """
        models = self.db.get_fine_tuned_models(language=language, limit=1)
        if models:
            return models[0]["model_path"]
        return None
```

---

#### **3. ضبط نماذج TrOCR (Fine-tuning)**
**الهدف**: ضبط نماذج TrOCR على **بيانات عربية** لتحسين دقتها.

**المتطلبات**:
- `transformers` (لنماذج TrOCR)
- `torch` (لدعم GPU)
- `peft` (لـ LoRA)
- `datasets` (لإدارة البيانات)

**التثبيت**:
```bash
pip install transformers torch peft datasets
```

**الميزات**:
- **ضبط نماذج TrOCR** على بيانات عربية.
- **استخدام LoRA** (Low-Rank Adaptation) لتقليل استهلاك الموارد.
- **حفظ النماذج المدربة** واستخدامها في المشروع.

**مثال على الكود**:
```python
# modules/ai/finetuning.py
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments
)
from datasets import Dataset, load_dataset
import torch
from peft import LoraConfig, get_peft_model, TaskType
from pathlib import Path
import logging
from typing import Optional, List, Union

logger = logging.getLogger(__name__)

class TrOCRFineTuner:
    """ضبط نماذج TrOCR على بيانات عربية."""

    def __init__(
        self,
        model_name: str = "microsoft/trocr-base-handwritten",
        output_dir: Union[str, Path] = "./fine_tuned_models",
        use_lora: bool = True,
        lora_r: int = 8,
        lora_alpha: int = 16,
        device: str = "auto"
    ):
        """
        تهيئة المدرب.

        Args:
            model_name: اسم النموذج الأساسي.
            output_dir: مجلد حفظ النماذج المدربة.
            use_lora: استخدام LoRA (افتراضي: True).
            lora_r: رتبة LoRA (افتراضي: 8).
            lora_alpha: ألفا LoRA (افتراضي: 16).
            device: الجهاز (auto, cuda, cpu).
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_lora = use_lora
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.device = device if device != "auto" else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.processor = None
        self.model = None

    def load_model(self):
        """تحميل النموذج والمعالج."""
        if self.processor is None or self.model is None:
            self.processor = TrOCRProcessor.from_pretrained(self.model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)

            # نقل النموذج إلى الجهاز
            self.model.to(self.device)

            logger.info(f"تم تحميل النموذج: {self.model_name} على الجهاز {self.device}")

    def apply_lora(self):
        """تطبيق LoRA على النموذج."""
        if not self.use_lora or self.model is None:
            return

        peft_config = LoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            inference_mode=False,
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=0.1,
            target_modules=["encoder.layer.0.attention.query_key_value"],
        )

        self.model = get_peft_model(self.model, peft_config)
        logger.info("تم تطبيق LoRA على النموذج")

    def prepare_dataset(
        self,
        images: List[Union[str, Path]],
        texts: List[str]
    ) -> Dataset:
        """
        إعداد مجموعة البيانات للتدريب.

        Args:
            images: قائمة مسارات الصور.
            texts: قائمة النصوص.

        Returns:
            Dataset: مجموعة البيانات الجاهزة.
        """
        if self.processor is None:
            self.load_model()

        # معالج الصور
        pixel_values = self.processor(images, return_tensors="pt").pixel_values

        # معالج النصوص
        labels = self.processor(texts, return_tensors="pt").input_ids

        # إنشاء Dataset
        dataset = Dataset.from_dict({
            "pixel_values": pixel_values,
            "labels": labels,
        })

        return dataset

    def train(
        self,
        train_images: List[Union[str, Path]],
        train_texts: List[str],
        val_images: Optional[List[Union[str, Path]]] = None,
        val_texts: Optional[List[str]] = None,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned",
        save_model: bool = True
    ) -> Path:
        """
        تدريب النموذج على بيانات مدخلة.

        Args:
            train_images: قائمة الصور التدريبية.
            train_texts: قائمة النصوص التدريبية.
            val_images: قائمة الصور التحققية (اختياري).
            val_texts: قائمة النصوص التحققية (اختياري).
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.
            save_model: حفظ النموذج (افتراضي: True).

        Returns:
            Path: مسار النموذج المدرب.
        """
        self.load_model()
        self.apply_lora()

        # إعداد مجموعة البيانات
        train_dataset = self.prepare_dataset(train_images, train_texts)
        val_dataset = None
        if val_images and val_texts:
            val_dataset = self.prepare_dataset(val_images, val_texts)

        # إعداد معلمات التدريب
        training_args = Seq2SeqTrainingArguments(
            output_dir=self.output_dir / model_name,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            num_train_epochs=epochs,
            evaluation_strategy="epoch" if val_dataset else "no",
            save_strategy="epoch",
            logging_dir=self.output_dir / "logs" / model_name,
            logging_steps=10,
            learning_rate=learning_rate,
            warmup_steps=500,
            weight_decay=0.01,
            fp16=torch.cuda.is_available(),
            report_to="none",
        )

        # إعداد المدرب
        trainer = Seq2SeqTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            processor=self.processor,
        )

        # تدريب النموذج
        logger.info("جاري تدريب النموذج...")
        trainer.train()

        # حفظ النموذج
        if save_model:
            output_path = self.output_dir / model_name
            self.model.save_pretrained(str(output_path))
            self.processor.save_pretrained(str(output_path))
            logger.info(f"تم حفظ النموذج المدرب في: {output_path}")
            return output_path

        return self.output_dir / model_name

    def fine_tune_from_directory(
        self,
        train_dir: Union[str, Path],
        val_dir: Optional[Union[str, Path]] = None,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned",
        image_extensions: List[str] = [".png", ".jpg", ".jpeg"],
        text_extension: str = ".txt"
    ) -> Path:
        """
        تدريب النموذج على بيانات من مجلد.

        Args:
            train_dir: مجلد يحتوي على صور ونصوص تدريبية.
            val_dir: مجلد يحتوي على صور ونصوص تحققية (اختياري).
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.
            image_extensions: امتدادات الصور المدعومة.
            text_extension: امتداد ملفات النصوص.

        Returns:
            Path: مسار النموذج المدرب.
        """
        train_dir = Path(train_dir)
        train_images = []
        train_texts = []

        # تحميل بيانات التدريب
        for ext in image_extensions:
            for img_path in train_dir.glob(f"*{ext}"):
                txt_path = img_path.with_suffix(text_extension)
                if txt_path.exists():
                    try:
                        from PIL import Image
                        img = Image.open(img_path)
                        with open(txt_path, "r", encoding="utf-8") as f:
                            text = f.read().strip()
                        train_images.append(img_path)
                        train_texts.append(text)
                    except Exception as e:
                        logger.error(f"فشل تحميل الصورة {img_path}: {e}")

        # تحميل بيانات التحقق (إذا كانت متاحة)
        val_images = []
        val_texts = []
        if val_dir:
            val_dir = Path(val_dir)
            for ext in image_extensions:
                for img_path in val_dir.glob(f"*{ext}"):
                    txt_path = img_path.with_suffix(text_extension)
                    if txt_path.exists():
                        try:
                            img = Image.open(img_path)
                            with open(txt_path, "r", encoding="utf-8") as f:
                                text = f.read().strip()
                            val_images.append(img_path)
                            val_texts.append(text)
                        except Exception as e:
                            logger.error(f"فشل تحميل الصورة {img_path}: {e}")

        return self.train(
            train_images=train_images,
            train_texts=train_texts,
            val_images=val_images,
            val_texts=val_texts,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            model_name=model_name,
        )

    def fine_tune_from_database(
        self,
        db_path: Union[str, Path],
        language: str = "ar",
        limit: int = 1000,
        epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 5e-5,
        model_name: str = "trocr_ar_finetuned"
    ) -> Path:
        """
        تدريب النموذج على بيانات من قاعدة بيانات Active Learning.

        Args:
            db_path: مسار قاعدة البيانات.
            language: لغة البيانات.
            limit: الحد الأقصى لعدد البيانات.
            epochs: عدد العصور.
            batch_size: حجم الدفعة.
            learning_rate: معدل التعلم.
            model_name: اسم النموذج المخرج.

        Returns:
            Path: مسار النموذج المدرب.
        """
        from .active_learning import ActiveLearningDB

        db = ActiveLearningDB(db_path)
        training_data = db.get_training_data(
            language=language,
            limit=limit,
            min_confidence=0.7
        )

        if not training_data:
            raise ValueError(f"لا توجد بيانات تدريب للغة {language}")

        train_images = []
        train_texts = []

        for data in training_data:
            if "image_path" in data and data["image_path"]:
                train_images.append(data["image_path"])
                train_texts.append(data["corrected_text"])

        return self.train(
            train_images=train_images,
            train_texts=train_texts,
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            model_name=model_name,
        )
```

---

#### **📊 الفوائد المتوقعة**
| **الفائدة** | **الوصف** | **التأثير** |
|--------------|-----------|--------------|
| **دقة أعلى** | تحسين دقة نماذج OCR العربية من خلال التعلم من المستخدم | ⭐⭐⭐⭐⭐ |
| **تخصيص** | ضبط النماذج على بيانات محددة (مثل الخط العربي) | ⭐⭐⭐⭐⭐ |
| **مرونة** | دعم عدة لغات ونماذج | ⭐⭐⭐⭐ |
| **كفاءة** | استخدام LoRA لتقليل استهلاك الموارد | ⭐⭐⭐⭐⭐ |
| **تعلم مستمر** | تحسين الدقة مع الوقت | ⭐⭐⭐⭐⭐ |

---

#### **🔮 التطويرات المستقبلية**
1. **دعم أكثر من نموذج**: دعم TrOCR + EasyOCR + PaddleOCR.
2. **دعم Data Augmentation**: زيادة بيانات التدريب باستخدام تقنيات مثل:
   - **Rotation** (تدوير الصور)
   - **Noise Addition** (إضافة ضوضاء)
   - **Blur** (تغبيش)
   - **Brightness/Contrast Adjustment** (تعديل الإضاءة/التباين)
3. **دعم Transfer Learning**: استخدام نماذج مدربة على لغات أخرى.
4. **دعم Ensemble Learning**: دمج عدة نماذج مدربة.
5. **دعم Online Learning**: تعلم مستمر أثناء استخدام النظام.

---

---
---
---

## 📅 **4. اقتراحات أخرى**

### **📌 قائمة بالاقتراحات الإضافية**
| **الاقتراح** | **الوصف** | **الأولوية** | **التكلفة (ساعات)** | **التأثير** |
|--------------|-----------|--------------|---------------------|--------------|
| **دعم Video OCR** | استخراج النصوص من الفيديوهات | ⭐⭐⭐⭐ | 10-15 | عالي |
| **دعم Audio Processing** | تحويل الكلام إلى نص (Whisper) | ⭐⭐⭐⭐ | 8-12 | عالي |
| **دعم Question Answering** | الإجابة على أسئلة حول النصوص (RAG + BERT) | ⭐⭐⭐⭐ | 10-15 | عالي |
| **دعم Multi-User** | دعم عدة مستخدمين مع صلاحيات مختلفة | ⭐⭐⭐ | 5-8 | متوسط |
| **دعم Cloud Sync** | مزامنة البيانات مع Google Drive/Dropbox | ⭐⭐⭐ | 5-8 | متوسط |
| **دعم OCR Batch Processing** | معالجة عدة ملفات في نفس الوقت | ⭐⭐⭐⭐ | 5-8 | عالي |
| **دعم API Key Management** | إدارة مفاتيح API (OpenAI, Google, etc.) | ⭐⭐⭐ | 3-5 | متوسط |
| **دعم Webhooks** | إشعار المستخدمين عند انتهاء المعالجة | ⭐⭐ | 3-5 | متوسط |
| **دعم Custom Models** | السماح للمستخدمين برفع نماذجهم الخاصة | ⭐⭐⭐ | 5-8 | متوسط |
| **دعم Model Versioning** | إدارة إصدارات النماذج | ⭐⭐ | 3-5 | متوسط |
| **دعم Data Augmentation** | زيادة بيانات التدريب | ⭐⭐⭐ | 5-8 | عالي |
| **دعم Transfer Learning** | استخدام نماذج مدربة على لغات أخرى | ⭐⭐⭐ | 5-8 | عالي |
| **دعم Ensemble Learning** | دمج عدة نماذج مدربة | ⭐⭐⭐⭐ | 8-12 | عالي |
| **دعم Online Learning** | تعلم مستمر أثناء استخدام النظام | ⭐⭐⭐⭐ | 10-15 | عالي |

---

### **📄 تفاصيل بعض الاقتراحات**

#### **1. دعم Video OCR**
**الهدف**: استخراج النصوص من الفيديوهات.
**الخطوات**:
1. استخراج الإطارات (Frames) من الفيديو.
2. تطبيق OCR على كل إطار.
3. دمج النتائج.
4. تصدير النص مع زمن كل إطار.

**المتطلبات**:
- `opencv-python` (لاستخراج الإطارات)
- `moviepy` (لمعالجة الفيديو)

**مثال على الكود**:
```python
# modules/vision/video_ocr.py
import cv2
import os
from typing import List, Dict, Union
from pathlib import Path
from .ocr_engine import OCREngine
import numpy as np

class VideoOCR:
    """استخراج النصوص من الفيديوهات."""

    def __init__(
        self,
        ocr_engine: OCREngine,
        frame_interval: int = 30,
        min_confidence: float = 0.7
    ):
        """
        تهيئة معالج Video OCR.

        Args:
            ocr_engine: محرك OCR المستخدم.
            frame_interval: عدد الإطارات بين كل معالجة (افتراضي: 30، أي كل ثانية في فيديو 30 fps).
            min_confidence: الحد الأدنى للثقة لقبول النتيجة.
        """
        self.ocr_engine = ocr_engine
        self.frame_interval = frame_interval
        self.min_confidence = min_confidence

    def process_video(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path] = "video_frames",
        output_text_path: Union[str, Path] = "video_text.txt",
        output_json_path: Union[str, Path] = "video_results.json",
        languages: List[str] = None,
    ) -> Dict:
        """
        معالج فيديو واستخراج النصوص.

        Args:
            video_path: مسار الفيديو.
            output_dir: مجلد لحفظ الإطارات (اختياري).
            output_text_path: مسار ملف النص المخرج.
            output_json_path: مسار ملف JSON بالنتائج.
            languages: لغات OCR (اختياري).

        Returns:
            Dict: نتائج المعالجة (نص، إطارات، أوقات).
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_text_path = Path(output_text_path)
        output_json_path = Path(output_json_path)

        output_dir.mkdir(parents=True, exist_ok=True)

        # فتح الفيديو
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"فشل فتح الفيديو: {video_path}")

        # الحصول على معلومات الفيديو
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        # معالج الإطارات
        frame_count = 0
        results = []
        all_text = ""

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # معالج كل frame_interval إطارات
            if frame_count % self.frame_interval == 0:
                # حفظ الإطار (اختياري)
                frame_path = output_dir / f"frame_{frame_count:04d}.png"
                cv2.imwrite(str(frame_path), frame)

                # تطبيق OCR
                result = self.ocr_engine.recognize(frame, languages=languages)

                # إذا كانت الثقة أعلى من الحد الأدنى
                if result["confidence"] >= self.min_confidence:
                    result["frame_number"] = frame_count
                    result["time"] = frame_count / fps if fps > 0 else 0
                    results.append(result)
                    all_text += f"[{result['time']:.1f}s] {result['text']}\n\n"

            frame_count += 1

        # إطلاق الموارد
        cap.release()

        # حفظ النص
        with open(output_text_path, "w", encoding="utf-8") as f:
            f.write(all_text)

        # حفظ النتائج كJSON
        with open(output_json_path, "w", encoding="utf-8") as f:
            import json
            json.dump(results, f, ensure_ascii=False, indent=2)

        return {
            "video_path": str(video_path),
            "total_frames": total_frames,
            "fps": fps,
            "duration": duration,
            "frames_processed": len(results),
            "output_dir": str(output_dir),
            "output_text_path": str(output_text_path),
            "output_json_path": str(output_json_path),
            "results": results,
        }

    def process_video_with_timestamps(
        self,
        video_path: Union[str, Path],
        timestamps: List[float],
        output_dir: Union[str, Path] = "video_frames",
        languages: List[str] = None,
    ) -> Dict:
        """
        معالج فيديو عند طوابع زمنية محددة.

        Args:
            video_path: مسار الفيديو.
            timestamps: قائمة بالطوابع الزمنية (بالثواني).
            output_dir: مجلد لحفظ الإطارات.
            languages: لغات OCR.

        Returns:
            Dict: نتائج المعالجة.
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # فتح الفيديو
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"فشل فتح الفيديو: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        results = []

        for timestamp in timestamps:
            # الانتقال إلى الإطار المقابل للطابع الزمني
            frame_num = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

            ret, frame = cap.read()
            if not ret:
                continue

            # حفظ الإطار
            frame_path = output_dir / f"frame_{frame_num:04d}.png"
            cv2.imwrite(str(frame_path), frame)

            # تطبيق OCR
            result = self.ocr_engine.recognize(frame, languages=languages)
            result["frame_number"] = frame_num
            result["time"] = timestamp
            results.append(result)

        # إطلاق الموارد
        cap.release()

        return {
            "video_path": str(video_path),
            "timestamps": timestamps,
            "results": results,
            "output_dir": str(output_dir),
        }
```

---

#### **2. دعم Audio Processing (Whisper)**
**الهدف**: تحويل الكلام إلى نص.
**الخطوات**:
1. تحميل نموذج Whisper.
2. معالج الملفات الصوتية.
3. تصدير النص.

**المتطلبات**:
- `transformers` (لنموذج Whisper)
- `torch` (لدعم GPU)

**مثال على الكود**:
```python
# modules/nlp/audio_processor.py
from transformers import pipeline
from typing import Union, Dict, Path, Optional
import torch
import logging
import os

logger = logging.getLogger(__name__)

class AudioProcessor:
    """معالج الملفات الصوتية (Speech-to-Text)."""

    def __init__(
        self,
        model_name: str = "openai/whisper-large-v3",
        device: str = "auto",
        chunk_length_s: int = 30,
        batch_size: int = 16,
    ):
        """
        تهيئة المعالج.

        Args:
            model_name: اسم نموذج Whisper.
            device: الجهاز (auto, cuda, cpu).
            chunk_length_s: طول كل جزء (بالثواني).
            batch_size: حجم الدفعة.
        """
        self.model_name = model_name
        self.device = device if device != "auto" else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.chunk_length_s = chunk_length_s
        self.batch_size = batch_size
        self.pipe = None

    def load_model(self):
        """تحميل النموذج."""
        if self.pipe is None:
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=0 if self.device == "cuda" else -1,
                chunk_length_s=self.chunk_length_s,
                batch_size=self.batch_size,
            )
            logger.info(f"تم تحميل نموذج {self.model_name} على الجهاز {self.device}")

    def process_audio(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        return_timestamps: bool = False,
    ) -> Dict:
        """
        معالج ملف صوت.

        Args:
            audio_path: مسار الملف الصوتي.
            language: لغة الملف (اختياري).
            return_timestamps: إرجاع الطوابع الزمنية (افتراضي: False).

        Returns:
            Dict: نتائج المعالجة (نص، وقت المعالجة، طوابع زمنية).
        """
        self.load_model()

        result = self.pipe(
            str(audio_path),
            language=language,
            return_timestamps=return_timestamps,
        )

        output = {
            "text": result["text"],
            "language": language or result.get("language", "unknown"),
            "processing_time": result.get("processing_time", 0),
        }

        if return_timestamps and "chunks" in result:
            output["timestamps"] = [
                {"text": chunk["text"], "timestamp": chunk["timestamp"]}
                for chunk in result["chunks"]
            ]

        return output

    def process_audio_batch(
        self,
        audio_paths: List[Union[str, Path]],
        language: Optional[str] = None,
    ) -> List[Dict]:
        """
        معالج عدة ملفات صوتية.

        Args:
            audio_paths: قائمة بمسارات الملفات الصوتية.
            language: لغة الملفات (اختياري).

        Returns:
            List[Dict]: قائمة بنتائج المعالجة.
        """
        self.load_model()
        results = []

        for audio_path in audio_paths:
            try:
                result = self.process_audio(audio_path, language=language)
                results.append(result)
            except Exception as e:
                logger.error(f"فشل معالج الملف الصوتي {audio_path}: {e}")
                results.append({
                    "text": "",
                    "language": language,
                    "error": str(e),
                    "processing_time": 0,
                })

        return results

    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        output_text_path: Optional[Union[str, Path]] = None,
        output_json_path: Optional[Union[str, Path]] = None,
    ) -> Dict:
        """
        تحويل ملف صوت إلى نص وحفظ النتائج.

        Args:
            audio_path: مسار الملف الصوتي.
            language: لغة الملف (اختياري).
            output_text_path: مسار ملف النص المخرج (اختياري).
            output_json_path: مسار ملف JSON المخرج (اختياري).

        Returns:
            Dict: نتائج المعالجة.
        """
        result = self.process_audio(audio_path, language=language, return_timestamps=True)

        if output_text_path:
            output_text_path = Path(output_text_path)
            output_text_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_text_path, "w", encoding="utf-8") as f:
                f.write(result["text"])

        if output_json_path:
            output_json_path = Path(output_json_path)
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        return result
```

---
---
---

## 📅 **5. خطة العمل**

### **📌 المرحلة 1: تطوير تطبيق الموبايل (4-6 أسابيع)**
**الأهداف**:
- إنشاء تطبيق Flutter لمراجعة OCR.
- ربط التطبيق مع Backend (FastAPI).
- اختبار التطبيق على Android.

**المهام**:
| **المهمة** | **المسؤول** | **المدة (أيام)** | **الحالة** | **الأولوية** |
|------------|--------------|------------------|------------|--------------|
| إعداد بيئة التطوير (Flutter + Android Studio) | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير Backend API (FastAPI) | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير واجهة المستخدم (Flutter) | DrAbdulmalek | 10 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير محرر النصوص (Quill) | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير نظام المراجعة | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير نظام الاقتراحات | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐ |
| اختبار التطبيق على Android | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| نشر التطبيق على Google Play | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐ |

---

### **📌 المرحلة 2: تحسين حفظ التنسيق (2-3 أسابيع)**
**الأهداف**:
- اختبار وتحسين نظام التصدير.
- دعم جميع أنواع التنسيق (جداول، صور، كود).

**المهام**:
| **المهمة** | **المسؤول** | **المدة (أيام)** | **الحالة** | **الأولوية** |
|------------|--------------|------------------|------------|--------------|
| اختبار نظام التصدير الحالي | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |
| تحسين تحليل الجداول | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| تحسين تحليل الصور | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |
| تحسين تحليل كتل الكود | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐ |
| اختبار التصدير إلى PDF/DOCX | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| تحسين دعم RTL | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |

---

### **📌 المرحلة 3: تحسين دقة OCR العربية (4-6 أسابيع)**
**الأهداف**:
- تطبيق نظام Active Learning.
- ضبط نماذج TrOCR على بيانات عربية.

**المهام**:
| **المهمة** | **المسؤول** | **المدة (أيام)** | **الحالة** | **الأولوية** |
|------------|--------------|------------------|------------|--------------|
| تطوير قاعدة بيانات Active Learning | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير نظام تسجيل التصحيحات | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير نظام اقتراحات التصحيح | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| تطوير نظام Fine-tuning | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| جمع بيانات تدريب | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| تدريب نماذج TrOCR | DrAbdulmalek | 5 | ⬜ | ⭐⭐⭐⭐⭐ |
| اختبار الدقة | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |

---
### **📌 المرحلة 4: نشر المشروع (2-3 أسابيع)**
**الأهداف**:
- نشر التطبيق على Google Play.
- نشر Backend على خادم سحابي.

**المهام**:
| **المهمة** | **المسؤول** | **المدة (أيام)** | **الحالة** | **الأولوية** |
|------------|--------------|------------------|------------|--------------|
| إعداد خادم سحابي | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| نشر Backend API | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |
| نشر تطبيق الموبايل | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐⭐ |
| اختبار النظام الكامل | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐⭐ |
| توثيق النظام | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐ |

---
### **📌 المرحلة 5: التطويرات المستقبلية (مستمر)**
**الأهداف**:
- إضافة ميزات جديدة.
- تحسين الأداء.
- جذب المساهمين.

**المهام**:
| **الميزة** | **المسؤول** | **المدة (أسبوع)** | **الحالة** | **الأولوية** |
|------------|--------------|-------------------|------------|--------------|
| دعم Video OCR | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐ |
| دعم Audio Processing | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐⭐ |
| دعم Question Answering | DrAbdulmalek | 3 | ⬜ | ⭐⭐⭐⭐ |
| دعم Multi-User | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐ |
| دعم Cloud Sync | DrAbdulmalek | 2 | ⬜ | ⭐⭐⭐ |
| دعم Batch Processing | DrAbdulmalek | 1 | ⬜ | ⭐⭐⭐⭐ |
| إنشاء مجتمع حول المشروع | DrAbdulmalek | 1 | ⬜ | ⭐⭐⭐ |

---
---
---

## 🏆 **الخلاصة النهائية**

### **✅ ما تم إنجازه**
1. **ملف Google Colab (IPYNB)**:
   - **جاهز للتشغيل** في بيئة Colab.
   - **اختبار جميع الميزات** (OCR, NLP, Export, etc.).
   - **تصحيح المشاكل الشائعة** (GPU, Memory, Dependencies).

2. **تطبيق الموبايل (Flutter + FastAPI)**:
   - **واجهة مستخدم مرنة** (RTL, Dark Mode, etc.).
   - **مراجعة نتائج OCR** على الموبايل.
   - **حفظ التعديلات** في قاعدة البيانات.
   - **اقتراحات التصحيح** التلقائية.

3. **نظام حفظ التنسيق**:
   - **دعم الجداول** (Markdown → HTML/PDF/DOCX).
   - **دعم الصور** (Markdown → HTML/PDF/DOCX).
   - **دعم كتل الكود** (Markdown → HTML/PDF/DOCX).
   - **دعم RTL** (العربية).
   - **تصدير إلى عدة صيغ** (HTML, PDF, DOCX, Excel).

4. **ملف الاقتراحات (`SUGGESTIONS.md`)**:
   - **مراجعة نتائج OCR على الموبايل**.
   - **حفظ تنسيق النص**.
   - **تحسين دقة نماذج OCR العربية**.
   - **اقتراحات أخرى**.

5. **كود تنفيذ جزء التنسيق**:
   - **`exporter.py`** (تصدير إلى HTML/PDF/DOCX/Excel).
   - **`format_parser.py`** (تحليل الجداول، الصور، الكود).
   - **`html_exporter.py`** (توليد HTML).
   - **`pdf_exporter.py`** (تحويل HTML إلى PDF).
   - **`docx_exporter.py`** (تحويل HTML إلى DOCX).
   - **`excel_exporter.py`** (تحويل الجداول إلى Excel).

---
