#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/ui/word_editor.py
======================================

واجهة تفاعلية لتصحيح الكلمات في وضع التعليم.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
from typing import Callable, List, Optional, Dict
import json

import cv2
import numpy as np
from PIL import Image, ImageTk


class TeachingModeUI:
    """
    واجهة تعليمية تفاعلية للتصحيح الكلمة بكلمة.
    
    المميزات:
    - عرض الصفحة الأصلية مع تحديد الكلمات
    - نافذة منبثقة لتصحيح كل كلمة
    - التنقل السريع بين الكلمات
    - حفظ التصحيحات تلقائياً
    - معاينة التغييرات فوراً
    """
    
    def __init__(
        self,
        segmenter,
        on_correction: Callable[[str, str, dict], None] = None,
        auto_save_path: Optional[Path] = None
    ):
        self.segmenter = segmenter
        self.on_correction = on_correction
        self.auto_save_path = auto_save_path or Path("./corrections.jsonl")
        
        # البيانات
        self.current_layout = None
        self.current_image = None
        self.word_buttons = {}  # id -> button
        self.corrections = {}  # word_id -> corrected_text
        
        # إعداد النافذة
        self.root = tk.Tk()
        self.root.title("🎯 OmniFile - وضع التعليم")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f5f5f5')
        
        # اتجاه RTL للعربية
        self.root.tk.call('tk', 'scaling', 1.5)
        
        self._setup_styles()
        self._create_ui()
        
        # اختصارات لوحة المفاتيح
        self._setup_shortcuts()
    
    def _setup_styles(self):
        """إعداد الأنماط."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # ألوان مخصصة
        style.configure('Word.TButton',
            font=('Segoe UI', 14),
            padding=5,
            background='#e3f2fd',
            foreground='#1565c0'
        )
        
        style.configure('WordCorrected.TButton',
            font=('Segoe UI', 14, 'bold'),
            padding=5,
            background='#c8e6c9',
            foreground='#2e7d32'
        )
        
        style.configure('WordHighConfidence.TButton',
            font=('Segoe UI', 14),
            padding=5,
            background='#fff3e0',
            foreground='#ef6c00'
        )
        
        style.configure('WordLowConfidence.TButton',
            font=('Segoe UI', 14),
            padding=5,
            background='#ffebee',
            foreground='#c62828'
        )
        
        style.configure('Info.TLabel',
            font=('Segoe UI', 12),
            background='#f5f5f5',
            foreground='#333'
        )
        
        style.configure('Title.TLabel',
            font=('Segoe UI', 18, 'bold'),
            background='#f5f5f5',
            foreground='#1565c0'
        )
    
    def _create_ui(self):
        """إنشاء واجهة المستخدم."""
        # الإطار الرئيسي
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)  # الصورة
        main_frame.columnconfigure(1, weight=1)  # اللوحة الجانبية
        main_frame.rowconfigure(1, weight=1)
        
        # العنوان
        title = ttk.Label(
            main_frame,
            text="🎯 وضع التعليم - تصحيح الكلمات",
            style='Title.TLabel'
        )
        title.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        
        # إطار الصورة
        image_frame = ttk.LabelFrame(main_frame, text="الصفحة الأصلية", padding="5")
        image_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # Canvas للصورة مع Scrollbar
        self.canvas_frame = ttk.Frame(image_frame)
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='white',
            highlightthickness=0
        )
        self.h_scroll = ttk.Scrollbar(image_frame, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(image_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        
        # اللوحة الجانبية
        sidebar = ttk.LabelFrame(main_frame, text="معلومات وتحكم", padding="10")
        sidebar.grid(row=1, column=1, sticky="nsew")
        
        # إحصائيات
        self.stats_frame = ttk.LabelFrame(sidebar, text="الإحصائيات", padding="5")
        self.stats_frame.pack(fill="x", pady=(0, 10))
        
        self.total_words_var = tk.StringVar(value="إجمالي الكلمات: 0")
        self.corrected_var = tk.StringVar(value="المصححة: 0")
        self.remaining_var = tk.StringVar(value="المتبقية: 0")
        self.accuracy_var = tk.StringVar(value="الدقة الحالية: 0%")
        
        ttk.Label(self.stats_frame, textvariable=self.total_words_var, style='Info.TLabel').pack(anchor="e")
        ttk.Label(self.stats_frame, textvariable=self.corrected_var, style='Info.TLabel').pack(anchor="e")
        ttk.Label(self.stats_frame, textvariable=self.remaining_var, style='Info.TLabel').pack(anchor="e")
        ttk.Label(self.stats_frame, textvariable=self.accuracy_var, style='Info.TLabel').pack(anchor="e")
        
        # الكلمة الحالية
        self.current_frame = ttk.LabelFrame(sidebar, text="الكلمة الحالية", padding="5")
        self.current_frame.pack(fill="x", pady=(0, 10))
        
        self.current_image_label = ttk.Label(self.current_frame)
        self.current_image_label.pack(pady=5)
        
        self.current_text_var = tk.StringVar(value="")
        ttk.Label(
            self.current_frame,
            textvariable=self.current_text_var,
            font=('Segoe UI', 16, 'bold'),
            foreground='#1565c0'
        ).pack()
        
        self.current_confidence_var = tk.StringVar(value="")
        ttk.Label(
            self.current_frame,
            textvariable=self.current_confidence_var,
            font=('Segoe UI', 10),
            foreground='#666'
        ).pack()
        
        # حقل التصحيح
        correction_frame = ttk.LabelFrame(sidebar, text="التصحيح", padding="5")
        correction_frame.pack(fill="x", pady=(0, 10))
        
        self.correction_entry = ttk.Entry(
            correction_frame,
            font=('Segoe UI', 16),
            justify='right'  # RTL للعربية
        )
        self.correction_entry.pack(fill="x", pady=5)
        self.correction_entry.bind('<Return>', lambda e: self._apply_correction())
        self.correction_entry.bind('<KP_Enter>', lambda e: self._apply_correction())
        
        # أزرار التصحيح
        btn_frame = ttk.Frame(correction_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(
            btn_frame,
            text="✓ تصحيح (Enter)",
            command=self._apply_correction
        ).pack(side="right", padx=2)
        
        ttk.Button(
            btn_frame,
            text="✓ صحيحة (Space)",
            command=self._mark_correct
        ).pack(side="right", padx=2)
        
        ttk.Button(
            btn_frame,
            text="تخطي (Tab)",
            command=self._skip_word
        ).pack(side="right", padx=2)
        
        # التنقل
        nav_frame = ttk.LabelFrame(sidebar, text="التنقل", padding="5")
        nav_frame.pack(fill="x", pady=(0, 10))
        
        nav_buttons = ttk.Frame(nav_frame)
        nav_buttons.pack(fill="x")
        
        ttk.Button(
            nav_buttons,
            text="← السابق",
            command=self._previous_word
        ).pack(side="right", padx=2)
        
        ttk.Button(
            nav_buttons,
            text="التالي →",
            command=self._next_word
        ).pack(side="right", padx=2)
        
        # قائمة الكلمات
        words_frame = ttk.LabelFrame(sidebar, text="قائمة الكلمات", padding="5")
        words_frame.pack(fill="both", expand=True)
        
        # Treeview للكلمات
        self.words_tree = ttk.Treeview(
            words_frame,
            columns=('status', 'original', 'corrected', 'confidence'),
            show='headings',
            height=15
        )
        
        self.words_tree.heading('status', text='الحالة')
        self.words_tree.heading('original', text='الأصلي')
        self.words_tree.heading('corrected', text='المصحح')
        self.words_tree.heading('confidence', text='الثقة')
        
        self.words_tree.column('status', width=60, anchor='center')
        self.words_tree.column('original', width=100, anchor='e')
        self.words_tree.column('corrected', width=100, anchor='e')
        self.words_tree.column('confidence', width=60, anchor='center')
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(words_frame, orient="vertical", command=self.words_tree.yview)
        self.words_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.words_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # شريط الحالة
        self.status_var = tk.StringVar(value="جاهز")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief="sunken",
            padding=(5, 2)
        )
        status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # شريط التقدم
        self.progress = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=200
        )
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
    
    def _setup_shortcuts(self):
        """إعداد اختصارات لوحة المفاتيح."""
        self.root.bind('<Control-s>', lambda e: self._save_corrections())
        self.root.bind('<Control-q>', lambda e: self._quit())
        self.root.bind('<space>', lambda e: self._mark_correct())
        self.root.bind('<Tab>', lambda e: self._skip_word())
        self.root.bind('<Left>', lambda e: self._previous_word())
        self.root.bind('<Right>', lambda e: self._next_word())
        self.root.bind('<Up>', lambda e: self._navigate_tree(-1))
        self.root.bind('<Down>', lambda e: self._navigate_tree(1))
        self.root.bind('<Control-z>', lambda e: self._undo_correction())
        self.root.bind('<F1>', lambda e: self._show_help())
    
    def load_page(self, image_path: Path):
        """تحميل صفحة للتصحيح."""
        self.status_var.set("جاري تحليل الصفحة...")
        self.root.update()
        
        # تحميل الصورة
        self.current_image = cv2.imread(str(image_path))
        if self.current_image is None:
            messagebox.showerror("خطأ", f"لا يمكن قراءة الصورة: {image_path}")
            return
        
        # تقسيم الصفحة
        self.current_layout = self.segmenter.segment_page(image_path)
        
        # عرض الصورة
        self._display_page()
        
        # ملء قائمة الكلمات
        self._populate_words_list()
        
        # تحديث الإحصائيات
        self._update_stats()
        
        # اختيار أول كلمة
        self._select_first_word()
        
        self.status_var.set(f"تم تحميل الصفحة: {len(self._all_words())} كلمة")
    
    def _display_page(self):
        """عرض الصفحة على Canvas."""
        if self.current_image is None:
            return
        
        # تحويل للعرض
        display_image = self.current_image.copy()
        
        # رسم مربعات حول الكلمات
        for word in self._all_words():
            x1, y1, x2, y2 = word.bbox
            
            # لون يعتمد على الحالة
            if word.id in self.corrections:
                color = (46, 125, 50)  # أخضر - مصحح
                thickness = 2
            elif word.confidence > 0.9:
                color = (239, 108, 0)  # برتقالي - ثقة عالية
                thickness = 1
            else:
                color = (198, 40, 40)  # أحمر - يحتاج مراجعة
                thickness = 2
            
            cv2.rectangle(display_image, (x1, y1), (x2, y2), color, thickness)
            
            # رقم الكلمة
            if word.reading_order < 10:
                cv2.putText(
                    display_image,
                    str(word.reading_order),
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1
                )
        
        # تحويل لـ PIL
        rgb = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        
        # تغيير الحجم إذا لزم الأمر
        max_width = 1000
        if pil_image.width > max_width:
            ratio = max_width / pil_image.width
            new_height = int(pil_image.height * ratio)
            pil_image = pil_image.resize((max_width, new_height), Image.LANCZOS)
        
        # عرض على Canvas
        self.tk_image = ImageTk.PhotoImage(pil_image)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, pil_image.width, pil_image.height))
    
    def _populate_words_list(self):
        """ملء قائمة الكلمات."""
        # مسح القائمة
        for item in self.words_tree.get_children():
            self.words_tree.delete(item)
        
        # إضافة الكلمات
        for word in self._all_words():
            status = "⏳"  # في الانتظار
            corrected = ""
            
            self.words_tree.insert(
                '',
                'end',
                iid=word.id,
                values=(status, word.text, corrected, f"{word.confidence:.0%}")
            )
    
    def _all_words(self) -> List:
        """الحصول على جميع الكلمات."""
        words = []
        for para in self.current_layout.paragraphs:
            for line in para.lines:
                words.extend(line.words)
        return words
    
    def _update_stats(self):
        """تحديث الإحصائيات."""
        all_words = self._all_words()
        total = len(all_words)
        corrected = len(self.corrections)
        remaining = total - corrected
        
        # حساب الدقة
        if corrected > 0:
            correct_count = sum(
                1 for w in all_words
                if w.id in self.corrections and self.corrections[w.id] == w.text
            )
            accuracy = correct_count / corrected * 100
        else:
            accuracy = 0
        
        self.total_words_var.set(f"إجمالي الكلمات: {total}")
        self.corrected_var.set(f"المصححة: {corrected}")
        self.remaining_var.set(f"المتبقية: {remaining}")
        self.accuracy_var.set(f"الدقة الحالية: {accuracy:.1f}%")
        
        # تحديث شريط التقدم
        if total > 0:
            self.progress['value'] = (corrected / total) * 100
    
    def _select_first_word(self):
        """اختيار أول كلمة تحتاج تصحيحاً."""
        for word in self._all_words():
            if word.confidence < 0.9 and word.id not in self.corrections:
                self._select_word(word.id)
                return
        
        # إذا كلها بثقة عالية، اختر الأولى
        if self._all_words():
            self._select_word(self._all_words()[0].id)
    
    def _select_word(self, word_id: str):
        """اختيار كلمة للتصحيح."""
        # العثور على الكلمة
        word = None
        for w in self._all_words():
            if w.id == word_id:
                word = w
                break
        
        if word is None:
            return
        
        self.current_word_id = word_id
        
        # تحديث العرض
        self._display_current_word(word)
        
        # تحديث الإدخال
        self.correction_entry.delete(0, 'end')
        
        # إذا تم تصحيحها سابقاً
        if word_id in self.corrections:
            self.correction_entry.insert(0, self.corrections[word_id])
        else:
            self.correction_entry.insert(0, word.text)
        
        self.correction_entry.select_range(0, 'end')
        self.correction_entry.focus()
        
        # تحديث القائمة
        self.words_tree.selection_set(word_id)
        self.words_tree.see(word_id)
        
        # تحديث الحالة
        self.status_var.set(f"كلمة {word.reading_order + 1}: الثقة {word.confidence:.1%}")
    
    def _display_current_word(self, word):
        """عرض الكلمة الحالية كبيرة."""
        # استخراج صورة الكلمة
        word_image = self.segmenter.extract_word_image(
            self.current_image,
            word,
            padding=10
        )
        
        # تكبير للعرض
        scale = 4
        h, w = word_image.shape[:2]
        word_image = cv2.resize(word_image, (w*scale, h*scale), interpolation=cv2.INTER_CUBIC)
        
        # تحويل
        rgb = cv2.cvtColor(word_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        
        self.current_word_tk = ImageTk.PhotoImage(pil_image)
        self.current_image_label.configure(image=self.current_word_tk)
        
        # النصوص
        self.current_text_var.set(word.text)
        self.current_confidence_var.set(f"الثقة: {word.confidence:.1%}")
    
    def _apply_correction(self):
        """تطبيق تصحيح."""
        if not hasattr(self, 'current_word_id'):
            return
        
        corrected = self.correction_entry.get().strip()
        if not corrected:
            return
        
        word_id = self.current_word_id
        
        # حفظ التصحيح
        self.corrections[word_id] = corrected
        
        # تحديث القائمة
        word = self._get_word_by_id(word_id)
        if word:
            self.words_tree.item(
                word_id,
                values=("✓", word.text, corrected, f"{word.confidence:.0%}")
            )
        
        # استدعاء callback
        if self.on_correction:
            word_image = self.segmenter.extract_word_image(
                self.current_image,
                word
            )
            self.on_correction(word.text, corrected, {
                'word_id': word_id,
                'word_image': word_image,
                'bbox': word.bbox,
                'confidence': word.confidence
            })
        
        # حفظ تلقائي
        self._auto_save()
        
        # تحديث الإحصائيات
        self._update_stats()
        
        # الانتقال للتالية
        self._next_word()
    
    def _mark_correct(self):
        """تعليم الكلمة كصحيحة."""
        if not hasattr(self, 'current_word_id'):
            return
        
        word = self._get_word_by_id(self.current_word_id)
        if word:
            self.corrections[self.current_word_id] = word.text
            self._apply_correction()
    
    def _skip_word(self):
        """تخطي الكلمة."""
        self._next_word()
    
    def _next_word(self):
        """الانتقال للكلمة التالية."""
        all_words = self._all_words()
        if not all_words:
            return
        
        # العثور على الكلمة الحالية
        current_idx = -1
        for i, w in enumerate(all_words):
            if w.id == getattr(self, 'current_word_id', None):
                current_idx = i
                break
        
        # الانتقال للتالية
        next_idx = (current_idx + 1) % len(all_words)
        self._select_word(all_words[next_idx].id)
    
    def _previous_word(self):
        """الانتقال للكلمة السابقة."""
        all_words = self._all_words()
        if not all_words:
            return
        
        current_idx = -1
        for i, w in enumerate(all_words):
            if w.id == getattr(self, 'current_word_id', None):
                current_idx = i
                break
        
        prev_idx = (current_idx - 1) % len(all_words)
        self._select_word(all_words[prev_idx].id)
    
    def _navigate_tree(self, direction: int):
        """التنقل في الشجرة."""
        selection = self.words_tree.selection()
        if not selection:
            return
        
        current = selection[0]
        all_items = self.words_tree.get_children()
        
        try:
            idx = all_items.index(current)
            new_idx = max(0, min(len(all_items) - 1, idx + direction))
            self._select_word(all_items[new_idx])
        except ValueError:
            pass
    
    def _get_word_by_id(self, word_id: str):
        """الحصول على كلمة بواسطة المعرف."""
        for w in self._all_words():
            if w.id == word_id:
                return w
        return None
    
    def _undo_correction(self):
        """التراجع عن آخر تصحيح."""
        if not self.corrections:
            return
        
        last_id = list(self.corrections.keys())[-1]
        del self.corrections[last_id]
        
        word = self._get_word_by_id(last_id)
        if word:
            self.words_tree.item(
                last_id,
                values=("⏳", word.text, "", f"{word.confidence:.0%}")
            )
        
        self._update_stats()
        self._select_word(last_id)
    
    def _auto_save(self):
        """حفظ تلقائي للتصحيحات."""
        if not self.auto_save_path:
            return
        
        data = []
        for word_id, corrected in self.corrections.items():
            word = self._get_word_by_id(word_id)
            if word:
                data.append({
                    'word_id': word_id,
                    'original': word.text,
                    'corrected': corrected,
                    'bbox': word.bbox,
                    'confidence': word.confidence,
                    'timestamp': str(np.datetime64('now'))
                })
        
        with open(self.auto_save_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    def _save_corrections(self):
        """حفظ التصحيحات يدوياً."""
        self._auto_save()
        messagebox.showinfo("تم الحفظ", f"تم حفظ {len(self.corrections)} تصحيح")
    
    def _show_help(self):
        """عرض مساعدة."""
        help_text = """
