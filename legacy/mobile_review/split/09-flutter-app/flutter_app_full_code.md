## 📱 **2. نظام مراجعة OCR على الموبايل (Android) - الكود الكامل**

### **📌 هيكل المشروع:**
```
omnifile_mobile/
├── lib/
│   ├── main.dart
│   ├── screens/
│   │   ├── home_screen.dart
│   │   ├── review_screen.dart
│   │   ├── settings_screen.dart
│   │   └── document_list_screen.dart
│   ├── models/
│   │   ├── document.dart
│   │   └── ocr_result.dart
│   ├── services/
│   │   ├── api_service.dart
│   │   ├── database_service.dart
│   │   └── file_service.dart
│   ├── widgets/
│   │   ├── text_editor.dart
│   │   ├── correction_suggestions.dart
│   │   ├── table_widget.dart
│   │   └── image_widget.dart
│   └── utils/
│       ├── format_utils.dart
│       └── constants.dart
├── assets/
│   └── images/
├── pubspec.yaml
└── android/
    └── app/
        └── build.gradle
```

---

### **📄 `pubspec.yaml`**
```yaml
name: omnifile_mobile
description: تطبيق مراجعة OCR لنظام OmniFile AI Processor

publish_to: 'none'

version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2
  http: ^1.1.0
  shared_preferences: ^2.2.2
  sqflite: ^2.3.0
  path_provider: ^2.1.1
  flutter_quill: ^8.0.0
  image_picker: ^1.0.4
  camera: ^0.10.5
  file_picker: ^5.3.3
  flutter_localizations:
    sdk: flutter
  intl: ^0.18.1
  provider: ^6.0.5
  cached_network_image: ^3.3.0
  photo_view: ^0.14.0
  url_launcher: ^6.1.11
  flutter_pdfview: ^2.0.1
  open_filex: ^4.0.0
  path: ^1.8.3

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0
  build_runner: ^2.4.6

flutter:
  uses-material-design: true
  assets:
    - assets/images/
```

---

### **📄 `lib/main.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:omnifile_mobile/screens/home_screen.dart';
import 'package:omnifile_mobile/utils/constants.dart';

void main() {
  runApp(const OmniFileApp());
}

class OmniFileApp extends StatelessWidget {
  const OmniFileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        useMaterial3: true,
        fontFamily: 'Amiri', // خط عربي
      ),
      darkTheme: ThemeData.dark().copyWith(
        primaryColor: Colors.blue,
        useMaterial3: true,
        fontFamily: 'Amiri',
      ),
      themeMode: ThemeMode.system,
      locale: const Locale('ar'), // اللغة العربية افتراضيًا
      supportedLocales: const [
        Locale('ar'), // العربية
        Locale('en'), // الإنجليزية
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      home: const HomeScreen(),
    );
  }
}
```

---

### **📄 `lib/utils/constants.dart`**
```dart
class AppConstants {
  static const String appName = 'OmniFile Mobile';
  static const String appVersion = '1.0.0';
  static const String apiBaseUrl = 'http://YOUR_SERVER_IP:5001'; // استبدل ب IP الخادم
  static const String defaultLanguage = 'ar';

  // ألوان التطبيق
  static const primaryColor = Color(0xFF1E88E5);
  static const secondaryColor = Color(0xFF43A047);
  static const errorColor = Color(0xFFE53935);
  static const warningColor = Color(0xFFFB8C00);
  static const infoColor = Color(0xFF1976D2);

  // إعدادات OCR
  static const List<String> supportedLanguages = ['ar', 'en', 'de'];
  static const Map<String, String> languageNames = {
    'ar': 'العربية',
    'en': 'English',
    'de': 'Deutsch',
  };

  // إعدادات التصدير
  static const List<String> exportFormats = ['html', 'pdf', 'docx', 'txt'];
  static const Map<String, String> exportFormatNames = {
    'html': 'HTML',
    'pdf': 'PDF',
    'docx': 'Word',
    'txt': 'نص عادي',
  };
}
```

---

### **📄 `lib/models/document.dart`**
```dart
class Document {
  final String id;
  final String fileName;
  final String filePath;
  final String rawText;
  final String processedText;
  final int pageCount;
  final String language;
  final double confidence;
  final String status;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final List<OCRResult> ocrResults;
  final Map<String, dynamic> metadata;

  Document({
    required this.id,
    required this.fileName,
    required this.filePath,
    required this.rawText,
    required this.processedText,
    required this.pageCount,
    required this.language,
    required this.confidence,
    required this.status,
    required this.createdAt,
    this.updatedAt,
    this.ocrResults = const [],
    this.metadata = const {},
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] ?? '',
      fileName: json['file_name'] ?? '',
      filePath: json['file_path'] ?? '',
      rawText: json['raw_text'] ?? '',
      processedText: json['processed_text'] ?? '',
      pageCount: json['page_count'] ?? 0,
      language: json['language'] ?? AppConstants.defaultLanguage,
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      status: json['status'] ?? 'pending_review',
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      ocrResults: (json['ocr_results'] as List<dynamic>?)
          ?.map((e) => OCRResult.fromJson(e))
          .toList() ?? [],
      metadata: json['metadata'] ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'file_name': fileName,
      'file_path': filePath,
      'raw_text': rawText,
      'processed_text': processedText,
      'page_count': pageCount,
      'language': language,
      'confidence': confidence,
      'status': status,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'ocr_results': ocrResults.map((e) => e.toJson()).toList(),
      'metadata': metadata,
    };
  }

  Document copyWith({
    String? id,
    String? fileName,
    String? filePath,
    String? rawText,
    String? processedText,
    int? pageCount,
    String? language,
    double? confidence,
    String? status,
    DateTime? createdAt,
    DateTime? updatedAt,
    List<OCRResult>? ocrResults,
    Map<String, dynamic>? metadata,
  }) {
    return Document(
      id: id ?? this.id,
      fileName: fileName ?? this.fileName,
      filePath: filePath ?? this.filePath,
      rawText: rawText ?? this.rawText,
      processedText: processedText ?? this.processedText,
      pageCount: pageCount ?? this.pageCount,
      language: language ?? this.language,
      confidence: confidence ?? this.confidence,
      status: status ?? this.status,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      ocrResults: ocrResults ?? this.ocrResults,
      metadata: metadata ?? this.metadata,
    );
  }
}

