# سياسة الأمان — OmniFile AI Processor
# Security Policy

---

## الإبلاغ عن الثغرات الأمنية — Reporting Vulnerabilities

نحن نأخذ أمن هذا المشروع بجدية تامة. إذا اكتشفت ثغرة أمنية، يُرجى الإبلاغ عنها بمسؤولية دون نشرها علنياً.

### طريقة الإبلاغ

1. **البريد الإلكتروني:** أرسل التقرير إلى <Abdulmalek.husseini@gmail.com> مع الموضوع `ثغرة أمنية — OmniFile AI Processor`
2. **لا تنشر الثغرة علنياً** قبل إصلاحها والاتفاق على جدول زمني للنشر
3. **مدة الاستجابة:** سنرد خلال **72 ساعة** كحد أقصى وسنُبلغك بخطة الإصلاح
4. **الإصلاح:** سنصدر تحديثاً أمنياً خلال **14 يوماً** من تأكيد الثغرة (حسب شدتها)
5. **الاعتراف:** سنشكرك في سجل التغييرات `CHANGELOG.md` ما لم تُفضل البقاء مجهولاً

### ما يجب تضمينه في التقرير

- وصف الثغرة والخطوات لإعادة إنتاجها (Proof of Concept)
- نسخة المشروع وبيئة التشغيل (OS, Python, etc.)
- تقدير مستوى الخطورة (Critical / High / Medium / Low)
- اقتراحات للإصلاح إن وجدت

---

## النُّسخ المدعومة — Supported Versions

| النسخة | الحالة | ملاحظات |
|--------|--------|---------|
| **v5.x** (current) | مدعومة بالكامل | تلقي تحديثات أمنية |
| v4.x | صيانة أمنية فقط | إصلاحات حرجة فقط |
| v3.x وأقدم | غير مدعومة | يجب الترقية |

---

## مزايا الأمان في المشروع — Security Features

### 1. منع حقن SQL — SQL Injection Prevention

يستخدم المشروع فئة `BaseDB` في `modules/core/base_db.py` كأساس لكل قواعد البيانات:

- **Parameterized Queries:** كل استعلامات SQL تستخدم معاملات مُعَلَّمة (`?`) بدلاً من سَلسَلة النصوص مباشرة:
  ```python
  conn.execute("INSERT INTO words VALUES(?, ?)", (word, count))
  ```
- **Validation of Table/Column Names:** التحقق من أسماء الجداول والأعمدة بـ Regex:
  ```python
  if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
      raise ValueError(f"Invalid table name: {table}")
  ```
- **WAL Mode:** استخدام `PRAGMA journal_mode=WAL` لتحسين الأداء والأمان المتزامن
- **Foreign Keys:** تفعيل `PRAGMA foreign_keys=ON` لحماية سلامة البيانات
- **Context Manager:** `connection()` يُنفِّذ `commit` عند النجاح و `rollback` عند الفشل تلقائياً

### 2. كشف البيانات الحساسة (PII Detection)

يوفّر المشروع فاحص بيانات حساسة متقدم في `modules/security/sensitive_data_scanner.py`:

- **مكتبة Microsoft Presidio:** كشف دقيق باستخدام `presidio-analyzer` و `presidio-anonymizer`
- **طبقة Regex احتياطية:** تعمل دائماً حتى بدون presidio
- **الأنماط المدعومة:**
  - أرقام بطاقات الائتمان (CREDIT_CARD)
  - عناوين البريد الإلكتروني (EMAIL_ADDRESS)
  - أرقام الهواتف (PHONE_NUMBER)
  - عناوين IP (IP_ADDRESS)
  - أرقام الضمان الاجتماعي (SSN)
  - مفاتيح API و JWT (API_KEY, JWT_TOKEN)
  - مفاتيح AWS (AWS_KEY)
  - المفاتيح الخاصة (PRIVATE_KEY)
  - أرقام IBAN البنكية (IBAN)
- **إخفاء الهوية:** دالة `anonymize_text()` لاستبدال البيانات الحساسة بـ `[REDACTED]`
- **أنماط مخصصة:** إمكانية إضافة أنماط كشف إضافية عبر `add_custom_pattern()`

### 3. فحص الاعتماديات — Dependency Scanning

- **Snyk:** مدمج في مسار CI/CD لفحص الثغرات في المكتبات الخارجية تلقائياً
- **التحديث الدوري:** مراجعة الاعتماديات بانتظام وتحديثها عند اكتشاف ثغرات

### 4. حماية الأكواد — Code Protection

يتوفّر `CodeProtector` في `modules/security/code_protector.py`:

