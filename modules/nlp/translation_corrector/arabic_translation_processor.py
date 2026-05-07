"""
🚀 نظام معالجة الترجمات العربية المتكامل
Arabic Translation Processing System - Unified Version

المطور: د. عبد المالك الحسيني
الإصدار: 2.0.0
الترخيص: MIT

نظام متكامل يجمع بين معالجة مجموعات البيانات الكبيرة وتصحيح الترجمات الفردية
"""

import os
import re
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

import gradio as gr
import pandas as pd
from datasets import load_dataset, Dataset
from huggingface_hub import HfApi
import httpx

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ قواعد المعالجة المتقدمة ============

class TranslationRule:
    """تمثيل قاعدة تصحيح واحدة"""
    
    def __init__(self, rule_id: str, category: str, english_pattern: str,
                 wrong_arabic: str, correct_arabic: str, 
                 description: str, priority: int = 2):
        self.rule_id = rule_id
        self.category = category
        self.english_pattern = english_pattern.lower()
        self.wrong_arabic = wrong_arabic
        self.correct_arabic = correct_arabic
        self.description = description
        self.priority = priority
        
    def applies_to(self, en_text: str, ar_text: str) -> bool:
        """فحص ما إذا كانت القاعدة تنطبق"""
        return (self.english_pattern in en_text.lower() and 
                self.wrong_arabic in ar_text)
    
    def apply(self, ar_text: str) -> str:
        """تطبيق القاعدة"""
        return ar_text.replace(self.wrong_arabic, self.correct_arabic)