class OCRResult {
  final String id;
  final String documentId;
  final int pageNum;
  final String wordText;
  final String rawText;
  final double confidence;
  final String modelSource;
  final DateTime createdAt;

  OCRResult({
    required this.id,
    required this.documentId,
    required this.pageNum,
    required this.wordText,
    required this.rawText,
    required this.confidence,
    required this.modelSource,
    required this.createdAt,
  });

  factory OCRResult.fromJson(Map<String, dynamic> json) {
    return OCRResult(
      id: json['id'] ?? '',
      documentId: json['document_id'] ?? '',
      pageNum: json['page_num'] ?? 0,
      wordText: json['word_text'] ?? '',
      rawText: json['raw_text'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      modelSource: json['model_source'] ?? '',
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'document_id': documentId,
      'page_num': pageNum,
      'word_text': wordText,
      'raw_text': rawText,
      'confidence': confidence,
      'model_source': modelSource,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
```

---

### **📄 `lib/services/api_service.dart`**
```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:omnifile_mobile/models/document.dart';
import 'package:omnifile_mobile/utils/constants.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();

  final String _baseUrl = AppConstants.apiBaseUrl;
  late SharedPreferences _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  Future<String> get _authToken async {
    return _prefs.getString('auth_token') ?? '';
  }

  // ============ Document API ============

  Future<List<Document>> getDocuments({
    int limit = 20,
    int offset = 0,
    String status = 'pending_review',
  }) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/documents?limit=$limit&offset=$offset&status=$status'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return (data['documents'] as List<dynamic>)
            .map((e) => Document.fromJson(e))
            .toList();
      } else {
        throw Exception('فشل تحميل المستندات: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل الاتصال بالخادم: $e');
    }
  }

  Future<Document> getDocument(String docId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/documents/$docId'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return Document.fromJson(json.decode(response.body));
      } else {
        throw Exception('فشل تحميل المستند: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل الاتصال بالخادم: $e');
    }
  }

