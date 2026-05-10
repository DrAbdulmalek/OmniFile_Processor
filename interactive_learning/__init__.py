#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/__init__.py
=================================

نظام التعلم التفاعلي المتكامل.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
import json

import cv2
import numpy as np

from .core.segmenter import SmartSegmenter, PageLayout, WordBox
from .ui.word_editor import TeachingModeUI, WebTeachingInterface
from .learning.online_learner import OnlineLearner, AdaptiveLearningPipeline
from .rendering.html_renderer import HTMLRenderer
from .graphics.diagram_renderer import FlowchartRenderer, ChartRenderer, FlowchartNode, FlowchartEdge


class InteractiveLearningSystem:
    """
    النظام المتكامل للتعلم التفاعلي.
    
    يوحد:
    - التقسيم الذكي
    - وضع التعليم
    - التعلم الفوري
    - إعادة الإنتاج
    """
    
    def __init__(
        self,
        model_path: str = "microsoft/trocr-large-handwritten",
        learning_mode: bool = True,
        auto_train: bool = True,
        device: str = "auto"
    ):
        # المكونات
        self.segmenter = SmartSegmenter(
            ocr_model=model_path,
            device=device
        )
        
        self.learner = OnlineLearner(
            base_model=model_path,
            device=device
        )
        
        self.pipeline = AdaptiveLearningPipeline(
            segmenter=self.segmenter,
            learner=self.learner,
            min_corrections_for_training=10 if auto_train else 999999
        )
        
        self.renderer = HTMLRenderer(
            include_interactive=learning_mode,
            rtl=True
        )
        
        self.learning_mode = learning_mode
        
        # الحالة
        self.current_layout: Optional[PageLayout] = None
        self.current_image: Optional[np.ndarray] = None
        self.corrections: Dict[str, str] = {}
    
    def process_page(self, image_path: Union[str, Path]) -> PageLayout:
        """
        معالجة صفحة وإرجاع التخطيط.
        
        Args:
            image_path: مسار الصورة
        
        Returns:
            PageLayout كامل
        """
        image_path = Path(image_path)
        
        # تحميل الصورة
        self.current_image = cv2.imread(str(image_path))
        
        # التقسيم
        self.current_layout = self.segmenter.segment_page(image_path)
        
        return self.current_layout
    
    def teaching_mode(
        self,
        layout: Optional[PageLayout] = None,
        image_path: Optional[Path] = None,
        ui_type: str = "desktop"  # desktop أو web
    ) -> Dict[str, str]:
        """
        تشغيل وضع التعليم التفاعلي.
        
        Args:
            layout: تخطيط مسبق (اختياري)
            image_path: مسار الصورة (اختياري)
            ui_type: نوع الواجهة
        
        Returns:
            التصحيحات {word_id: corrected_text}
        """
        if layout:
            self.current_layout = layout
        
        if image_path and self.current_image is None:
            self.current_image = cv2.imread(str(image_path))
        
        if self.current_layout is None:
            raise ValueError("No layout loaded. Call process_page first.")
        
        # اختيار الواجهة
        if ui_type == "desktop":
            return self._run_desktop_ui()
        else:
            return self._run_web_ui()
    
    def _run_desktop_ui(self) -> Dict[str, str]:
        """تشغيل واجهة سطح المكتب."""
        def on_correction(original, corrected, metadata):
            """معالجة تصحيح من المستخدم."""
            self.pipeline.process_user_correction(
                original_word=type('Word', (), {
                    'text': original,
                    'confidence': metadata.get('confidence', 0),
                    'id': metadata.get('word_id', ''),
                    'bbox': metadata.get('bbox', (0, 0, 0, 0))
                })(),
                corrected_text=corrected,
                word_image=metadata.get('word_image')
            )
        
        # إنشاء الواجهة
        ui = TeachingModeUI(
            segmenter=self.segmenter,
            on_correction=on_correction,
            auto_save_path=Path("./corrections.jsonl")
        )
        
        # تحميل الصفحة
        if self.current_image is not None:
            # حفظ مؤقت
            temp_path = Path("/tmp/omnifile_current.jpg")
            cv2.imwrite(str(temp_path), self.current_image)
            ui.load_page(temp_path)
        
        # تشغيل
        ui.run()
        
        # الحصول على التصحيحات
        self.corrections = ui.get_corrections()
        return self.corrections
    
    def _run_web_ui(self) -> Dict[str, str]:
        """تشغيل واجهة الويب."""
        def on_correction(original, corrected, metadata):
            self.pipeline.process_user_correction(
                original_word=type('Word', (), {
                    'text': original,
                    'confidence': 0,
                    'id': metadata.get('word_id', ''),
                    'bbox': metadata.get('bbox', (0, 0, 0, 0))
                })(),
                corrected_text=corrected,
                word_image=metadata.get('word_image')
            )
        
        ui = WebTeachingInterface(
            segmenter=self.segmenter,
            on_correction=on_correction
        )
        
        # تشغيل الخادم
        import threading
        server_thread = threading.Thread(
            target=ui.run,
            kwargs={'host': '0.0.0.0', 'port': 5000}
        )
        server_thread.daemon = True
        server_thread.start()
        
        print("🌐 فتح الواجهة على: http://localhost:5000")
        print("اضغط Ctrl+C للإنهاء")
        
        try:
            server_thread.join()
        except KeyboardInterrupt:
            pass
        
        self.corrections = ui.corrections
        return self.corrections
    
    def learn_from_corrections(
        self,
        corrections: Optional[Dict[str, str]] = None,
        force: bool = False
    ) -> Dict:
        """
        تدريب النموذج على التصحيحات.
        
        Args:
            corrections: تصحيحات إضافية (اختياري)
            force: إجبار التدريب فوراً
        
        Returns:
            إحصائيات التدريب
        """
        corrections = corrections or self.corrections
        
        if not corrections:
            return {'status': 'no_corrections'}
        
        # تجهيز أزواج التدريب
        training_pairs = []
        for word_id, corrected_text in corrections.items():
            # العثور على الكلمة
            word = self._find_word_by_id(word_id)
            if word and corrected_text != word.text:
                word_image = self.segmenter.extract_word_image(
                    self.current_image,
                    word
                )
                training_pairs.append({
                    'image': word_image,
                    'original_text': word.text,
                    'corrected_text': corrected_text,
                    'confidence_before': word.confidence
                })
        
        # إضافة للمتعلم
        for pair in training_pairs:
            self.learner.add_correction(pair)
        
        # تدريب فوري إذا كان مطلوباً
        if force:
            return self.learner.learn_from_corrections(
                corrections=training_pairs,
                epochs=5
            )
        
        return {
            'status': 'queued',
            'pairs_added': len(training_pairs),
            'pending_training': len(self.pipeline.pending_corrections)
        }
    
    def render_with_layout(
        self,
        corrections: Optional[Dict[str, str]] = None,
        format: str = "html",
        output_path: Optional[Path] = None,
        preserve_graphics: bool = True
    ) -> Path:
        """
        إنتاج المستند النهائي مع الحفاظ على التخطيط.
        
        Args:
            corrections: تصحيحات للتطبيق
            format: html, docx, pdf
            output_path: مسار الحفظ
            preserve_graphics: الحفاظ على الرسومات
        
        Returns:
            مسار الملف المنتج
        """
        if self.current_layout is None:
            raise ValueError("No layout loaded. Call process_page first.")
        
        corrections = corrections or self.corrections
        
        # تحديد المسار
        if output_path is None:
            output_path = Path(f"./output.{format}")
        
        # التصيير
        if format == "html":
            self.renderer.render(
                layout=self.current_layout,
                original_image=self.current_image if preserve_graphics else None,
                corrections=corrections,
                output_path=output_path
            )
        
        elif format in ["docx", "pdf"]:
            self.renderer.render_with_layout_preservation(
                layout=self.current_layout,
                output_path=output_path,
                format=format
            )
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        print(f"✅ تم الإنتاج: {output_path}")
        return output_path
    
    def render_flowchart(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        output_path: Path,
        interactive: bool = True
    ) -> Path:
        """
        رسم مخطط تدفق من البيانات المكتشفة.
        
        Args:
            nodes: [{'id', 'type', 'text', ...}]
            edges: [{'source', 'target', 'label'}]
            output_path: مسار الحفظ
            interactive: تفاعلي أم لا
        
        Returns:
            مسار الملف
        """
        renderer = FlowchartRenderer()
        
        # إضافة العقد
        for node_data in nodes:
            node = FlowchartNode(
                id=node_data['id'],
                node_type=node_data.get('type', 'process'),
                text=node_data.get('text', ''),
                x=node_data.get('x', 0),
                y=node_data.get('y', 0)
            )
            renderer.add_node(node)
        
        # إضافة الوصلات
        for edge_data in edges:
            edge = FlowchartEdge(
                source=edge_data['source'],
                target=edge_data['target'],
                label=edge_data.get('label', ''),
                style=edge_data.get('style', 'solid')
            )
            renderer.add_edge(edge)
        
        # التصيير
        if interactive:
            renderer.render_interactive_html(output_path.with_suffix('.html'))
        
        renderer.render(output_path.with_suffix('.svg'))
        
        return output_path
    
    def render_chart(
        self,
        chart_type: str,
        data: List[Dict],
        output_path: Path,
        title: str = ""
    ) -> Path:
        """
        رسم مخطط بياني.
        
        Args:
            chart_type: bar, pie, line
            data: بيانات المخطط
            output_path: مسار الحفظ
            title: عنوان المخطط
        
        Returns:
            مسار الملف
        """
        renderer = ChartRenderer()
        
        if chart_type == 'bar':
            svg = renderer.render_bar_chart(data, title)
        elif chart_type == 'pie':
            svg = renderer.render_pie_chart(data, title)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # حفظ
        output_path.write_text(svg, encoding='utf-8')
        return output_path
    
    def export_training_data(
        self,
        output_dir: Path,
        split_ratio: float = 0.8
    ) -> Dict[str, Path]:
        """
        تصدير بيانات التدريب من التصحيحات المتراكمة.
        
        Args:
            output_dir: مجلد الإخراج
            split_ratio: نسبة التقسيم train/val
        
        Returns:
            مسارات ملفات التدريب
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # جمع جميع أزواج التدريب
        all_pairs = []
        
        # من الذاكرة
        for item in self.learner.memory:
            all_pairs.append(item)
        
        # من التصحيحات الحالية
        for word_id, corrected in self.corrections.items():
            word = self._find_word_by_id(word_id)
            if word and corrected != word.text:
                word_image = self.segmenter.extract_word_image(
                    self.current_image,
                    word
                )
                all_pairs.append({
                    'image': word_image,
                    'original_text': word.text,
                    'corrected_text': corrected
                })
        
        # خلط وتقسيم
        import random
        random.shuffle(all_pairs)
        
        split_idx = int(len(all_pairs) * split_ratio)
        train_pairs = all_pairs[:split_idx]
        val_pairs = all_pairs[split_idx:]
        
        # حفظ
        def save_pairs(pairs, name):
            pair_dir = output_dir / name
            pair_dir.mkdir(exist_ok=True)
            
            labels = []
            for i, pair in enumerate(pairs):
                # حفظ الصورة
                img_path = pair_dir / f"word_{i:06d}.png"
                cv2.imwrite(str(img_path), pair['image'])
                
                labels.append({
                    'image': str(img_path),
                    'text': pair['corrected_text'],
                    'original': pair.get('original_text', '')
                })
            
            # حفظ التسميات
            with open(pair_dir / 'labels.json', 'w', encoding='utf-8') as f:
                json.dump(labels, f, ensure_ascii=False, indent=2)
            
            return pair_dir
        
        train_dir = save_pairs(train_pairs, 'train')
        val_dir = save_pairs(val_pairs, 'val') if val_pairs else None
        
        return {
            'train': train_dir,
            'val': val_dir,
            'total_pairs': len(all_pairs)
        }
    
    def get_stats(self) -> Dict:
        """الحصول على إحصائيات النظام."""
        return {
            'learning': self.pipeline.get_learning_stats(),
            'current_page': {
                'words': len(self._all_words()) if self.current_layout else 0,
                'paragraphs': len(self.current_layout.paragraphs) if self.current_layout else 0,
                'tables': len(self.current_layout.tables) if self.current_layout else 0,
                'graphics': len(self.current_layout.graphics) if self.current_layout else 0
            },
            'corrections': {
                'total': len(self.corrections),
                'by_page': len(set(w.line_id for w in self._all_words() if w.id in self.corrections))
            }
        }
    
    def _find_word_by_id(self, word_id: str) -> Optional[WordBox]:
        """العثور على كلمة بواسطة المعرف."""
        if not self.current_layout:
            return None
        
        for para in self.current_layout.paragraphs:
            for line in para.lines:
                for word in line.words:
                    if word.id == word_id:
                        return word
        
        return None
    
    def _all_words(self) -> List[WordBox]:
        """الحصول على جميع الكلمات."""
        words = []
        if self.current_layout:
            for para in self.current_layout.paragraphs:
                for line in para.lines:
                    words.extend(line.words)
        return words


# =============================================================================
# دوال مساعدة سهلة الاستخدام
# =============================================================================

def process_and_learn(
    image_path: Union[str, Path],
    model_path: str = "microsoft/trocr-large-handwritten",
    interactive: bool = True
) -> Dict:
    """
    معالجة صفحة والتعلم منها بسهولة.
    
    Args:
        image_path: مسار الصورة
        model_path: مسار النموذج
        interactive: وضع تفاعلي
    
    Returns:
        نتائج المعالجة والتعلم
    """
    system = InteractiveLearningSystem(
        model_path=model_path,
        learning_mode=interactive
    )
    
    # معالجة
    print("🔍 جاري تحليل الصفحة...")
    layout = system.process_page(image_path)
    print(f"✅ تم العثور على {len(system._all_words())} كلمة")
    
    # وضع التعليم
    if interactive:
        print("🎯 بدء وضع التعليم...")
        corrections = system.teaching_mode()
        print(f"✅ تم تصحيح {len(corrections)} كلمة")
        
        # تدريب
        if len(corrections) > 5:
            print("🧠 جاري التعلم...")
            stats = system.learn_from_corrections(force=True)
            print(f"✅ اكتمل التدريب: {stats}")
    
    # إنتاج الناتج
    print("📄 جاري إنتاج المستند...")
    output = system.render_with_layout(
        format="html",
        preserve_graphics=True
    )
    
    return {
        'layout': layout,
        'corrections': system.corrections,
        'output_path': output,
        'stats': system.get_stats()
    }


def batch_process(
    image_paths: List[Path],
    output_dir: Path,
    model_path: str = "microsoft/trocr-large-handwritten"
) -> List[Dict]:
    """
    معالجة دفعية لمجموعة صفحات.
    
    Args:
        image_paths: قائمة المسارات
        output_dir: مجلد الإخراج
        model_path: مسار النموذج
    
    Returns:
        نتائج المعالجة
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    system = InteractiveLearningSystem(model_path=model_path)
    results = []
    
    for i, path in enumerate(image_paths):
        print(f"\n📄 معالجة {i+1}/{len(image_paths)}: {path.name}")
        
        result = process_and_learn(path, model_path, interactive=False)
        
        # نقل الناتج
        final_path = output_dir / f"page_{i:03d}.html"
        result['output_path'].rename(final_path)
        result['output_path'] = final_path
        
        results.append(result)
    
    # تصدير بيانات التدريب المتراكمة
    train_data = system.export_training_data(output_dir / "training_data")
    print(f"\n📊 تم تصدير بيانات التدريب: {train_data}")
    
    return results