class ArabicTranslationProcessor:
    """معالج متقدم للترجمات العربية"""
    
    def __init__(self, rules_file: Optional[str] = None):
        """تهيئة المعالج"""
        self.rules: List[TranslationRule] = []
        self.compiled_patterns = self._compile_regex_patterns()
        self.statistics = {
            "total_processed": 0,
            "total_corrections": 0,
            "rules_applied": {}
        }
        
        if rules_file and Path(rules_file).exists():
            self.load_rules_from_file(rules_file)
        else:
            self._initialize_default_rules()
    
    def _compile_regex_patterns(self) -> Dict:
        """تجميع الأنماط التعبيرية المنتظمة"""
        return {
            # علامات الترقيم والروابط
            'comma_spacing': re.compile(r'\s*,\s*'),
            'arabic_comma': re.compile(r'،\s*'),
            'waw_conjunction': re.compile(r'([،؛])\s*و'),
            
            # الأرقام
            'number_spacing': re.compile(r'(\d)\s+(\d)'),
            'number_comma': re.compile(r'(\d+),(\d+)'),
            
            # المبني للمجهول
            'passive_by': re.compile(r'\b(was|were|been)\s+(\w+)\s+by\s+', re.I),
            'passive_simple': re.compile(r'\b(was|were|is|are|been)\s+(\w+ed)\b', re.I),
            
            # التنوين
            'tanween_alif': re.compile(r'([بتثجحخدذرزسشصضطظعغفقكلمنهي])ا(?!\w)'),
            
            # حروف زائدة
            'redundant_ba': re.compile(r'بواسطة\s+'),
            'redundant_waw': re.compile(r'(رغم|خاصة|سبق)\s+وأن'),
            
            # تكرار الكلمات
            'word_repeat': re.compile(r'\b(\w+)\s+\1\b'),
            
            # المسافات الزائدة
            'extra_spaces': re.compile(r'\s{2,}'),
            'space_before_punct': re.compile(r'\s+([،؛؟!.])'),
        }
    
    def _initialize_default_rules(self):
        """تحميل القواعد الافتراضية"""
        default_rules = [
            # قواعد تركيبية (Structural)
            TranslationRule(
                "STRUCT_001", "structural",
                "no smoking", "ممنوع التدخين", "التدخين ممنوع",
                "تقديم المبتدأ على الخبر في الجملة الاسمية", 1
            ),
            TranslationRule(
                "STRUCT_002", "structural",
                "no parking", "ممنوع الوقوف", "الوقوف ممنوع",
                "تقديم المبتدأ على الخبر", 1
            ),
            
            # قواعد نحوية (Grammatical)
            TranslationRule(
                "GRAM_001", "grammatical",
                "by", "بواسطة", "",
                "حذف 'بواسطة' المترجمة حرفياً من by", 2
            ),
            TranslationRule(
                "GRAM_002", "grammatical",
                "met with", "التقى ب", "لقي",
                "تصحيح تعدية الفعل 'لقي'", 2
            ),
            TranslationRule(
                "GRAM_003", "grammatical",
                "and that", "وأن", "أن",
                "حذف الواو الزائدة", 2
            ),
            
            # قواعد معجمية (Lexical)
            TranslationRule(
                "LEX_001", "lexical",
                "ladies and gentlemen", "السيدات والسادة", "السادة والسيدات",
                "تقديم المذكر على المؤنث في العربية", 1
            ),
            TranslationRule(
                "LEX_002", "lexical",
                "computer", "كمبيوتر", "حاسوب",
                "استخدام المصطلح العربي الفصيح", 1
            ),
            TranslationRule(
                "LEX_003", "lexical",
                "internet", "إنترنت", "الشابكة",
                "استخدام المصطلح العربي", 2
            ),
            TranslationRule(
                "LEX_004", "lexical",
                "mobile", "موبايل", "هاتف محمول",
                "استخدام المصطلح العربي", 2
            ),
            
            # قواعد أسلوبية (Stylistic)
            TranslationRule(
                "STYLE_001", "stylistic",
                "played a role", "لعب دوراً", "قام بدور",
                "استخدام الفعل المناسب", 2
            ),
            TranslationRule(
                "STYLE_002", "stylistic",
                "covered the event", "غطى الحدث", "تابع الحدث",
                "التعبير الإعلامي المناسب", 2
            ),
            TranslationRule(
                "STYLE_003", "stylistic",
                "took place", "أخذ مكاناً", "وقع / حدث",
                "استخدام الفعل العربي الصحيح", 2
            ),
            
            # قواعد ثقافية (Cultural)
            TranslationRule(
                "CULT_001", "cultural",
                "god", "جود", "الله",
                "استخدام اللفظ الإسلامي المناسب", 1
            ),
        ]
        
        self.rules = default_rules
        logger.info(f"تم تحميل {len(self.rules)} قاعدة افتراضية")
    
    def load_rules_from_file(self, filepath: str):
        """تحميل القواعد من ملف JSON"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            self.rules = []
            for rule_dict in rules_data:
                rule = TranslationRule(
                    rule_id=rule_dict.get('rule_id', f"CUSTOM_{len(self.rules)}"),
                    category=rule_dict['category'],
                    english_pattern=rule_dict['english_pattern'],
                    wrong_arabic=rule_dict['wrong_arabic'],
                    correct_arabic=rule_dict['correct_arabic'],
                    description=rule_dict.get('rule_description', rule_dict.get('description', '')),
                    priority=rule_dict.get('priority', 2)
                )
                self.rules.append(rule)
            
            logger.info(f"تم تحميل {len(self.rules)} قاعدة من {filepath}")
        except Exception as e:
            logger.error(f"خطأ في تحميل القواعد: {e}")
            self._initialize_default_rules()
    
    def apply_regex_corrections(self, text: str) -> Tuple[str, List[str]]:
        """تطبيق التصحيحات بالتعبيرات المنتظمة"""
        corrected = text
        applied = []
        
        # 1. إصلاح المسافات والفواصل
        temp = self.compiled_patterns['comma_spacing'].sub('، ', corrected)
        if temp != corrected:
            corrected = temp
            applied.append("REGEX_COMMA")
        
        # 2. إصلاح الأرقام
        temp = self.compiled_patterns['number_spacing'].sub(r'\1\2', corrected)
        if temp != corrected:
            corrected = temp
            applied.append("REGEX_NUM")
        
        # 3. حذف الحروف الزائدة
        temp = self.compiled_patterns['redundant_waw'].sub(r'\1 أن', corrected)
        if temp != corrected:
            corrected = temp
            applied.append("REGEX_WAW")
        
        # 4. إصلاح المسافات الزائدة
        corrected = self.compiled_patterns['extra_spaces'].sub(' ', corrected)
        corrected = self.compiled_patterns['space_before_punct'].sub(r'\1', corrected)
        
        return corrected.strip(), applied
    
    def process_translation(self, english_text: str, arabic_text: str,
                          apply_rules: bool = True,
                          apply_regex: bool = True) -> Dict:
        """
        معالجة ترجمة واحدة
        
        Args:
            english_text: النص الإنجليزي الأصلي
            arabic_text: الترجمة العربية
            apply_rules: تطبيق القواعد المحددة
            apply_regex: تطبيق التصحيحات بالتعبيرات المنتظمة
            
        Returns:
            قاموس يحتوي على النتائج والإحصائيات
        """
        if not arabic_text:
            return {
                "original": "",
                "corrected": "",
                "corrections": [],
                "rule_ids": []
            }
        
        corrected_text = arabic_text
        applied_corrections = []
        rule_ids = []
        
        # 1. تطبيق القواعد المحددة
        if apply_rules:
            sorted_rules = sorted(self.rules, key=lambda r: r.priority)
            
            for rule in sorted_rules:
                if rule.applies_to(english_text, corrected_text):
                    old_text = corrected_text
                    corrected_text = rule.apply(corrected_text)
                    
                    if old_text != corrected_text:
                        applied_corrections.append({
                            "rule_id": rule.rule_id,
                            "category": rule.category,
                            "description": rule.description,
                            "original": rule.wrong_arabic,
                            "corrected": rule.correct_arabic
                        })
                        rule_ids.append(rule.rule_id)
                        
                        # تحديث الإحصائيات
                        if rule.rule_id not in self.statistics["rules_applied"]:
                            self.statistics["rules_applied"][rule.rule_id] = 0
                        self.statistics["rules_applied"][rule.rule_id] += 1
        
        # 2. تطبيق التصحيحات بالتعبيرات المنتظمة
        if apply_regex:
            corrected_text, regex_ids = self.apply_regex_corrections(corrected_text)
            rule_ids.extend(regex_ids)
        
        # تحديث الإحصائيات العامة
        self.statistics["total_processed"] += 1
        if applied_corrections or rule_ids:
            self.statistics["total_corrections"] += 1
        
        return {
            "original": arabic_text,
            "corrected": corrected_text,
            "corrections": applied_corrections,
            "rule_ids": rule_ids,
            "improved": len(applied_corrections) > 0 or len(rule_ids) > 0
        }
    
    def get_statistics(self) -> Dict:
        """الحصول على إحصائيات المعالجة"""
        return self.statistics.copy()
    
    def reset_statistics(self):
        """إعادة تعيين الإحصائيات"""
        self.statistics = {
            "total_processed": 0,
            "total_corrections": 0,
            "rules_applied": {}
        }


# ============ معالجة مجموعات البيانات ============

async def preview_dataset(dataset_id: str, limit: int = 10) -> Tuple[pd.DataFrame, str]:
    """معاينة مجموعة بيانات من Hugging Face"""
    try:
        # محاولة استخدام Datasets Server API
        url = "https://datasets-server.huggingface.co/rows"
        params = {
            "dataset": dataset_id,
            "config": "default",
            "split": "train",
            "offset": 0,
            "length": min(limit, 100)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                rows = data.get("rows", [])
                
                if rows:
                    df = pd.DataFrame([r["row"] for r in rows[:limit]])
                    return df, f"✅ تم تحميل {len(df)} صف من {dataset_id}"
                else:
                    return pd.DataFrame(), "⚠️ لا توجد بيانات"
            else:
                # الطريقة البديلة: التحميل المباشر
                ds = load_dataset(dataset_id, split="train", streaming=True)
                rows = []
                for i, row in enumerate(ds):
                    if i >= limit:
                        break
                    rows.append(row)
                
                df = pd.DataFrame(rows)
                return df, f"✅ تم تحميل {len(df)} صف"
                
    except Exception as e:
        logger.error(f"خطأ في معاينة البيانات: {e}")
        return pd.DataFrame(), f"❌ خطأ: {str(e)}"


def process_dataset(
    dataset_id: str,
    save_repo: str,
    processor: ArabicTranslationProcessor,
    enable_rules: bool = True,
    enable_regex: bool = True,
    batch_size: int = 64,
    hf_token: Optional[str] = None,
    progress_callback=None
) -> Tuple[str, Optional[pd.DataFrame], Optional[str]]:
    """
    معالجة مجموعة بيانات كاملة
    
    Args:
        dataset_id: معرف مجموعة البيانات
        save_repo: مستودع الحفظ
        processor: معالج الترجمات
        enable_rules: تفعيل القواعد المحددة
        enable_regex: تفعيل التصحيحات بالتعبيرات المنتظمة
        batch_size: حجم الدفعة
        hf_token: توكن Hugging Face
        progress_callback: دالة callback للتقدم
        
    Returns:
        (رسالة الحالة، جدول عينة النتائج، رابط المستودع)
    """
    try:
        if progress_callback:
            progress_callback(0.0, "جاري التحميل...")
        
        # التحقق من التوكن
        if not hf_token:
            hf_token = os.environ.get("HF_TOKEN")
        
        if not hf_token:
            return "❌ HF_TOKEN غير موجود في المتغيرات البيئية", None, None
        
        # تحميل البيانات
        logger.info(f"تحميل مجموعة البيانات: {dataset_id}")
        ds = load_dataset(dataset_id, token=hf_token)
        
        # تحويل إلى DataFrame
        if isinstance(ds, dict):
            df = pd.concat([ds[k].to_pandas() for k in ds], ignore_index=True)
        else:
            df = ds.to_pandas()
        
        logger.info(f"تم تحميل {len(df)} صف")
        
        if progress_callback:
            progress_callback(0.2, f"تم تحميل {len(df):,} صف")
        
        # اكتشاف الأعمدة
        en_col = None
        ar_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if not en_col and any(x in col_lower for x in ['en', 'english', 'source']):
                en_col = col
            if not ar_col and any(x in col_lower for x in ['ar', 'arabic', 'target']):
                ar_col = col
        
        if not en_col:
            en_col = df.columns[0]
        if not ar_col and len(df.columns) > 1:
            ar_col = df.columns[1]
        
        logger.info(f"الأعمدة المكتشفة - إنجليزي: {en_col}, عربي: {ar_col}")
        
        if progress_callback:
            progress_callback(0.3, "جاري المعالجة...")
        
        # معالجة الصفوف
        processed_rows = []
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                en_text = str(row.get(en_col, "")).strip()
                ar_text = str(row.get(ar_col, "")).strip() if ar_col else ""
                
                # معالجة الترجمة
                result = processor.process_translation(
                    en_text, ar_text,
                    apply_rules=enable_rules,
                    apply_regex=enable_regex
                )
                
                processed_rows.append({
                    "english": en_text,
                    "arabic_original": ar_text,
                    "arabic_corrected": result["corrected"],
                    "rule_ids": ",".join(result["rule_ids"]),
                    "corrections_count": len(result["corrections"]),
                    "improved": result["improved"],
                    "processed_at": datetime.now().isoformat()
                })
            
            # تحديث التقدم
            current_progress = 0.3 + (i / total) * 0.6
            if progress_callback:
                progress_callback(
                    current_progress,
                    f"معالجة {i:,} / {total:,}"
                )
        
        if progress_callback:
            progress_callback(0.9, "جاري الحفظ...")
        
        # حفظ النتائج
        result_df = pd.DataFrame(processed_rows)
        result_ds = Dataset.from_pandas(result_df)
        
        logger.info(f"حفظ النتائج إلى: {save_repo}")
        result_ds.push_to_hub(save_repo, token=hf_token)
        
        if progress_callback:
            progress_callback(1.0, "تم!")
        
        # إحصائيات
        stats = processor.get_statistics()
        improved_count = result_df['improved'].sum()
        
        stats_text = f"""