  Future<Document> uploadDocument({
    required File file,
    String? language,
    List<String>? engines,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/api/documents/upload'),
      );

      request.headers.addAll({
        'Authorization': 'Bearer ${await _authToken}',
      });

      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          file.path,
        ),
      );

      if (language != null) {
        request.fields['language'] = language;
      }

      if (engines != null) {
        request.fields['engines'] = engines.join(',');
      }

      final response = await request.send();

      if (response.statusCode == 200) {
        final responseBody = await response.stream.bytesToString();
        return Document.fromJson(json.decode(responseBody));
      } else {
        throw Exception('فشل رفع الملف: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل رفع الملف: $e');
    }
  }

  Future<bool> saveCorrections({
    required String docId,
    required String correctedText,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/documents/$docId/corrections'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'corrected_text': correctedText,
        }),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        throw Exception('فشل حفظ التعديلات: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل حفظ التعديلات: $e');
    }
  }

  Future<bool> markAsReviewed(String docId) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/documents/$docId/mark_reviewed'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        throw Exception('فشل تحديد المستند كمراجع: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل تحديد المستند كمراجع: $e');
    }
  }

  // ============ OCR API ============

  Future<Map<String, dynamic>> processOCR({
    required File imageFile,
    String? language,
    List<String>? engines,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/api/ocr'),
      );

      request.headers.addAll({
        'Authorization': 'Bearer ${await _authToken}',
      });

      request.files.add(
        await http.MultipartFile.fromPath(
          'file',
          imageFile.path,
        ),
      );

      if (language != null) {
        request.fields['language'] = language;
      }

      if (engines != null) {
        request.fields['engines'] = engines.join(',');
      }

      final response = await request.send();

      if (response.statusCode == 200) {
        final responseBody = await response.stream.bytesToString();
        return json.decode(responseBody);
      } else {
        throw Exception('فشل معالج OCR: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل معالج OCR: $e');
    }
  }

  // ============ Export API ============

  Future<String> exportDocument({
    required String docId,
    required String format,
    String? fileName,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/documents/$docId/export?format=$format'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          if (fileName != null) 'file_name': fileName,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['file_url'] ?? '';
      } else {
        throw Exception('فشل تصدير المستند: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل تصدير المستند: $e');
    }
  }

  // ============ Suggestions API ============

  Future<List<String>> getSuggestions({
    required String text,
    required String language,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/suggestions'),
        headers: {
          'Authorization': 'Bearer ${await _authToken}',
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'text': text,
          'language': language,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<String>.from(data['suggestions']);
      } else {
        throw Exception('فشل الحصول على الاقتراحات: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل الحصول على الاقتراحات: $e');
    }
  }

  // ============ Auth API ============

  Future<bool> login({
    required String username,
    required String password,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/auth/login'),
        headers: {
          'Content-Type': 'application/json',
        },
        body: json.encode({
          'username': username,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        await _prefs.setString('auth_token', data['access_token']);
        return true;
      } else {
        throw Exception('فشل تسجيل الدخول: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('فشل تسجيل الدخول: $e');
    }
  }

  Future<bool> logout() async {
    try {
      await _prefs.remove('auth_token');
      return true;
    } catch (e) {
      throw Exception('فشل تسجيل الخروج: $e');
    }
  }
}
```

---

### **📄 `lib/services/database_service.dart`**
```dart
import 'package:sqflite/sqflite.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart';
import 'package:omnifile_mobile/models/document.dart';

class DatabaseService {
  static final DatabaseService _instance = DatabaseService._internal();
  factory DatabaseService() => _instance;
  DatabaseService._internal();

  static Database? _database;

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final documentsDirectory = await getApplicationDocumentsDirectory();
    final path = join(documentsDirectory, 'omnifile_database.db');

    return await openDatabase(
      path,
      version: 1,
      onCreate: _onCreate,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_path TEXT,
        raw_text TEXT,
        processed_text TEXT,
        page_count INTEGER,
        language TEXT,
        confidence REAL,
        status TEXT,
        created_at TEXT,
        updated_at TEXT,
        metadata TEXT
      )
    ''');

    await db.execute('''
      CREATE TABLE ocr_results (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_num INTEGER,
        word_text TEXT,
        raw_text TEXT,
        confidence REAL,
        model_source TEXT,
        created_at TEXT,
        FOREIGN KEY (document_id) REFERENCES documents (id)
      )
    ''');
  }

  // ============ Document Operations ============

  Future<int> insertDocument(Document document) async {
    final db = await database;
    return await db.insert(
      'documents',
      {
        'id': document.id,
        'file_name': document.fileName,
        'file_path': document.filePath,
        'raw_text': document.rawText,
        'processed_text': document.processedText,
        'page_count': document.pageCount,
        'language': document.language,
        'confidence': document.confidence,
        'status': document.status,
        'created_at': document.createdAt.toIso8601String(),
        'updated_at': document.updatedAt?.toIso8601String(),
        'metadata': json.encode(document.metadata),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Document>> getDocuments({
    int limit = 20,
    int offset = 0,
    String status = 'pending_review',
  }) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'documents',
      where: 'status = ?',
      whereArgs: [status],
      limit: limit,
      offset: offset,
      orderBy: 'created_at DESC',
    );

    return maps.map((map) => Document.fromJson(map)).toList();
  }

  Future<Document?> getDocument(String id) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'documents',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );

    if (maps.isNotEmpty) {
      return Document.fromJson(maps.first);
    }
    return null;
  }

  Future<int> updateDocument(Document document) async {
    final db = await database;
    return await db.update(
      'documents',
      {
        'file_name': document.fileName,
        'file_path': document.filePath,
        'raw_text': document.rawText,
        'processed_text': document.processedText,
        'page_count': document.pageCount,
        'language': document.language,
        'confidence': document.confidence,
        'status': document.status,
        'updated_at': document.updatedAt?.toIso8601String(),
        'metadata': json.encode(document.metadata),
      },
      where: 'id = ?',
      whereArgs: [document.id],
    );
  }

  Future<int> deleteDocument(String id) async {
    final db = await database;
    return await db.delete(
      'documents',
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  // ============ OCR Results Operations ============

  Future<int> insertOCRResult(OCRResult result) async {
    final db = await database;
    return await db.insert(
      'ocr_results',
      {
        'id': result.id,
        'document_id': result.documentId,
        'page_num': result.pageNum,
        'word_text': result.wordText,
        'raw_text': result.rawText,
        'confidence': result.confidence,
        'model_source': result.modelSource,
        'created_at': result.createdAt.toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<OCRResult>> getOCRResults(String documentId) async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query(
      'ocr_results',
      where: 'document_id = ?',
      whereArgs: [documentId],
      orderBy: 'page_num ASC',
    );

    return maps.map((map) => OCRResult.fromJson(map)).toList();
  }
}
```

---

### **📄 `lib/screens/home_screen.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:omnifile_mobile/screens/document_list_screen.dart';
import 'package:omnifile_mobile/screens/review_screen.dart';
import 'package:omnifile_mobile/screens/settings_screen.dart';
import 'package:omnifile_mobile/utils/constants.dart';
import 'package:omnifile_mobile/services/api_service.dart';
import 'package:omnifile_mobile/services/database_service.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'dart:io';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiService _apiService = ApiService();
  final DatabaseService _dbService = DatabaseService();
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _apiService.init();
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final XFile? image = await picker.pickImage(source: source);

      if (image != null) {
        final file = File(image.path);
        _processFile(file);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل اختيار الصورة: $e')),
      );
    }
  }

  Future<void> _pickFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg'],
      );

      if (result != null) {
        final file = File(result.files.single.path!);
        _processFile(file);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل اختيار الملف: $e')),
      );
    }
  }

  Future<void> _processFile(File file) async {
    try {
      final document = await _apiService.uploadDocument(
        file: file,
        language: AppConstants.defaultLanguage,
        engines: ['trocr', 'easyocr', 'tesseract'],
      );

      // حفظ في قاعدة البيانات المحلية
      await _dbService.insertDocument(document);

      // التنقل إلى شاشة المراجعة
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => ReviewScreen(documentId: document.id),
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل معالجة الملف: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(AppConstants.appName),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const SettingsScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: [
          _buildHomeContent(),
          const DocumentListScreen(),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() => _currentIndex = index);
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'الرئيسية',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.list),
            label: 'المستندات',
          ),
        ],
      ),
    );
  }

  Widget _buildHomeContent() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.description, size: 100, color: AppConstants.primaryColor),
            const SizedBox(height: 20),
            const Text(
              'مرحبا في OmniFile Mobile',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            const Text(
              'قم برفع صورة أو ملف PDF لبدء مراجعة OCR',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 40),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Expanded(
                  child: _buildFeatureCard(
                    icon: Icons.camera_alt,
                    title: 'التقاط من الكاميرا',
                    onTap: () => _pickImage(ImageSource.camera),
                  ),
                ),
                const SizedBox(width: 20),
                Expanded(
                  child: _buildFeatureCard(
                    icon: Icons.image,
                    title: 'اختيار صورة',
                    onTap: () => _pickImage(ImageSource.gallery),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            _buildFeatureCard(
              icon: Icons.upload_file,
              title: 'رفع ملف PDF',
              onTap: _pickFile,
            ),
            const SizedBox(height: 20),
            _buildFeatureCard(
              icon: Icons.list,
              title: 'عرض المستندات السابقة',
              onTap: () => setState(() => _currentIndex = 1),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              Icon(icon, size: 40, color: AppConstants.primaryColor),
              const SizedBox(height: 10),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

### **📄 `lib/screens/document_list_screen.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:omnifile_mobile/models/document.dart';
import 'package:omnifile_mobile/screens/review_screen.dart';
import 'package:omnifile_mobile/services/api_service.dart';
import 'package:omnifile_mobile/services/database_service.dart';
import 'package:omnifile_mobile/utils/constants.dart';

class DocumentListScreen extends StatefulWidget {
  const DocumentListScreen({super.key});

  @override
  State<DocumentListScreen> createState() => _DocumentListScreenState();
}

class _DocumentListScreenState extends State<DocumentListScreen> {
  final ApiService _apiService = ApiService();
  final DatabaseService _dbService = DatabaseService();
  List<Document> _documents = [];
  bool _isLoading = true;
  String _selectedStatus = 'pending_review';

  @override
  void initState() {
    super.initState();
    _loadDocuments();
  }

  Future<void> _loadDocuments() async {
    setState(() => _isLoading = true);
    try {
      // محاولة تحميل من API أولاً
      try {
        _documents = await _apiService.getDocuments(
          status: _selectedStatus,
        );
      } catch (e) {
        // إذا فشل API، تحميل من قاعدة البيانات المحلية
        _documents = await _dbService.getDocuments(
          status: _selectedStatus,
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل تحميل المستندات: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _refreshDocuments() async {
    await _loadDocuments();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('قائمة المستندات'),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.filter_list),
            onSelected: (value) {
              setState(() {
                _selectedStatus = value;
                _loadDocuments();
              });
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'pending_review',
                child: Text('في انتظار المراجعة'),
              ),
              const PopupMenuItem(
                value: 'reviewed',
                child: Text('مراجع'),
              ),
              const PopupMenuItem(
                value: 'all',
                child: Text('الكل'),
              ),
            ],
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refreshDocuments,
              child: _documents.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(Icons.description, size: 60, color: Colors.grey),
                          const SizedBox(height: 20),
                          const Text(
                            'لا توجد مستندات',
                            style: TextStyle(fontSize: 18),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            _selectedStatus == 'pending_review'
                                ? 'قم برفع ملف جديد لبدء المراجعة'
                                : 'لا توجد مستندات ${_selectedStatus == "reviewed" ? "مراجعة" : ""}',
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: _documents.length,
                      itemBuilder: (context, index) {
                        final doc = _documents[index];
                        return _buildDocumentCard(doc);
                      },
                    ),
            ),
    );
  }

  Widget _buildDocumentCard(Document document) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      child: InkWell(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => ReviewScreen(documentId: document.id),
            ),
          );
        },
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      document.fileName,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Chip(
                    label: Text(
                      AppConstants.languageNames[document.language] ?? document.language,
                      style: const TextStyle(fontSize: 12),
                    ),
                    backgroundColor: Colors.blue.withOpacity(0.1),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  _buildInfoChip(Icons.text_snippet, '${document.pageCount} صفحات'),
                  const SizedBox(width: 8),
                  _buildInfoChip(Icons.verified_user, '${(document.confidence * 100).toStringAsFixed(1)}%'),
                  const SizedBox(width: 8),
                  _buildInfoChip(
                    Icons.schedule,
                    '${document.createdAt.day}/${document.createdAt.month}/${document.createdAt.year}',
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      document.rawText.length > 100
                          ? '${document.rawText.substring(0, 100)}...'
                          : document.rawText,
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Icon(
                    document.status == 'reviewed'
                        ? Icons.check_circle
                        : Icons.hourglass_empty,
                    color: document.status == 'reviewed'
                        ? Colors.green
                        : Colors.orange,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoChip(IconData icon, String label) {
    return Chip(
      avatar: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 12)),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: -4),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }
}
```

---

### **📄 `lib/screens/review_screen.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'package:omnifile_mobile/models/document.dart';
import 'package:omnifile_mobile/services/api_service.dart';
import 'package:omnifile_mobile/services/database_service.dart';
import 'package:omnifile_mobile/widgets/correction_suggestions.dart';
import 'package:omnifile_mobile/widgets/table_widget.dart';
import 'package:omnifile_mobile/widgets/image_widget.dart';
import 'package:omnifile_mobile/utils/constants.dart';
import 'package:omnifile_mobile/utils/format_utils.dart';

class ReviewScreen extends StatefulWidget {
  final String documentId;

  const ReviewScreen({super.key, required this.documentId});

  @override
  State<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends State<ReviewScreen> {
  final ApiService _apiService = ApiService();
  final DatabaseService _dbService = DatabaseService();
  Document? _document;
  bool _isLoading = true;
  bool _isSaving = false;
  final QuillController _quillController = QuillController.basic();
  final ScrollController _scrollController = ScrollController();
  List<String> _suggestions = [];
  bool _showSuggestions = true;

  @override
  void initState() {
    super.initState();
    _loadDocument();
  }

  @override
  void dispose() {
    _quillController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadDocument() async {
    setState(() => _isLoading = true);
    try {
      // محاولة تحميل من API أولاً
      try {
        _document = await _apiService.getDocument(widget.documentId);
      } catch (e) {
        // إذا فشل API، تحميل من قاعدة البيانات المحلية
        _document = await _dbService.getDocument(widget.documentId);
      }

      if (_document != null) {
        // تحميل النص في محرر Quill
        _quillController.document = Document.fromJson({
          'ops': [
            {'insert': _document!.rawText},
          ],
        });

        // تحميل الاقتراحات
        if (_document!.language == AppConstants.defaultLanguage) {
          _loadSuggestions(_document!.rawText);
        }
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل تحميل المستند: $e')),
      );
      Navigator.pop(context);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _loadSuggestions(String text) async {
    try {
      _suggestions = await _apiService.getSuggestions(
        text: text,
        language: _document?.language ?? AppConstants.defaultLanguage,
      );
    } catch (e) {
      // في حالة الفشل، استخدام اقتراحات افتراضية
      _suggestions = FormatUtils.getDefaultSuggestions(
        _document?.language ?? AppConstants.defaultLanguage,
      );
    }
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _saveCorrections() async {
    if (_document == null) return;

    setState(() => _isSaving = true);
    try {
      final correctedText = _quillController.document.toPlainText();

      // حفظ في API
      try {
        await _apiService.saveCorrections(
          docId: _document!.id,
          correctedText: correctedText,
        );
      } catch (e) {
        // إذا فشل API، حفظ في قاعدة البيانات المحلية
        final updatedDoc = _document!.copyWith(
          processedText: correctedText,
          status: 'reviewed',
          updatedAt: DateTime.now(),
        );
        await _dbService.updateDocument(updatedDoc);
      }

      // تحديث الحالة المحلية
      setState(() {
        _document = _document!.copyWith(
          processedText: correctedText,
          status: 'reviewed',
          updatedAt: DateTime.now(),
        );
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم حفظ التعديلات بنجاح!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل حفظ التعديلات: $e')),
      );
    } finally {
      setState(() => _isSaving = false);
    }
  }

  Future<void> _markAsReviewed() async {
    if (_document == null) return;

    setState(() => _isSaving = true);
    try {
      // تحديد كمراجع في API
      try {
        await _apiService.markAsReviewed(_document!.id);
      } catch (e) {
        // إذا فشل API، تحديث قاعدة البيانات المحلية
        final updatedDoc = _document!.copyWith(
          status: 'reviewed',
          updatedAt: DateTime.now(),
        );
        await _dbService.updateDocument(updatedDoc);
      }

      // تحديث الحالة المحلية
      setState(() {
        _document = _document!.copyWith(
          status: 'reviewed',
          updatedAt: DateTime.now(),
        );
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تم تحديد المستند كمراجع!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('فشل تحديد المستند كمراجع: $e')),
      );
    } finally {
      setState(() => _isSaving = false);
    }
  }

  void _applySuggestion(String suggestion) {
    final selection = _quillController.selection;
    if (selection.isValid) {
      _quillController.replaceText(
        selection.start,
        selection.end,
        suggestion,
        null,
      );
    } else {
      // إذا لم يتم تحديد نص، إضافة الاقتراح في نهاية النص
      _quillController.replaceText(
        _quillController.selection.end,
        _quillController.selection.end,
        ' $suggestion',
        null,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_document?.fileName ?? 'مراجعة المستند'),
        actions: [
          if (_document?.status != 'reviewed')
            IconButton(
              icon: const Icon(Icons.check),
              onPressed: _isSaving ? null : _markAsReviewed,
              tooltip: 'تحديد كمراجع',
            ),
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _isSaving ? null : _saveCorrections,
            tooltip: 'حفظ التعديلات',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // معلومات المستند
                _buildDocumentInfo(),

                // محرر النص
                Expanded(
                  child: _buildTextEditor(),
                ),

                // اقتراحات التصحيح
                if (_showSuggestions && _suggestions.isNotEmpty)
                  CorrectionSuggestions(
                    suggestions: _suggestions,
                    onSuggestionSelected: _applySuggestion,
                  ),
              ],
            ),
      bottomNavigationBar: _buildBottomAppBar(),
    );
  }

  Widget _buildDocumentInfo() {
    if (_document == null) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.all(10),
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildInfoItem(
              '📄 الملف',
              _document!.fileName,
            ),
            _buildInfoItem(
              '📊 الثقة',
              '${(_document!.confidence * 100).toStringAsFixed(1)}%',
            ),
            _buildInfoItem(
              '📝 الصفحات',
              _document!.pageCount.toString(),
            ),
            _buildInfoItem(
              '🌐 اللغة',
              AppConstants.languageNames[_document!.language] ?? _document!.language,
            ),
          ],
        ),
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

  Widget _buildTextEditor() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // شريط أدوات المحرر
        QuillToolbar.basic(
          controller: _quillController,
          multiRowsDisplay: false,
          showAlignmentButtons: true,
          showDirection: true,
          toolbarOptions: const QuillToolbarOptions(
            defaultToolbarButtonSize: 24,
          ),
        ),

        // منطقة الكتابة
        Expanded(
          child: Container(
            margin: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Scrollbar(
              controller: _scrollController,
              child: SingleChildScrollView(
                controller: _scrollController,
                padding: const EdgeInsets.all(10),
                child: QuillEditor(
                  controller: _quillController,
                  readOnly: false,
                  autoFocus: true,
                  expands: false,
                  padding: EdgeInsets.zero,
                  embedBuilders: [
                    // دعم الجداول
                    TableEmbedBuilder(),
                    // دعم الصور
                    ImageEmbedBuilder(),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBottomAppBar() {
    return Container(
      padding: const EdgeInsets.all(10),
      color: Theme.of(context).cardColor,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          IconButton(
            icon: const Icon(Icons.undo),
            onPressed: _quillController.undo,
            tooltip: 'تراجع',
          ),
          IconButton(
            icon: const Icon(Icons.redo),
            onPressed: _quillController.redo,
            tooltip: 'إعادة',
          ),
          IconButton(
            icon: Icon(
              _showSuggestions ? Icons.lightbulb : Icons.lightbulb_outline,
            ),
            onPressed: () {
              setState(() => _showSuggestions = !_showSuggestions);
            },
            tooltip: 'إظهار/إخفاء الاقتراحات',
          ),
          IconButton(
            icon: const Icon(Icons.format_size),
            onPressed: () {
              // تغيير حجم الخط
              showDialog(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('حجم الخط'),
                  content: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final size in [12, 14, 16, 18, 20, 22])
                        ListTile(
                          title: Text('حجم $size'),
                          onTap: () {
                            Navigator.pop(context);
                            // تطبيق حجم الخط (سيتم إضافة لاحقًا)
                          },
                        ),
                    ],
                  ),
                ),
              );
            },
            tooltip: 'حجم الخط',
          ),
        ],
      ),
    );
  }
}

// ============ Embed Builders ============

class TableEmbedBuilder extends EmbedBuilder {
  @override
  String get key => 'table';

  @override
  Widget build(
    BuildContext context,
    QuillEmbed embed,
    bool readOnly,
    {required EmbedBuilderOptions options},
  ) {
    final tableData = embed.data as Map<String, dynamic>;
    return TableWidget(
      rows: (tableData['rows'] as List<dynamic>).map((row) {
        return (row as List<dynamic>).map((cell) => cell.toString()).toList();
      }).toList(),
      isRtl: true,
    );
  }
}

class ImageEmbedBuilder extends EmbedBuilder {
  @override
  String get key => 'image';

  @override
  Widget build(
    BuildContext context,
    QuillEmbed embed,
    bool readOnly,
    {required EmbedBuilderOptions options},
  ) {
    final imageData = embed.data as Map<String, dynamic>;
    final imageUrl = imageData['url'] as String?;
    final imageBase64 = imageData['base64'] as String?;

    if (imageUrl != null) {
      return ImageWidget(imageUrl: imageUrl);
    } else if (imageBase64 != null) {
      return ImageWidget(imageBase64: imageBase64);
    } else {
      return const Icon(Icons.image, size: 100);
    }
  }
}
```

---

### **📄 `lib/widgets/correction_suggestions.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:omnifile_mobile/utils/constants.dart';

class CorrectionSuggestions extends StatelessWidget {
  final List<String> suggestions;
  final Function(String) onSuggestionSelected;

  const CorrectionSuggestions({
    super.key,
    required this.suggestions,
    required this.onSuggestionSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (suggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.all(10),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'اقتراحات التصحيح:',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8.0,
              runSpacing: 8.0,
              children: suggestions.map((suggestion) {
                return FilterChip(
                  label: Text(suggestion),
                  onSelected: (selected) {
                    if (selected) {
                      onSuggestionSelected(suggestion);
                    }
                  },
                  backgroundColor: Colors.blue.withOpacity(0.1),
                  selectedColor: AppConstants.primaryColor,
                  checkmarkColor: Colors.white,
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

### **📄 `lib/widgets/table_widget.dart`**
```dart
import 'package:flutter/material.dart';

class TableWidget extends StatelessWidget {
  final List<List<String>> rows;
  final bool isRtl;
  final TextStyle? headerStyle;
  final TextStyle? cellStyle;

  const TableWidget({
    super.key,
    required this.rows,
    this.isRtl = false,
    this.headerStyle,
    this.cellStyle,
  });

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Table(
        border: TableBorder.all(color: Colors.grey.shade300),
        columnWidths: const {
          for (int i = 0; i < 10; i++) FlexColumnWidth(),
        },
        children: [
          // رأس الجدول
          TableRow(
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
            ),
            children: rows[0].map((header) {
              return TableCell(
                child: Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Text(
                    header,
                    style: headerStyle ?? const TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: isRtl ? TextAlign.right : TextAlign.left,
                  ),
                ),
              );
            }).toList(),
          ),

          // صفوف البيانات
          for (int i = 1; i < rows.length; i++)
            TableRow(
              children: rows[i].map((cell) {
                return TableCell(
                  child: Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: Text(
                      cell,
                      style: cellStyle,
                      textAlign: isRtl ? TextAlign.right : TextAlign.left,
                    ),
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
}
```

---

### **📄 `lib/widgets/image_widget.dart`**
```dart
import 'package:flutter/material.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:photo_view/photo_view.dart';

class ImageWidget extends StatelessWidget {
  final String? imageUrl;
  final String? imageBase64;
  final String? caption;
  final double? width;
  final double? height;
  final BoxFit? fit;

  const ImageWidget({
    super.key,
    this.imageUrl,
    this.imageBase64,
    this.caption,
    this.width,
    this.height,
    this.fit,
  }) : assert(imageUrl != null || imageBase64 != null, 'يجب تحديد imageUrl أو imageBase64');

  @override
  Widget build(BuildContext context) {
    Widget image;

    if (imageUrl != null) {
      image = CachedNetworkImage(
        imageUrl: imageUrl!,
        placeholder: (context, url) => const Center(child: CircularProgressIndicator()),
        errorWidget: (context, url, error) => const Icon(Icons.error),
        fit: fit,
      );
    } else if (imageBase64 != null) {
      final bytes = base64.decode(imageBase64!.split(',').last);
      image = Image.memory(
        Uint8List.fromList(bytes),
        fit: fit,
      );
    } else {
      image = const Icon(Icons.image, size: 100);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        GestureDetector(
          onTap: () {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => PhotoView(
                  imageProvider: imageUrl != null
                      ? CachedNetworkImageProvider(imageUrl!)
                      : MemoryImage(base64.decode(imageBase64!.split(',').last)),
                ),
              ),
            );
          },
          child: Container(
            width: width,
            height: height,
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade300),
              borderRadius: BorderRadius.circular(8),
            ),
            child: image,
          ),
        ),
        if (caption != null && caption!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 8.0),
            child: Text(
              caption!,
              style: const TextStyle(
                fontStyle: FontStyle.italic,
                color: Colors.grey,
              ),
              textAlign: TextAlign.center,
            ),
          ),
      ],
    );
  }
}
```

---

### **📄 `lib/utils/format_utils.dart`**
```dart
import 'package:omnifile_mobile/utils/constants.dart';

class FormatUtils {
  // الحصول على اقتراحات افتراضية بناءً على اللغة
  static List<String> getDefaultSuggestions(String language) {
    switch (language) {
      case 'ar':
        return [
          'تصحيح إملائي',
          'تصحيح نحوي',
          'تحسين الأسلوب',
          'إزالة التكرار',
          'تحسين الوضوح',
        ];
      case 'en':
        return [
          'Fix spelling',
          'Fix grammar',
          'Improve style',
          'Remove repetition',
          'Improve clarity',
        ];
      case 'de':
        return [
          'Rechtschreibung korrigieren',
          'Grammatik korrigieren',
          'Stil verbessern',
          'Wiederholungen entfernen',
          'Klarheit verbessern',
        ];
      default:
        return [];
    }
  }

  // تحليل النص لاكتشاف الجداول
  static List<List<String>> parseTables(String text) {
    final List<List<String>> tables = [];
    final lines = text.split('\n');

    List<List<String>>? currentTable;
    bool inTable = false;

    for (final line in lines) {
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        if (!inTable) {
          // بداية جدول جديد
          currentTable = [];
          inTable = true;
        }

        // تحليل السطر
        final cells = line
            .split('|')
            .where((cell) => cell.trim().isNotEmpty)
            .map((cell) => cell.trim())
            .toList();

        currentTable.add(cells);
      } else {
        if (inTable) {
          // نهاية الجدول
          if (currentTable != null && currentTable.length > 1) {
            tables.add(currentTable);
          }
          currentTable = null;
          inTable = false;
        }
      }
    }

    // إضافة الجدول الأخير إذا كان هناك جدول غير مكتمل
    if (currentTable != null && currentTable.length > 1) {
      tables.add(currentTable);
    }

    return tables;
  }

  // تحليل الصور من النص
  static List<Map<String, String>> parseImages(String text) {
    final List<Map<String, String>> images = [];
    final imageRegex = RegExp(r'!\[([^\]]*)\]\(([^)]+)\)');

    for (final match in imageRegex.allMatches(text)) {
      images.add({
        'alt': match.group(1) ?? '',
        'url': match.group(2) ?? '',
      });
    }

    return images;
  }

  // تحليل كتل الكود من النص
  static List<Map<String, String>> parseCodeBlocks(String text) {
    final List<Map<String, String>> codeBlocks = [];
    final codeRegex = RegExp(r'```(\w*)\n([\s\S+?])```');

    for (final match in codeRegex.allMatches(text)) {
      codeBlocks.add({
        'language': match.group(1) ?? '',
        'code': match.group(2)?.trim() ?? '',
      });
    }

    return codeBlocks;
  }

  // تحويل نص Markdown إلى HTML
  static String markdownToHtml(String text, {bool isRtl = false}) {
    String html = text;

    // العناوين
    html = html.replaceAllMapped(
      RegExp(r'^#\s+(.*?)$', multiLine: true),
      (match) => '<h1>${match.group(1)}</h1>',
    );
    html = html.replaceAllMapped(
      RegExp(r'^##\s+(.*?)$', multiLine: true),
      (match) => '<h2>${match.group(1)}</h2>',
    );
    html = html.replaceAllMapped(
      RegExp(r'^###\s+(.*?)$', multiLine: true),
      (match) => '<h3>${match.group(1)}</h3>',
    );

    // غليظ
    html = html.replaceAll(RegExp(r'\*\*(.*?)\*\*'), r'<strong>$1</strong>');

    // مائل
    html = html.replaceAll(RegExp(r'\*(.*?)\*'), r'<em>$1</em>');

    // مسطّر
    html = html.replaceAll(RegExp(r'~~(.*?)~~'), r'<s>$1</s>');

    // روابط
    html = html.replaceAllMapped(
      RegExp(r'\[(.*?)\]\((.*?)\)'),
      (match) => '<a href="${match.group(2)}">${match.group(1)}</a>',
    );

    // صور
    html = html.replaceAllMapped(
      RegExp(r'!\[(.*?)\]\((.*?)\)'),
      (match) => '<img src="${match.group(2)}" alt="${match.group(1)}" style="max-width: 100%;">',
    );

    // كتل الكود
    html = html.replaceAllMapped(
      RegExp(r'```(\w*)\n([\s\S+?])```'),
      (match) {
        final language = match.group(1) ?? '';
        final code = match.group(2)?.trim() ?? '';
        return '<pre><code class="language-$language">$code</code></pre>';
      },
    );

    // الجداول
    html = html.replaceAllMapped(
      RegExp(r'(\|[^\n]+\|\s*\n)(\|[-+:=\s\|]+\|\s*\n)([\s\S+?](?=\n\n|\n\Z|\Z))'),
      (match) {
        final header = match.group(1)!.trim();
        final separator = match.group(2)!.trim();
        final rows = match.group(3)!.trim();

        final headerCells = header
            .split('|')
            .where((cell) => cell.trim().isNotEmpty)
            .map((cell) => cell.trim())
            .toList();

        final dataRows = rows
            .split('\n')
            .where((row) => row.trim().isNotEmpty)
            .map((row) {
          return row
              .split('|')
              .where((cell) => cell.trim().isNotEmpty)
              .map((cell) => cell.trim())
              .toList();
        }).toList();

        String tableHtml = '<table>\n  <thead>\n    <tr>';
        for (final cell in headerCells) {
          tableHtml += '\n      <th style="text-align: ${isRtl ? 'right' : 'left'}">$cell</th>';
        }
        tableHtml += '\n    </tr>\n  </thead>\n  <tbody>';

        for (final row in dataRows) {
          tableHtml += '\n    <tr>';
          for (final cell in row) {
            tableHtml += '\n      <td style="text-align: ${isRtl ? 'right' : 'left'}">$cell</td>';
          }
          tableHtml += '\n    </tr>';
        }

        tableHtml += '\n  </tbody>\n</table>';
        return tableHtml;
      },
    );

    // الأسطر الجديدة
    html = html.replaceAll('\n', '<br>');

    // اتجاه النص
    if (isRtl) {
      html = '<div style="direction: rtl; text-align: right;">$html</div>';
    }

    return html;
  }
}
```

---

### **📄 `lib/screens/settings_screen.dart`**
```dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:omnifile_mobile/utils/constants.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late SharedPreferences _prefs;
  bool _darkMode = false;
  String _language = AppConstants.defaultLanguage;
  bool _enableAutoCorrect = true;
  bool _enableSuggestions = true;
  bool _showTables = true;
  bool _showImages = true;
  String _defaultExportFormat = 'pdf';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    _prefs = await SharedPreferences.getInstance();
    setState(() {
      _darkMode = _prefs.getBool('dark_mode') ?? false;
      _language = _prefs.getString('language') ?? AppConstants.defaultLanguage;
      _enableAutoCorrect = _prefs.getBool('enable_auto_correct') ?? true;
      _enableSuggestions = _prefs.getBool('enable_suggestions') ?? true;
      _showTables = _prefs.getBool('show_tables') ?? true;
      _showImages = _prefs.getBool('show_images') ?? true;
      _defaultExportFormat = _prefs.getString('default_export_format') ?? 'pdf';
    });
  }

  Future<void> _saveSettings() async {
    await _prefs.setBool('dark_mode', _darkMode);
    await _prefs.setString('language', _language);
    await _prefs.setBool('enable_auto_correct', _enableAutoCorrect);
    await _prefs.setBool('enable_suggestions', _enableSuggestions);
    await _prefs.setBool('show_tables', _showTables);
    await _prefs.setBool('show_images', _showImages);
    await _prefs.setString('default_export_format', _defaultExportFormat);

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('تم حفظ الإعدادات')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('الإعدادات'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveSettings,
            tooltip: 'حفظ الإعدادات',
          ),
        ],
      ),
      body: ListView(
        children: [
          // الوضع الداكن
          SwitchListTile(
            title: const Text('الوضع الداكن'),
            value: _darkMode,
            onChanged: (value) {
              setState(() => _darkMode = value);
            },
            secondary: const Icon(Icons.dark_mode),
          ),

          const Divider(),

          // اللغة
          ListTile(
            title: const Text('اللغة الافتراضية'),
            trailing: DropdownButton<String>(
              value: _language,
              onChanged: (value) {
                setState(() => _language = value!);
              },
              items: AppConstants.supportedLanguages.map((lang) {
                return DropdownMenuItem(
                  value: lang,
                  child: Text(AppConstants.languageNames[lang] ?? lang),
                );
              }).toList(),
            ),
            leading: const Icon(Icons.language),
          ),

          const Divider(),

          // إعدادات التصحيح
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              'إعدادات التصحيح',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),

          SwitchListTile(
            title: const Text('التصحيح التلقائي'),
            value: _enableAutoCorrect,
            onChanged: (value) {
              setState(() => _enableAutoCorrect = value);
            },
            secondary: const Icon(Icons.auto_fix_high),
          ),

          SwitchListTile(
            title: const Text('عرض اقتراحات التصحيح'),
            value: _enableSuggestions,
            onChanged: (value) {
              setState(() => _enableSuggestions = value);
            },
            secondary: const Icon(Icons.lightbulb),
          ),

          const Divider(),

          // إعدادات العرض
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              'إعدادات العرض',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),

          SwitchListTile(
            title: const Text('عرض الجداول'),
            value: _showTables,
            onChanged: (value) {
              setState(() => _showTables = value);
            },
            secondary: const Icon(Icons.table_chart),
          ),

          SwitchListTile(
            title: const Text('عرض الصور'),
            value: _showImages,
            onChanged: (value) {
              setState(() => _showImages = value);
            },
            secondary: const Icon(Icons.image),
          ),

          const Divider(),

          // إعدادات التصدير
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              'إعدادات التصدير',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),

          ListTile(
            title: const Text('الصيغة الافتراضية للتصدير'),
            trailing: DropdownButton<String>(
              value: _defaultExportFormat,
              onChanged: (value) {
                setState(() => _defaultExportFormat = value!);
              },
              items: AppConstants.exportFormats.map((format) {
                return DropdownMenuItem(
                  value: format,
                  child: Text(AppConstants.exportFormatNames[format] ?? format),
                );
              }).toList(),
            ),
            leading: const Icon(Icons.save),
          ),

          const Divider(),

          // معلومات التطبيق
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              'معلومات التطبيق',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),

          const ListTile(
            title: Text('الإصدار'),
            trailing: Text(AppConstants.appVersion),
            leading: Icon(Icons.info),
          ),

          const ListTile(
            title: Text('المطور'),
            trailing: Text('Dr. Abdulmalek'),
            leading: Icon(Icons.person),
          ),

          ListTile(
            title: const Text('الترخيص'),
            trailing: const Text('MIT'),
            leading: const Icon(Icons.description),
            onTap: () {
              // عرض ترخيص MIT
              showLicensePage(
                context: context,
                applicationName: AppConstants.appName,
                applicationVersion: AppConstants.appVersion,
                applicationIcon: const Icon(Icons.description),
              );
            },
          ),
        ],
      ),
    );
  }
}
```

---

### **📄 `android/app/build.gradle`**
```gradle
android {
    compileSdk 34

    defaultConfig {
        applicationId "com.omnifile.mobile"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0.0"

        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }

    compileOptions {
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }

    kotlinOptions {
        jvmTarget = '1.8'
    }

    buildFeatures {
        viewBinding true
    }
}

dependencies {
    implementation 'androidx.core:core-ktx:1.12.0'
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'

    // Flutter dependencies
    implementation 'io.flutter:flutter_embedding_debug:1.0.0'
    implementation 'io.flutter:flutter_embedding_release:1.0.0'

    testImplementation 'junit:junit:4.13.2'
    androidTestImplementation 'androidx.test.ext:junit:1.1.5'
    androidTestImplementation 'androidx.test.espresso:espresso-core:3.5.1'
}
```

---

### **📄 `android/local.properties`**
```
sdk.dir=/Users/yourname/Library/Android/sdk
```

---
---
---

## 📄 **4. ملف الاقتراحات (`SUGGESTIONS.md`)**
