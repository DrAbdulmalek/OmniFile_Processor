"""
الواجهة الرسومية المتكاملة لـ OmniFile Processor
=====================================================
واجهة Tkinter احترافية تجمع جميع وحدات المشروع في مكان واحد.

التبويبات:
1. المعالجة (Processing) — استخراج النصوص من الملفات
2. التدقيق والاعتماد (Review) — مراجعة النصوص واعتمادها للتدريب
3. البحث الشامل (Search) — البحث في الأرشيف
4. الإحصائيات (Statistics) — عرض إحصائيات المشروع
5. الإعدادات (Settings) — تهيئة المعالجة

المتطلبات:
    python -c "import tkinter"  # Tkinter مدمج مع بايثون
    pip install paddleocr paddlepaddle  # لمحرك OCR (اختياري)

الاستخدام:
    python gui_app.py
"""

import os
import sys
import json
import threading
import queue
import tkinter as tk
from tkinter import (
    filedialog, messagebox, scrolledtext, ttk,
    Frame, Label, Button, Entry, Text, StringVar,
    BooleanVar, DoubleVar, PanedWindow, Menu
)
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

# إضافة مسار المشروع
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class OmniFileGUI:
    """
    الواجهة الرسومية الرئيسية لـ OmniFile Processor.

    تجمع بين:
    - نظام بصمة الملفات (FileFingerprintManager)
    - مصنف المحتوى الطبي (MedicalClassifier)
    - محرك OCR (EasyOCR / PaddleOCR)
    - التدقيق اللغوي (LanguageCorrector)
    - مولد بيانات التدريب (DatasetGenerator)
    - محرك البحث الشامل (SearchEngine)
    """

    # الألوان (نظام ليلي مريح)
    COLORS = {
        "bg_dark": "#1e1e2e",
        "bg_medium": "#2d2d44",
        "bg_light": "#3d3d5c",
        "bg_input": "#454566",
        "fg_primary": "#e0e0e0",
        "fg_secondary": "#a0a0b8",
        "accent_blue": "#5b8def",
        "accent_green": "#4caf50",
        "accent_orange": "#ff9800",
        "accent_red": "#f44336",
        "accent_purple": "#9c27b0",
        "border": "#555577",
        "success": "#81c784",
        "warning": "#ffb74d",
        "error": "#e57373",
    }

    def __init__(self, root: tk.Tk):
        """
        تهيئة الواجهة الرسومية.

        Args:
            root: نافذة Tkinter الرئيسية
        """
        self.root = root
        self.root.title("OmniFile AI Processor v4.2.0 — معالج الملفات الشامل")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=self.COLORS["bg_dark"])

        # متغيرات الحالة
        self.selected_folder = StringVar(value="")
        self.output_folder = StringVar(value="")
        self.search_query = StringVar(value="")
        self.status_var = StringVar(value="جاهز")
        self.progress_var = DoubleVar(value=0)
        self.confidence_threshold = DoubleVar(value=0.70)
        self.auto_watch_var = BooleanVar(value=False)

        # قائمة انتظار الرسائل من الخيوط
        self._msg_queue: queue.Queue = queue.Queue()

        # المكونات الداخلية (تُحمّل كسول)
        self._fingerprint_mgr = None
        self._classifier = None
        self._corrector = None
        self._dataset_gen = None
        self._search_engine = None
        self._ocr_engine = None
        self._watchdog = None

        # بناء الواجهة
        self._setup_styles()
        self._create_menu()
        self._create_header()
        self._create_notebook()
        self._create_status_bar()
        self._check_initialization()

        # بدء مراقبة الرسائل
        self._process_messages()

    # ==================================================================
    # إعداد الأنماط والألوان
    # ==================================================================
    def _setup_styles(self):
        """إعداد أنماط ttk."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background=self.COLORS["bg_dark"])
        style.configure("Medium.TFrame", background=self.COLORS["bg_medium"])
        style.configure("Dark.TNotebook", background=self.COLORS["bg_dark"])
        style.configure("Dark.TNotebook.Tab",
                         background=self.COLORS["bg_medium"],
                         foreground=self.COLORS["fg_primary"],
                         padding=[12, 6])
        style.map("Dark.TNotebook.Tab",
                   background=[("selected", self.COLORS["bg_light"])],
                   foreground=[("selected", self.COLORS["accent_blue"])])

        style.configure("Dark.TLabel",
                         background=self.COLORS["bg_dark"],
                         foreground=self.COLORS["fg_primary"])
        style.configure("Header.TLabel",
                         background=self.COLORS["bg_medium"],
                         foreground=self.COLORS["accent_blue"],
                         font=("Arial", 14, "bold"))
        style.configure("Status.TLabel",
                         background=self.COLORS["bg_medium"],
                         foreground=self.COLORS["fg_secondary"])

        style.configure("Action.TButton",
                         background=self.COLORS["accent_blue"],
                         foreground="white",
                         font=("Arial", 10, "bold"),
                         padding=[16, 8])
        style.map("Action.TButton",
                   background=[("active", "#4a7de0")])

        style.configure("Success.TButton",
                         background=self.COLORS["accent_green"],
                         foreground="white",
                         font=("Arial", 10, "bold"),
                         padding=[16, 8])

        style.configure("Warning.TButton",
                         background=self.COLORS["accent_orange"],
                         foreground="white",
                         font=("Arial", 10, "bold"),
                         padding=[16, 8])

        style.configure("Dark.TProgressbar",
                         background=self.COLORS["accent_blue"],
                         troughcolor=self.COLORS["bg_light"])

        style.configure("Dark.TCheckbutton",
                         background=self.COLORS["bg_dark"],
                         foreground=self.COLORS["fg_primary"])

    def _create_menu(self):
        """إنشاء شريط القوائم."""
        menubar = Menu(self.root, bg=self.COLORS["bg_medium"],
                        fg=self.COLORS["fg_primary"])

        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="اختيار مجلد الإدخال", command=self._select_input_folder)
        file_menu.add_command(label="اختيار مجلد المخرجات", command=self._select_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="خروج", command=self.root.quit)
        menubar.add_cascade(label="ملف", menu=file_menu)

        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(label="كشف الملفات المكررة", command=self._find_duplicates)
        tools_menu.add_command(label="تصدير الإحصائيات", command=self._export_stats)
        tools_menu.add_command(label="تنظيف السجلات القديمة", command=self._cleanup_records)
        menubar.add_cascade(label="أدوات", menu=tools_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="عن البرنامج", command=self._show_about)
        menubar.add_cascade(label="مساعدة", menu=help_menu)

        self.root.config(menu=menubar)

    def _create_header(self):
        """إنشاء شريط الرأس."""
        header = Frame(self.root, bg=self.COLORS["bg_medium"], height=50)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)

        # العنوان
        title_label = Label(
            header, text="OmniFile AI Processor v4.2.0",
            font=("Arial", 16, "bold"),
            bg=self.COLORS["bg_medium"],
            fg=self.COLORS["accent_blue"],
        )
        title_label.pack(side=tk.LEFT, padx=15, pady=10)

        # حالة المحركات
        self._engine_status = Label(
            header, text="جاري التحميل...",
            font=("Arial", 9),
            bg=self.COLORS["bg_medium"],
            fg=self.COLORS["fg_secondary"],
        )
        self._engine_status.pack(side=tk.RIGHT, padx=15, pady=10)

    def _create_notebook(self):
        """إنشاء دفتر التبويبات الرئيسي."""
        self.notebook = ttk.Notebook(self.root, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # تبويب المعالجة
        self._create_processing_tab()

        # تبويب التدقيق والاعتماد
        self._create_review_tab()

        # تبويب البحث
        self._create_search_tab()

        # تبويب الإحصائيات
        self._create_stats_tab()

    def _create_status_bar(self):
        """إنشاء شريط الحالة."""
        status_bar = Frame(self.root, bg=self.COLORS["bg_medium"], height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
        status_bar.pack_propagate(False)

        self.status_label = Label(
            status_bar, textvariable=self.status_var,
            font=("Arial", 9),
            bg=self.COLORS["bg_medium"],
            fg=self.COLORS["fg_secondary"],
            anchor=tk.W,
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

        # شريط التقدم
        self.progress_bar = ttk.Progressbar(
            status_bar, variable=self.progress_var,
            maximum=100, style="Dark.TProgressbar",
        )
        self.progress_bar.place(relx=0.8, rely=0.5, relwidth=0.18, anchor=tk.CENTER)

    # ==================================================================
    # تبويب المعالجة
    # ==================================================================
    def _create_processing_tab(self):
        """إنشاء تبويب المعالجة."""
        tab = Frame(self.notebook, bg=self.COLORS["bg_dark"])
        self.notebook.add(tab, text="  المعالجة  ")

        # الجزء العلوي — إعدادات
        top_frame = Frame(tab, bg=self.COLORS["bg_dark"])
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        # اختيار المجلد
        folder_frame = Frame(top_frame, bg=self.COLORS["bg_dark"])
        folder_frame.pack(fill=tk.X, pady=5)

        Label(folder_frame, text="مجلد الإدخال:",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_primary"],
              font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))

        self.folder_entry = Entry(
            folder_frame, textvariable=self.selected_folder,
            bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            insertbackground="white", font=("Arial", 10),
            width=50,
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        Button(
            folder_frame, text="استعراض", command=self._select_input_folder,
            bg=self.COLORS["bg_light"], fg=self.COLORS["fg_primary"],
            relief=tk.FLAT, padx=15
        ).pack(side=tk.LEFT, padx=5)

        # أزرار التحكم
        btn_frame = Frame(top_frame, bg=self.COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=10)

        self._start_btn = Button(
            btn_frame, text="بدء المعالجة",
            command=self._start_processing,
            bg=self.COLORS["accent_blue"], fg="white",
            font=("Arial", 11, "bold"), relief=tk.FLAT,
            padx=20, pady=8, cursor="hand2",
        )
        self._start_btn.pack(side=tk.LEFT, padx=5)

        self._stop_btn = Button(
            btn_frame, text="إيقاف",
            command=self._stop_processing,
            bg=self.COLORS["accent_red"], fg="white",
            font=("Arial", 11, "bold"), relief=tk.FLAT,
            padx=20, pady=8, cursor="hand2",
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=5)

        # مراقبة تلقائية
        chk = tk.Checkbutton(
            btn_frame, text="مراقبة تلقائية (Watchdog)",
            variable=self.auto_watch_var,
            command=self._toggle_watchdog,
            bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_primary"],
            selectcolor=self.COLORS["bg_light"],
            activebackground=self.COLORS["bg_dark"],
            activeforeground=self.COLORS["fg_primary"],
            font=("Arial", 10),
        )
        chk.pack(side=tk.LEFT, padx=20)

        # منطقة السجلات
        log_label = Label(tab, text="سجل العمليات:",
                          bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
                          font=("Arial", 10, "bold"))
        log_label.pack(anchor=tk.W, padx=10)

        self.log_area = scrolledtext.ScrolledText(
            tab, bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            font=("Courier New", 9), wrap=tk.WORD,
            insertbackground="white", height=20,
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # تكوين ألوان النص
        self.log_area.tag_configure("success", foreground=self.COLORS["success"])
        self.log_area.tag_configure("warning", foreground=self.COLORS["warning"])
        self.log_area.tag_configure("error", foreground=self.COLORS["error"])
        self.log_area.tag_configure("info", foreground=self.COLORS["accent_blue"])
        self.log_area.tag_configure("header", foreground=self.COLORS["accent_purple"],
                                    font=("Courier New", 10, "bold"))

    # ==================================================================
    # تبويب التدقيق والاعتماد
    # ==================================================================
    def _create_review_tab(self):
        """إنشاء تبويب التدقيق والاعتماد."""
        tab = Frame(self.notebook, bg=self.COLORS["bg_dark"])
        self.notebook.add(tab, text="  التدقيق والاعتماد  ")

        # منطقة النص للمراجعة
        review_frame = Frame(tab, bg=self.COLORS["bg_dark"])
        review_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # النص الأصلي
        Label(review_frame, text="النص الأصلي (OCR):",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
              font=("Arial", 10, "bold")).pack(anchor=tk.W)

        self.original_text = scrolledtext.ScrolledText(
            review_frame, bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            font=("Arial", 11), wrap=tk.WORD, height=8,
            insertbackground="white",
        )
        self.original_text.pack(fill=tk.X, pady=(5, 10))

        # أزرار التدقيق
        review_btns = Frame(review_frame, bg=self.COLORS["bg_dark"])
        review_btns.pack(fill=tk.X, pady=5)

        Button(
            review_btns, text="تدقيق لغوي",
            command=self._run_spell_check,
            bg=self.COLORS["accent_blue"], fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            padx=15, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        Button(
            review_btns, text="تصنيف المحتوى",
            command=self._run_classification,
            bg=self.COLORS["accent_purple"], fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            padx=15, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        # النتيجة
        Label(review_frame, text="النص المصحح:",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
              font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))

        self.corrected_text = scrolledtext.ScrolledText(
            review_frame, bg=self.COLORS["bg_input"], fg=self.COLORS["success"],
            font=("Arial", 11), wrap=tk.WORD, height=8,
            insertbackground="white",
        )
        self.corrected_text.pack(fill=tk.X, pady=(5, 10))

        # زر الاعتماد للتدريب
        train_frame = Frame(review_frame, bg=self.COLORS["bg_dark"])
        train_frame.pack(fill=tk.X, pady=10)

        self._approve_btn = Button(
            train_frame, text="اعتماد للتدريب (Fine-tuning)",
            command=self._approve_for_training,
            bg=self.COLORS["accent_orange"], fg="white",
            font=("Arial", 11, "bold"), relief=tk.FLAT,
            padx=20, pady=8, cursor="hand2",
        )
        self._approve_btn.pack(side=tk.LEFT, padx=5)

        self._training_count_label = Label(
            train_frame, text="بيانات التدريب: 0",
            bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
            font=("Arial", 10),
        )
        self._training_count_label.pack(side=tk.LEFT, padx=15)

    # ==================================================================
    # تبويب البحث الشامل
    # ==================================================================
    def _create_search_tab(self):
        """إنشاء تبويب البحث الشامل."""
        tab = Frame(self.notebook, bg=self.COLORS["bg_dark"])
        self.notebook.add(tab, text="  البحث الشامل  ")

        # شريط البحث
        search_frame = Frame(tab, bg=self.COLORS["bg_dark"])
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        Label(search_frame, text="البحث:",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_primary"],
              font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))

        search_entry = Entry(
            search_frame, textvariable=self.search_query,
            bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            insertbackground="white", font=("Arial", 11),
            width=40,
        )
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        search_entry.bind("<Return>", lambda e: self._perform_search())

        Button(
            search_frame, text="بحث", command=self._perform_search,
            bg=self.COLORS["accent_blue"], fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            padx=20, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        # خيارات البحث
        options_frame = Frame(tab, bg=self.COLORS["bg_dark"])
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        Label(options_frame, text="التصنيف:",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
              font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 5))

        self._category_filter = ttk.Combobox(
            options_frame, values=["الكل"], width=15,
            state="readonly",
        )
        self._category_filter.set("الكل")
        self._category_filter.pack(side=tk.LEFT, padx=5)

        Label(options_frame, text="الحد الأدنى للثقة:",
              bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_secondary"],
              font=("Arial", 9)).pack(side=tk.LEFT, padx=(15, 5))

        conf_scale = tk.Scale(
            options_frame, from_=0, to=1, resolution=0.05,
            orient=tk.HORIZONTAL, variable=self.confidence_threshold,
            bg=self.COLORS["bg_dark"], fg=self.COLORS["fg_primary"],
            troughcolor=self.COLORS["bg_light"],
            highlightthickness=0, length=100,
        )
        conf_scale.pack(side=tk.LEFT, padx=5)

        # نتائج البحث
        self.search_results = scrolledtext.ScrolledText(
            tab, bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            font=("Arial", 10), wrap=tk.WORD, height=20,
            insertbackground="white",
        )
        self.search_results.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.search_results.tag_configure("filename", foreground=self.COLORS["accent_blue"],
                                           font=("Arial", 10, "bold"))
        self.search_results.tag_configure("snippet", foreground=self.COLORS["fg_primary"])
        self.search_results.tag_configure("meta", foreground=self.COLORS["fg_secondary"])

    # ==================================================================
    # تبويب الإحصائيات
    # ==================================================================
    def _create_stats_tab(self):
        """إنشاء تبويب الإحصائيات."""
        tab = Frame(self.notebook, bg=self.COLORS["bg_dark"])
        self.notebook.add(tab, text="  الإحصائيات  ")

        btn_frame = Frame(tab, bg=self.COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        Button(
            btn_frame, text="تحديث الإحصائيات",
            command=self._refresh_stats,
            bg=self.COLORS["accent_blue"], fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            padx=15, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        Button(
            btn_frame, text="تصدير التقرير",
            command=self._export_stats,
            bg=self.COLORS["accent_green"], fg="white",
            font=("Arial", 10, "bold"), relief=tk.FLAT,
            padx=15, pady=5, cursor="hand2",
        ).pack(side=tk.LEFT, padx=5)

        self.stats_area = scrolledtext.ScrolledText(
            tab, bg=self.COLORS["bg_input"], fg=self.COLORS["fg_primary"],
            font=("Courier New", 10), wrap=tk.WORD,
            insertbackground="white", height=25,
        )
        self.stats_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.stats_area.tag_configure("header", foreground=self.COLORS["accent_blue"],
                                      font=("Courier New", 12, "bold"))
        self.stats_area.tag_configure("key", foreground=self.COLORS["accent_green"])
        self.stats_area.tag_configure("value", foreground=self.COLORS["fg_primary"])
        self.stats_area.tag_configure("separator", foreground=self.COLORS["border"])

    # ==================================================================
    # منطق المعالجة
    # ==================================================================
    def _select_input_folder(self):
        """اختيار مجلد الإدخال."""
        folder = filedialog.askdirectory(title="اختر مجلد الملفات")
        if folder:
            self.selected_folder.set(folder)
            self._log(f"تم اختيار المجلد: {folder}", "info")

    def _select_output_folder(self):
        """اختيار مجلد المخرجات."""
        folder = filedialog.askdirectory(title="اختر مجلد المخرجات")
        if folder:
            self.output_folder.set(folder)

    def _start_processing(self):
        """بدء المعالجة."""
        folder = self.selected_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("تنبيه", "يرجى اختيار مجلد صحيح")
            return

        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self._log("=" * 60, "header")
        self._log("بدأت عملية المعالجة الذكية", "header")
        self._log("=" * 60, "header")

        # تشغيل في خيط منفصل
        self._processing = True
        thread = threading.Thread(target=self._processing_worker, daemon=True)
        thread.start()

    def _processing_worker(self):
        """عامل المعالجة (يعمل في خيط منفصل)."""
        folder = self.selected_folder.get()
        extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']

        # جمع الملفات
        files = []
        for root, _, filenames in os.walk(folder):
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in extensions:
                    files.append(os.path.join(root, fname))

        if not files:
            self._msg_queue.put(("warning", "لا توجد ملفات مدعومة في المجلد"))
            self._msg_queue.put(("reset_buttons", None))
            return

        self._msg_queue.put(("info", f"تم العثور على {len(files)} ملف"))

        # تهيئة المكونات
        try:
            from modules.core.file_fingerprint import FileFingerprintManager
            from modules.core.classifier import MedicalClassifier
            from modules.core.dataset_generator import DatasetGenerator

            fp_mgr = FileFingerprintManager()
            classifier = MedicalClassifier()
            dataset_gen = DatasetGenerator(output_dir="training_data")

            new_count = 0
            cached_count = 0

            for i, filepath in enumerate(files):
                if not self._processing:
                    self._msg_queue.put(("warning", "تم إيقاف المعالجة"))
                    break

                fname = os.path.basename(filepath)
                progress = (i + 1) / len(files) * 100
                self._msg_queue.put(("progress", progress))

                # فحص البصمة
                if fp_mgr.is_new_file(filepath):
                    new_count += 1
                    self._msg_queue.put(("info", f"[{i+1}/{len(files)}] جاري معالجة: {fname}"))

                    # محاولة استخراج النص
                    text = self._extract_text(filepath)

                    if text:
                        # تصنيف
                        result = classifier.classify(text)
                        category = result["category"]
                        confidence = result["confidence"]

                        # تسجيل البصمة
                        fp_mgr.mark_processed(
                            filepath, category=category,
                            confidence_score=confidence
                        )

                        # حفظ النص
                        output = self.output_folder.get() or folder
                        os.makedirs(os.path.join(output, category), exist_ok=True)
                        txt_path = os.path.join(output, category, f"{fname}.txt")
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(text)

                        self._msg_queue.put((
                            "success",
                            f"تم: {fname} → {category} ({confidence:.0%})"
                        ))

                        # إضافة لبيانات التدريب
                        dataset_gen.add_entry(
                            input_text=text,
                            output_text=text,
                            specialty=category,
                            quality="auto" if confidence > 0.5 else "draft",
                            source_file=fname,
                        )
                    else:
                        self._msg_queue.put(("error", f"فشل استخراج النص: {fname}"))
                else:
                    cached_count += 1
                    self._msg_queue.put(("info", f"تخطى: {fname} (موجود سابقاً)"))

            # ملخص
            self._msg_queue.put(("header", "=" * 60))
            self._msg_queue.put(("header", f"اكتملت المعالجة!"))
            self._msg_queue.put(("success", f"جديد: {new_count} | متخطى: {cached_count}"))
            self._msg_queue.put(("info", f"إجمالي: {len(files)} ملف"))

            # تصدير بيانات التدريب
            if new_count > 0:
                dataset_gen.export("jsonl")
                self._msg_queue.put((
                    "success",
                    f"تم تصدير {len(dataset_gen)} إدخال لبيانات التدريب"
                ))

        except Exception as e:
            self._msg_queue.put(("error", f"خطأ في المعالجة: {str(e)}"))

        self._msg_queue.put(("progress", 100))
        self._msg_queue.put(("reset_buttons", None))

    def _stop_processing(self):
        """إيقاف المعالجة."""
        self._processing = False
        self._log("جاري إيقاف المعالجة...", "warning")

    def _extract_text(self, filepath: str) -> Optional[str]:
        """استخراج النص من الملف."""
        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == '.pdf':
                return self._extract_pdf(filepath)
            elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
                return self._extract_image(filepath)
        except Exception as e:
            self._msg_queue.put(("error", f"خطأ في {os.path.basename(filepath)}: {e}"))
        return None

    def _extract_pdf(self, filepath: str) -> Optional[str]:
        """استخراج النص من PDF."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip() if text.strip() else None
        except ImportError:
            self._msg_queue.put(("warning", "PyMuPDF غير مثبت — لا يمكن قراءة PDF"))
            return None

    def _extract_image(self, filepath: str) -> Optional[str]:
        """استخراج النص من الصورة باستخدام OCR."""
        try:
            import easyocr
            reader = easyocr.Reader(['ar', 'en'], gpu=False)
            results = reader.readtext(filepath)
            text = " ".join([r[1] for r in results])
            return text.strip() if text.strip() else None
        except ImportError:
            self._msg_queue.put(("warning", "EasyOCR غير مثبت — لا يمكن قراءة الصور"))
            return None
        except Exception as e:
            self._msg_queue.put(("error", f"خطأ في OCR: {e}"))
            return None

    # ==================================================================
    # التدقيق والاعتماد
    # ==================================================================
    def _run_spell_check(self):
        """تشغيل التدقيق اللغوي."""
        text = self.original_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("تنبيه", "أدخل نصاً للتدقيق")
            return

        try:
            from modules.nlp.language_corrector import LanguageCorrector
            corrector = LanguageCorrector(lang='ar')
            result = corrector.check(text)
            self.corrected_text.delete("1.0", tk.END)
            self.corrected_text.insert(tk.END, result["corrected"])
            self._log(f"التدقيق: {result['error_count']} خطأ ({result['method']})", "info")

            # إظهار الملخص
            summary = corrector.get_error_summary(result)
            if result["error_count"] > 0:
                self._log(summary, "warning")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل التدقيق: {e}")

    def _run_classification(self):
        """تشغيل تصنيف المحتوى."""
        text = self.original_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("تنبيه", "أدخل نصاً للتصنيف")
            return

        try:
            from modules.core.classifier import MedicalClassifier
            clf = MedicalClassifier()
            result = clf.classify(text)
            category = result["category"]
            confidence = result["confidence"]

            msg = f"التصنيف: {category} (الثقة: {confidence:.0%})"
            self._log(msg, "success")

            if result.get("top_keywords"):
                self._log(f"الكلمات المفتاحية: {', '.join(result['top_keywords'][:5])}", "info")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل التصنيف: {e}")

    def _approve_for_training(self):
        """اعتماد النص الحالي لبيانات التدريب."""
        original = self.original_text.get("1.0", tk.END).strip()
        corrected = self.corrected_text.get("1.0", tk.END).strip()

        if not corrected:
            messagebox.showinfo("تنبيه", "لا يوجد نص للاعتماد")
            return

        try:
            from modules.core.dataset_generator import DatasetGenerator
            gen = DatasetGenerator(output_dir="training_data")

            gen.add_entry(
                input_text=original or corrected,
                output_text=corrected,
                quality="verified",
                specialty="orthopedic",
            )

            gen.export("jsonl")
            self._log("تم اعتماد النص لبيانات التدريب", "success")
            self._training_count_label.config(text=f"بيانات التدريب: {len(gen)}")
            messagebox.showinfo("نجاح", "تمت إضافة النص إلى بيانات التدريب بنجاح!")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الحفظ: {e}")

    # ==================================================================
    # البحث
    # ==================================================================
    def _perform_search(self):
        """تنفيذ البحث."""
        query = self.search_query.get().strip()
        if not query:
            messagebox.showinfo("تنبيه", "أدخل كلمة البحث")
            return

        self.search_results.delete("1.0", tk.END)
        self._log(f"جاري البحث عن: {query}", "info")

        try:
            from modules.core.search_engine import SearchEngine
            engine = SearchEngine()

            results = engine.search(query, limit=50)
            total = results.get("total_count", 0)

            if total == 0:
                self.search_results.insert(tk.END, f"لم يتم العثور على نتائج لـ: {query}\n\n")
                return

            self.search_results.insert(
                tk.END,
                f"تم العثور على {total} نتيجة:\n", "header"
            )

            for r in results.get("results", []):
                fname = r.get("file_name", "Unknown")
                cat = r.get("category", "N/A")
                conf = r.get("confidence_score", 0)
                snippet = r.get("snippet", "")

                self.search_results.insert(tk.END, f"\n--- {fname}", "filename")
                self.search_results.insert(tk.END, f" [{cat}] ({conf:.0%})\n", "meta")
                if snippet:
                    self.search_results.insert(tk.END, f"  {snippet}\n", "snippet")

            self._log(f"البحث: {total} نتيجة", "success")
            engine.close()

        except Exception as e:
            self.search_results.insert(tk.END, f"خطأ في البحث: {e}\n", "error")

    # ==================================================================
    # الإحصائيات
    # ==================================================================
    def _refresh_stats(self):
        """تحديث الإحصائيات."""
        self.stats_area.delete("1.0", tk.END)

        try:
            from modules.core.file_fingerprint import FileFingerprintManager
            fp = FileFingerprintManager()
            stats = fp.get_statistics()

            self.stats_area.insert(tk.END, "إحصائيات الأرشيف الرقمي\n", "header")
            self.stats_area.insert(tk.END, "=" * 50 + "\n\n", "separator")

            self.stats_area.insert(tk.END, "الملفات:\n", "key")
            self.stats_area.insert(tk.END, f"  الإجمالي:       {stats.get('total_files', 0)}\n", "value")
            self.stats_area.insert(tk.END, f"  متوسط الثقة:    {stats.get('average_confidence', 0):.1%}\n", "value")
            self.stats_area.insert(tk.END, f"  الحجم الكلي:    {stats.get('total_size_mb', 0):.1f} MB\n", "value")
            self.stats_area.insert(tk.END, f"  متوسط المعالجة: {stats.get('average_processing_time', 0):.1f} ثانية\n\n", "value")

            cats = stats.get("by_category", [])
            if cats:
                self.stats_area.insert(tk.END, "التصنيفات:\n", "key")
                for cat in cats:
                    self.stats_area.insert(
                        tk.END,
                        f"  {cat.get('category', 'N/A'):20s} {cat.get('count', 0)} ملف\n",
                        "value"
                    )

            exts = stats.get("by_extension", [])
            if exts:
                self.stats_area.insert(tk.END, "\nالامتدادات:\n", "key")
                for ext in exts[:10]:
                    self.stats_area.insert(
                        tk.END,
                        f"  {ext.get('file_extension', 'N/A'):10s} {ext.get('count', 0)} ملف\n",
                        "value"
                    )

            fp.close()

        except Exception as e:
            self.stats_area.insert(tk.END, f"خطأ في تحميل الإحصائيات: {e}\n", "error")

    def _export_stats(self):
        """تصدير الإحصائيات."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
            title="حفظ التقرير",
        )
        if not filepath:
            return

        try:
            from modules.core.file_fingerprint import FileFingerprintManager
            fp = FileFingerprintManager()
            fp.export_fingerprints(filepath)
            fp.close()
            self._log(f"تم تصدير التقرير إلى: {filepath}", "success")
            messagebox.showinfo("نجاح", "تم تصدير التقرير بنجاح!")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل التصدير: {e}")

    # ==================================================================
    # أدوات إضافية
    # ==================================================================
    def _find_duplicates(self):
        """كشف الملفات المكررة."""
        folder = self.selected_folder.get()
        if not folder:
            folder = filedialog.askdirectory(title="اختر المجلد للفحص")
        if not folder:
            return

        self._log("جاري البحث عن الملفات المكررة...", "info")

        try:
            from modules.core.file_fingerprint import FileFingerprintManager
            fp = FileFingerprintManager()
            duplicates = fp.find_duplicates(folder)
            fp.close()

            if not duplicates:
                self._log("لم يتم العثور على ملفات مكررة", "success")
            else:
                total_dupes = sum(len(g) - 1 for g in duplicates)
                self._log(f"تم العثور على {total_dupes} ملف مكرر في {len(duplicates)} مجموعة", "warning")
                for group in duplicates[:10]:
                    names = [os.path.basename(f["path"]) for f in group]
                    self._log(f"  متكرر: {', '.join(names)}", "info")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الفحص: {e}")

    def _cleanup_records(self):
        """تنظيف السجلات القديمة."""
        try:
            from modules.core.file_fingerprint import FileFingerprintManager
            fp = FileFingerprintManager()
            deleted = fp.cleanup_old_records(days=90)
            fp.close()
            self._log(f"تم حذف {deleted} سجل قديم", "success")
            messagebox.showinfo("نجاح", f"تم حذف {deleted} سجل")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل التنظيف: {e}")

    def _toggle_watchdog(self):
        """تشغيل/إيقاف المراقبة التلقائية."""
        folder = self.selected_folder.get()
        if not folder:
            self.auto_watch_var.set(False)
            messagebox.showwarning("تنبيه", "اختر مجلد أولاً")
            return

        if self.auto_watch_var.get():
            try:
                from modules.core.watchdog_service import FolderWatchdog
                self._watchdog = FolderWatchdog(
                    watch_dir=folder,
                    callback=self._watchdog_callback,
                    poll_interval=3.0,
                )
                self._watchdog.start()
                self._log(f"بدأت مراقبة: {folder}", "success")
            except Exception as e:
                self.auto_watch_var.set(False)
                messagebox.showerror("خطأ", f"فشل بدء المراقبة: {e}")
        else:
            if self._watchdog:
                self._watchdog.stop()
                self._log("تم إيقاف المراقبة", "info")

    def _watchdog_callback(self, filepath: str):
        """دالة الاستدعاء لمراقب المجلدات."""
        self._msg_queue.put(("info", f"ملف جديد: {os.path.basename(filepath)}"))

    def _show_about(self):
        """عرض معلومات البرنامج."""
        messagebox.showinfo(
            "عن OmniFile AI Processor",
            "OmniFile AI Processor v4.2.0\n\n"
            "نظام ذكاء اصطناعي متكامل لمعالجة الملفات\n"
            "والنصوص العربية مع التركيز على المحتوى الطبي\n\n"
            "المطور: Dr. Abdulmalek Tamer Al-husseini\n"
            "الرخصة: MIT License\n\n"
            "المحركات المدعومة:\n"
            "• Tesseract OCR\n"
            "• EasyOCR\n"
            "• PaddleOCR\n"
            "• TrOCR\n"
            "• Surya OCR (معطل حالياً)"
        )

    def _check_initialization(self):
        """فحص توفر المحركات."""
        status_parts = []

        try:
            import easyocr
            status_parts.append("EasyOCR ✓")
        except ImportError:
            status_parts.append("EasyOCR ✗")

        try:
            import fitz
            status_parts.append("PyMuPDF ✓")
        except ImportError:
            status_parts.append("PyMuPDF ✗")

        try:
            from modules.core.classifier import MedicalClassifier
            status_parts.append("Classifier ✓")
        except Exception:
            status_parts.append("Classifier ✗")

        self._engine_status.config(text=" | ".join(status_parts))

    # ==================================================================
    # أدوات مساعدة
    # ==================================================================
    def _log(self, message: str, tag: str = "info"):
        """إضافة رسالة لمنطقة السجلات."""
        self.log_area.insert(tk.END, message + "\n", tag)
        self.log_area.see(tk.END)

    def _process_messages(self):
        """معالجة الرسائل من الخيوط."""
        try:
            while True:
                msg_type, content = self._msg_queue.get_nowait()
                if msg_type == "reset_buttons":
                    self._start_btn.config(state=tk.NORMAL)
                    self._stop_btn.config(state=tk.DISABLED)
                elif msg_type == "progress":
                    self.progress_var.set(content)
                else:
                    self._log(str(content), msg_type)
        except queue.Empty:
            pass
        self.root.after(100, self._process_messages)


def main():
    """نقطة الدخول الرئيسية."""
    root = tk.Tk()

    # محاولة تعيين أيقونة التطبيق
    try:
        icon_path = os.path.join(PROJECT_ROOT, "docs", "author.png")
        if os.path.exists(icon_path):
            root.iconphoto(True, tk.PhotoImage(file=icon_path))
    except Exception:
        pass

    app = OmniFileGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.quit(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