✅ **تم بنجاح!**

📊 **الإحصائيات:**
- إجمالي الجمل: **{len(processed_rows):,}**
- الجمل المحسَّنة: **{improved_count:,}** ({improved_count/len(processed_rows)*100:.1f}%)
- إجمالي التصحيحات: **{stats['total_corrections']:,}**

📋 **القواعد الأكثر استخداماً:**
"""
        
        # عرض أفضل 5 قواعد
        top_rules = sorted(
            stats['rules_applied'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for rule_id, count in top_rules:
            stats_text += f"\n  - **{rule_id}**: {count:,} مرة"
        
        stats_text += f"\n\n💾 **المستودع:** `{save_repo}`"
        
        # عينة من النتائج
        sample_df = result_df[['english', 'arabic_original', 'arabic_corrected', 'rule_ids']].head(10)
        
        repo_link = f"https://huggingface.co/datasets/{save_repo}"
        
        return stats_text, sample_df, repo_link
        
    except Exception as e:
        logger.error(f"خطأ في المعالجة: {e}", exc_info=True)
        return f"❌ خطأ: {str(e)}", None, None


# ============ واجهة Gradio ============

def create_gradio_interface():
    """إنشاء واجهة Gradio المتقدمة"""
    
    # تهيئة المعالج
    processor = ArabicTranslationProcessor()
    
    with gr.Blocks(title="نظام معالجة الترجمات العربية") as app:
        
        # الترويسة
        gr.Markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='color: #2563eb; font-size: 2.5em;'>🚀 نظام معالجة الترجمات العربية</h1>
            <p style='font-size: 1.2em; color: #64748b;'>
                نظام متكامل لمعالجة وتحسين الترجمات العربية باستخدام قواعد لغوية ذكية
            </p>
            <p style='color: #94a3b8;'>
                <strong>الإصدار 2.0.0</strong> | المطور: د. عبد المالك الحسيني | مفتوح المصدر
            </p>
        </div>
        """)
        
        gr.Markdown("---")
        
        # التبويبات الرئيسية
        with gr.Tabs():
            
            # ========== تبويب 1: معالجة ترجمة واحدة ==========
            with gr.Tab("📝 تصحيح ترجمة", id="single"):
                gr.Markdown("### تصحيح ترجمة واحدة")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        en_input = gr.Textbox(
                            label="📄 النص الإنجليزي",
                            placeholder="Enter English text here...",
                            lines=5
                        )
                        
                        ar_input = gr.Textbox(
                            label="📄 الترجمة العربية",
                            placeholder="أدخل الترجمة العربية هنا...",
                            lines=5
                        )
                        
                        with gr.Row():
                            apply_rules_check = gr.Checkbox(
                                label="تطبيق القواعد المحددة",
                                value=True
                            )
                            apply_regex_check = gr.Checkbox(
                                label="تطبيق التصحيحات التلقائية",
                                value=True
                            )
                        
                        correct_btn = gr.Button(
                            "✅ تصحيح الترجمة",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column(scale=1):
                        ar_output = gr.Textbox(
                            label="✨ الترجمة المصححة",
                            lines=5,
                            interactive=False
                        )
                        
                        corrections_output = gr.JSON(
                            label="📋 التصحيحات المطبقة"
                        )
                        
                        stats_single = gr.Markdown(label="📊 الإحصائيات")
                
                def correct_single(en, ar, rules, regex):
                    result = processor.process_translation(
                        en, ar, apply_rules=rules, apply_regex=regex
                    )
                    
                    stats_md = f"""
**النتيجة:**
- تم تطبيق **{len(result['corrections'])}** تصحيح
- عدد القواعد: **{len(result['rule_ids'])}**
- حالة التحسين: **{'✅ نعم' if result['improved'] else 'ℹ️ لا تحتاج تحسين'}**
"""
                    
                    return result['corrected'], result['corrections'], stats_md
                
                correct_btn.click(
                    fn=correct_single,
                    inputs=[en_input, ar_input, apply_rules_check, apply_regex_check],
                    outputs=[ar_output, corrections_output, stats_single]
                )
            
            # ========== تبويب 2: معالجة مجموعة بيانات ==========
            with gr.Tab("🗂️ معالجة مجموعة بيانات", id="batch"):
                gr.Markdown("### معالجة مجموعة بيانات كاملة من Hugging Face")
                
                with gr.Row():
                    with gr.Column():
                        dataset_input = gr.Textbox(
                            label="🔖 معرف مجموعة البيانات",
                            placeholder="مثال: DrAbdulmalek/Translated_Books",
                            info="معرف المجموعة على Hugging Face Hub"
                        )
                        
                        save_repo_input = gr.Textbox(
                            label="💾 مستودع الحفظ",
                            placeholder="مثال: DrAbdulmalek/Processed_Translations",
                            info="اسم المستودع لحفظ النتائج"
                        )
                        
                        with gr.Row():
                            enable_rules_batch = gr.Checkbox(
                                label="تطبيق القواعد المحددة",
                                value=True
                            )
                            enable_regex_batch = gr.Checkbox(
                                label="تطبيق التصحيحات التلقائية",
                                value=True
                            )
                        
                        batch_size_slider = gr.Slider(
                            label="حجم الدفعة",
                            minimum=10,
                            maximum=500,
                            value=64,
                            step=10,
                            info="عدد الصفوف في كل دفعة"
                        )
                        
                        process_btn = gr.Button(
                            "🚀 بدء المعالجة",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column():
                        stats_batch = gr.Markdown(label="📊 الإحصائيات")
                        repo_link = gr.Textbox(
                            label="🔗 رابط المستودع",
                            interactive=False
                        )
                
                sample_output = gr.DataFrame(
                    label="📄 عينة من النتائج (أول 10 صفوف)",
                    wrap=True,
                    max_height=400
                )
                
                def process_with_progress(dataset_id, save_repo, rules, regex, batch_size, progress=gr.Progress()):
                    return process_dataset(
                        dataset_id, save_repo, processor,
                        enable_rules=rules,
                        enable_regex=regex,
                        batch_size=int(batch_size),
                        progress_callback=progress
                    )
                
                process_btn.click(
                    fn=process_with_progress,
                    inputs=[
                        dataset_input,
                        save_repo_input,
                        enable_rules_batch,
                        enable_regex_batch,
                        batch_size_slider
                    ],
                    outputs=[stats_batch, sample_output, repo_link]
                )
            
            # ========== تبويب 3: معاينة البيانات ==========
            with gr.Tab("👁️ معاينة البيانات", id="preview"):
                gr.Markdown("### معاينة مجموعة بيانات قبل المعالجة")
                
                with gr.Row():
                    preview_dataset_input = gr.Textbox(
                        label="🔖 معرف مجموعة البيانات",
                        placeholder="DrAbdulmalek/Translated_Books"
                    )
                    preview_limit = gr.Slider(
                        label="عدد الصفوف",
                        minimum=5,
                        maximum=100,
                        value=10,
                        step=5
                    )
                
                preview_btn = gr.Button("🔍 معاينة", variant="secondary")
                
                preview_status = gr.Textbox(label="📊 الحالة")
                preview_output = gr.DataFrame(
                    label="📄 البيانات",
                    wrap=True,
                    max_height=500
                )
                
                async def preview_async(dataset_id, limit):
                    return await preview_dataset(dataset_id, limit)
                
                preview_btn.click(
                    fn=lambda d, l: asyncio.run(preview_async(d, l)),
                    inputs=[preview_dataset_input, preview_limit],
                    outputs=[preview_output, preview_status]
                )
            
            # ========== تبويب 4: إدارة القواعد ==========
            with gr.Tab("⚙️ إدارة القواعد", id="rules"):
                gr.Markdown("### عرض وإدارة قواعد التصحيح")
                
                with gr.Tabs():
                    with gr.Tab("📚 عرض القواعد"):
                        rules_list = gr.DataFrame(
                            value=pd.DataFrame([
                                {
                                    "المعرف": r.rule_id,
                                    "الفئة": r.category,
                                    "النمط الإنجليزي": r.english_pattern,
                                    "الخطأ": r.wrong_arabic,
                                    "الصواب": r.correct_arabic,
                                    "الوصف": r.description,
                                    "الأولوية": r.priority
                                }
                                for r in processor.rules
                            ]),
                            label=f"القواعس المتاحة ({len(processor.rules)} قاعدة)",
                            wrap=True,
                            max_height=600
                        )
                    
                    with gr.Tab("📊 الإحصائيات"):
                        stats_rules = gr.JSON(
                            value=processor.get_statistics(),
                            label="إحصائيات استخدام القواعد"
                        )
                        
                        reset_stats_btn = gr.Button("🔄 إعادة تعيين الإحصائيات")
                        
                        def reset_stats():
                            processor.reset_statistics()
                            return processor.get_statistics()
                        
                        reset_stats_btn.click(
                            fn=reset_stats,
                            outputs=stats_rules
                        )
            
            # ========== تبويب 5: المساعدة والتوثيق ==========
            with gr.Tab("📖 التوثيق", id="docs"):
                gr.Markdown("""
                ## 📚 دليل الاستخدام الشامل
                
                ### 🎯 نظرة عامة
                
                **نظام معالجة الترجمات العربية** هو أداة متقدمة لتحسين جودة الترجمات الآلية من الإنجليزية للعربية.
                يعتمد النظام على:
                - **قواعد لغوية محددة** (Rule-based)
                - **تعبيرات منتظمة متقدمة** (Regex-based)
                - **معالجة دفعية** للمجموعات الكبيرة
                
                ---
                
                ### 1️⃣ تصحيح ترجمة واحدة
                
                **الخطوات:**
                1. أدخل النص الإنجليزي الأصلي
                2. أدخل الترجمة العربية المراد تصحيحها
                3. اختر نوع التصحيحات المطلوبة
                4. اضغط "تصحيح الترجمة"
                
                **مثال:**
                ```
                إنجليزي: The meeting was cancelled by the manager
                عربي (خطأ): تم إلغاء الاجتماع بواسطة المدير
                عربي (صحيح): ألغى المديرُ الاجتماعَ
                ```
                
                ---
                
                ### 2️⃣ معالجة مجموعة بيانات
                
                **المتطلبات:**
                - حساب Hugging Face
                - توكن وصول (HF_TOKEN)
                - مجموعة بيانات موجودة
                
                **الخطوات:**
                1. أدخل معرف مجموعة البيانات (مثل: `username/dataset-name`)
                2. أدخل اسم المستودع لحفظ النتائج
                3. اختر الإعدادات المناسبة
                4. اضغط "بدء المعالجة"
                
                **تنسيق البيانات المتوقع:**
                ```json
                {
                  "en": "English text here",
                  "ar": "النص العربي هنا"
                }
                ```
                
                الأعمدة المدعومة:
                - **للإنجليزي**: `en`, `english`, `source`, `text_en`
                - **للعربي**: `ar`, `arabic`, `target`, `text_ar`
                
                ---
                
                ### 3️⃣ القواعد المطبقة
                
                #### أ) قواعد تركيبية (Structural)
                - تصحيح ترتيب الجملة العربية
                - مثال: "ممنوع التدخين" → "التدخين ممنوع"
                
                #### ب) قواعد نحوية (Grammatical)
                - حذف الحروف الزائدة ("بواسطة", "وأن")
                - تصحيح تعدية الأفعال
                - إصلاح المبني للمجهول
                
                #### ج) قواعد معجمية (Lexical)
                - استبدال المصطلحات الدخيلة بالعربية الفصيحة
                - مثال: "كمبيوتر" → "حاسوب"
                
                #### د) قواعد أسلوبية (Stylistic)
                - تحسين الصياغة والأسلوب
                - مثال: "لعب دوراً" → "قام بدور"
                
                #### هـ) قواعد ثقافية (Cultural)
                - مراعاة السياق الثقافي والديني
                
                ---
                
                ### 4️⃣ إعداد HF_TOKEN
                
                **لاستخدام النظام على Hugging Face Spaces:**
                
                1. اذهب إلى **Settings** → **Variables and secrets**
                2. أضف Secret جديد:
                   - **Name**: `HF_TOKEN`
                   - **Value**: [توكن الوصول من حسابك](https://huggingface.co/settings/tokens)
                3. احفظ التغييرات
                
                **للاستخدام المحلي:**
                ```bash
                export HF_TOKEN="your_token_here"
                ```
                
                ---
                
                ### 5️⃣ نصائح وأفضل الممارسات
                
                ✅ **افعل:**
                - ابدأ باختبار المعالجة على مجموعة صغيرة أولاً
                - راجع العينة من النتائج قبل الحفظ النهائي
                - استخدم أسماء واضحة لمستودعات الحفظ
                - احتفظ بنسخة من البيانات الأصلية
                
                ❌ **لا تفعل:**
                - لا تعالج مجموعات ضخمة دون تجربة أولية
                - لا تستخدم أسماء مستودعات موجودة (سيتم الكتابة فوقها)
                - لا تشارك HF_TOKEN مع أحد
                
                ---
                
                ### 6️⃣ الأسئلة الشائعة
                
                **س: ما هي المدة المتوقعة للمعالجة؟**
                ج: تعتمد على حجم المجموعة. تقريباً:
                - 1000 جملة: ~2-3 دقائق
                - 10000 جملة: ~15-20 دقيقة
                - 100000 جملة: ~2-3 ساعات
                
                **س: هل يمكن إضافة قواعد جديدة؟**
                ج: نعم! يمكن تحرير ملف القواعد JSON أو تطوير النظام محلياً.
                
                **س: هل النظام مجاني؟**
                ج: نعم، مفتوح المصدر تحت ترخيص MIT.
                
                ---
                
                ### 🔗 روابط مفيدة
                
                - [📖 الكود المصدري](https://github.com/DrAbdulmalek/arabic-translation-unified)
                - [🤗 Hugging Face Hub](https://huggingface.co)
                - [📚 توثيق Datasets](https://huggingface.co/docs/datasets)
                - [🔑 إنشاء توكن وصول](https://huggingface.co/settings/tokens)
                
                ---
                
                ### 📝 الترخيص والاستشهاد
                
                **الترخيص:** MIT License
                
                **الاستشهاد:**
                ```bibtex
                @software{arabic_translation_processor,
                  author = {د. عبد المالك الحسيني},
                  title = {نظام معالجة الترجمات العربية},
                  year = {2024},
                  url = {https://github.com/DrAbdulmalek/arabic-translation-unified}
                }
                ```
                
                ---
                
                ### 📞 الدعم والمساعدة
                
                للحصول على المساعدة أو الإبلاغ عن مشكلة:
                - 🐛 [فتح Issue على GitHub](https://github.com/DrAbdulmalek/arabic-translation-unified/issues)
                - 💬 [منتدى Hugging Face](https://discuss.huggingface.co)
                - 📧 البريد الإلكتروني: support@example.com
                """)
        
        # التذييل
        gr.Markdown("""
        ---
        <div style='text-align: center; padding: 20px; color: #64748b;'>
            <p><strong>نظام معالجة الترجمات العربية</strong> v2.0.0</p>
            <p>تم التطوير بواسطة <strong>د. عبد المالك الحسيني</strong></p>
            <p>مبني على كتاب "أسس الترجمة" | للاستخدام التعليمي والبحثي</p>
            <p style='margin-top: 10px;'>
                <a href='https://github.com/DrAbdulmalek' target='_blank' style='margin: 0 10px;'>GitHub</a> |
                <a href='https://huggingface.co/DrAbdulmalek' target='_blank' style='margin: 0 10px;'>Hugging Face</a> |
                <a href='#' target='_blank' style='margin: 0 10px;'>التوثيق</a>
            </p>
            <p style='margin-top: 10px; font-size: 0.9em;'>
                صُنع بـ ❤️ للغة العربية | MIT License
            </p>
        </div>
        """)
    
    return app


# ============ نقطة البدء ============

if __name__ == "__main__":
    logger.info("بدء تشغيل النظام...")
    
    # إنشاء الواجهة
    app = create_gradio_interface()
    
    # إطلاق التطبيق
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