- **كشف ملفات الأكواد:** دعم 60+ امتداد (`.py`, `.js`, `.java`, `.cpp`, `.sql`, ...)
- **استخراج أجزاء الأكواد:** من نصوص Markdown (` ``` `) و HTML (`<code>`, `<pre>`)
- **حماية النصوص:** لف أجزاء الأكواد بعلامات حماية لمنع تعديلها أثناء المعالجة النصية
- **كشف اللغة:** دعم 7 لغات برمجية (Python, JavaScript, Java, C++, Go, Rust, SQL)
- **منع التدقيق الإملائي:** منع فحص الإملاء داخل أجزاء الأكواد البرمجية

### 5. دعم التشفير — Encryption Support

يتوفّر `FileEncryptor` في `modules/security/encryption.py`:

- **تشفير Fernet (AES-128-CBC):** تشفير وفك تشفير الملفات باستخدام مكتبة `cryptography`
- **توليد مفاتيح عشوائية:** أو استخدام مفتاح/كلمة مرور مخصصة
- **تشفير المجلدات:** تشفير كامل المجلدات بنمط `glob`
- **حفظ المفاتيح:** حفظ المفاتيح في ملفات بصلاحيات `0o600`

### 6. أنماط التحقق من المدخلات — Input Validation Patterns

- **Allowed Extensions:** القائمة البيضاء لامتدادات الملفات المقبولة (في `OmniFileConfig.allowed_extensions`)
- **Blocked Patterns:** حظر أنماط خطيرة مثل `password`, `secret`, `api_key`
- **File Fingerprint:** بصمة الملفات (`modules/core/file_fingerprint.py`) لمنع التكرار والملفات الضارة
- **Secure File Handler:** معالجة آمنة للملفات (`modules/security/secure_file_handler.py`)
- **Audit Logging:** تسجيل المراجعة لكل العمليات (`modules/security/audit_logger.py`)

---

## إدارة الأسرار — Secrets Management

### أفضل الممارسات

1. **لا ترتكب الأسرار في الكود (Never Commit Secrets):** لا تضع مفاتيح API أو كلمات المرور في الكود المصدري
2. **استخدم متغيرات البيئة:** كل البيانات الحساسة تُمرَّر عبر Environment Variables
3. **ملف `.env`:** استخدم ملف `.env` محلي (مُضاف لـ `.gitignore`) للتطوير
4. **تدوير المفاتيح:** غيِّر مفاتيح API وTokens بشكل دوري

### المتغيرات البيئية الحساسة — Environment Variables

| المتغير | الاستخدام | الحساسية |
|---------|-----------|----------|
| `GEMINI_API_KEY` | مفتاح Google Gemini API | عالية |
| `OPENAI_API_KEY` | مفتاح OpenAI API | عالية |
| `HF_TOKEN` | رمز HuggingFace Authentication | عالية |
| `GITHUB_TOKEN` | رمز GitHub Personal Access | عالية |
| `GATEWAY_AUTH_TOKEN` | رمز مصادقة AI Gateway | عالية |
| `CELERY_BROKER_URL` | عنوان Redis/Celery | متوسطة |
| `DATABASE_URL` | سلسلة اتصال قاعدة البيانات | متوسطة |

### إعداد متغيرات البيئة

```bash
# عبر ملف .env (للتطوير فقط)
echo "GEMINI_API_KEY=your-key-here" >> .env

# أو عبر export (لينكس/ماك)
export GEMINI_API_KEY="your-key-here"

# أو عبر OmniFileConfig
cfg.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
```

---

## اعتبارات أمنية معروفة — Known Security Considerations

1. **قاعدة بيانات SQLite محلية:** SQLite لا يدعم التحكم بالوصول على مستوى المستخدمين. تأكد من حماية مجلد المشروع بأذونات نظام التشغيل المناسبة
2. **نماذج ML المحمّلة:** النماذج المُحمَّلة من HuggingFace قد تحتوي على كود ضار. استخدم `HF_TOKEN` مع مصادر موثوقة فقط
3. **معالجة الملفات المُحمَّلة:** تأكد من فحص الملفات المُحمَّلة قبل المعالجة باستخدام `SensitiveDataScanner` و `SecureFileHandler`
4. **AI Gateway:** واجهة AI Gateway (المنفذ 8082) يجب أن تكون خلف جدار حماية ولا تُعرض مباشرة على الإنترنت بدون مصادقة
5. **Docker:** عند استخدام Docker، لا تُمرر الأسرار عبر docker-compose.yml. استخدم Docker Secrets أو ملف `.env`
6. **التخزين المؤقت:** مجلد `models_cache` يحتوي على نماذج كبيرة. تأكد من عدم مشاركته علنياً

---

## ختم زمني — Timestamp

آخر تحديث لهذه الوثيقة: يوليو 2025

OmniFile AI Processor v5.0 — Dr. Abdulmalek Tamer Al-husseini