اختصارات لوحة المفاتيح:
─────────────────────────
Enter       تطبيق التصحيح
Space       تعليم كصحيحة
Tab         تخطي الكلمة
← →         التنقل بين الكلمات
↑ ↓         التنقل في القائمة
Ctrl+Z      تراجع
Ctrl+S      حفظ
Ctrl+Q      خروج
F1          هذه المساعدة
        """
        messagebox.showinfo("مساعدة", help_text)
    
    def _quit(self):
        """الخروج."""
        if self.corrections:
            save = messagebox.askyesnocancel(
                "تصحيحات غير محفوظة",
                "هل تريد حفظ التصحيحات قبل الخروج؟"
            )
            if save is None:  # Cancel
                return
            if save:
                self._auto_save()
        
        self.root.quit()
    
    def get_corrections(self) -> Dict[str, str]:
        """الحصول على جميع التصحيحات."""
        return self.corrections.copy()
    
    def get_training_pairs(self) -> List[Dict]:
        """الحصول على أزواج التدريب."""
        pairs = []
        for word_id, corrected in self.corrections.items():
            word = self._get_word_by_id(word_id)
            if word and corrected != word.text:
                word_image = self.segmenter.extract_word_image(
                    self.current_image,
                    word
                )
                pairs.append({
                    'image': word_image,
                    'original_text': word.text,
                    'corrected_text': corrected,
                    'bbox': word.bbox,
                    'confidence_before': word.confidence
                })
        return pairs
    
    def run(self):
        """تشغيل الواجهة."""
        self.root.mainloop()
    
    def run_with_page(self, image_path: Path):
        """تشغيل مع صفحة محددة."""
        self.load_page(image_path)
        self.run()


# =============================================================================
# واجهة ويب (Flask) - بديل للـ Tkinter
# =============================================================================

from flask import Flask, render_template, request, jsonify
import base64


class WebTeachingInterface:
    """واجهة تعليمية على الويب."""
    
    def __init__(self, segmenter, on_correction=None):
        self.segmenter = segmenter
        self.on_correction = on_correction
        self.app = Flask(__name__)
        self.current_layout = None
        self.current_image = None
        self.corrections = {}
        
        self._setup_routes()
    
    def _setup_routes(self):
        """إعداد المسارات."""
        
        @self.app.route('/')
        def index():
            return render_template('teaching_mode.html')
        
        @self.app.route('/api/load', methods=['POST'])
        def load_page():
            """تحميل صفحة."""
            data = request.json
            image_path = data.get('image_path')
            
            self.current_image = cv2.imread(image_path)
            self.current_layout = self.segmenter.segment_page(image_path)
            
            # تحويل الصورة لـ base64
            _, buffer = cv2.imencode('.jpg', self.current_image)
            img_base64 = base64.b64encode(buffer).decode()
            
            # تجهيز بيانات الكلمات
            words = []
            for para in self.current_layout.paragraphs:
                for line in para.lines:
                    for word in line.words:
                        words.append({
                            'id': word.id,
                            'text': word.text,
                            'confidence': word.confidence,
                            'bbox': word.bbox,
                            'needs_review': word.confidence < 0.9
                        })
            
            return jsonify({
                'success': True,
                'image': img_base64,
                'words': words,
                'width': self.current_layout.width,
                'height': self.current_layout.height
            })
        
        @self.app.route('/api/correct', methods=['POST'])
        def correct_word():
            """تصحيح كلمة."""
            data = request.json
            word_id = data.get('word_id')
            corrected = data.get('corrected')
            
            self.corrections[word_id] = corrected
            
            # استدعاء callback
            if self.on_correction:
                word = self._get_word_by_id(word_id)
                if word:
                    word_image = self.segmenter.extract_word_image(
                        self.current_image,
                        word
                    )
                    self.on_correction(word.text, corrected, {
                        'word_id': word_id,
                        'word_image': word_image,
                        'bbox': word.bbox
                    })
            
            return jsonify({'success': True})
        
        @self.app.route('/api/export', methods=['POST'])
        def export():
            """تصدير التصحيحات."""
            return jsonify({
                'success': True,
                'corrections': self.corrections,
                'training_pairs': self._get_training_pairs_web()
            })
    
    def _get_word_by_id(self, word_id: str):
        """الحصول على كلمة."""
        for para in self.current_layout.paragraphs:
            for line in para.lines:
                for word in line.words:
                    if word.id == word_id:
                        return word
        return None
    
    def _get_training_pairs_web(self):
        """أزواج التدريب للويب."""
        pairs = []
        for word_id, corrected in self.corrections.items():
            word = self._get_word_by_id(word_id)
            if word and corrected != word.text:
                word_image = self.segmenter.extract_word_image(
                    self.current_image,
                    word
                )
                _, buffer = cv2.imencode('.png', word_image)
                img_base64 = base64.b64encode(buffer).decode()
                
                pairs.append({
                    'image': img_base64,
                    'original': word.text,
                    'corrected': corrected
                })
        return pairs
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """تشغيل الخادم."""
        self.app.run(host=host, port=port, debug=debug)
