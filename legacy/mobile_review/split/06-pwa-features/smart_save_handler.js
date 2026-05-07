// smart_save_handler.js - Smart save with beforeunload protection

/**
 * 💾 SmartSaveHandler: حماية التعديلات من الفقد المفاجئ
 * - حفظ تلقائي مشفر لـ sessionStorage
 * - تنبيه بصري عند وجود تغييرات غير محفوظة
 * - نافذة تأكيد عند محاولة الإغلاق/التحديث
 */
class SmartSaveHandler {
  constructor(cryptoStorage, autoSaveIntervalMs = 30000) {
    this.crypto = cryptoStorage;
    this.hasUnsaved = false;
    this.dirtyBlocks = new Set();
    this.timer = null;
    this.init();
  }

  init() {
    // 1️⃣ تتبع التعديلات في الوقت الفعلي
    document.addEventListener('input', (e) => {
      if (e.target.matches('.text-editor, textarea, [contenteditable]')) {
        const id = e.target.dataset.blockId || 'main_draft';
        this.markDirty(id);
        this.showUnsavedBadge(true);
      }
    });

    // 2️⃣ الحفظ التلقائي المشفر
    this.timer = setInterval(() => this.flushDrafts(), autoSaveIntervalMs);

    // 3️⃣ منع الإغلاق المفاجئ
    window.addEventListener('beforeunload', (e) => {
      if (this.hasUnsaved) {
        this.flushDrafts(true); // حفظ إجباري متزامن
        e.preventDefault();
        e.returnValue = 'لديك تعديلات غير محفوظة. هل تريد المغادرة؟';
      }
    });

    // استعادة المسودات عند التحميل
    this.restoreAllDrafts();
  }

  markDirty(id) { this.dirtyBlocks.add(id); this.hasUnsaved = true; }

  showUnsavedBadge(show) {
    const badge = document.getElementById('unsaved-indicator');
    if (badge) badge.style.display = show ? 'block' : 'none';
  }

  async flushDrafts(force = false) {
    if (!this.hasUnsaved && !force) return;
    const ids = Array.from(this.dirtyBlocks);
    for (const id of ids) {
      const el = document.querySelector(`[data-block-id="${id}"]`);
      if (el) {
        await this.crypto.store(`draft_${id}`, { text: el.value, updated: Date.now() });
      }
    }
    this.dirtyBlocks.clear();
    if (force) this.hasUnsaved = false;
    this.showUnsavedBadge(false);
    this.toast('💾 تم الحفظ التلقائي المشفر', 'success');
  }

  async restoreAllDrafts() {
    const keys = Object.keys(sessionStorage).filter(k => k.startsWith('omnifile_draft_'));
    for (const key of keys) {
      const id = key.replace('omnifile_draft_', '');
      const el = document.querySelector(`[data-block-id="${id}"]`);
      if (el) {
        const data = await this.crypto.retrieve(`draft_${id}`);
        if (data) { el.value = data.text; this.showUnsavedBadge(true); }
      }
    }
  }

  toast(msg, type) {
    // استخدام دالة toast الموجودة أو إنشاؤها مؤقتاً
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:${type==='success'?'#16a34a':'#333'};color:#fff;padding:10px 20px;border-radius:8px;z-index:9999;opacity:0;transition:opacity 0.3s`;
    t.textContent = msg; document.body.appendChild(t);
    setTimeout(() => t.style.opacity = 1, 10);
    setTimeout(() => { t.style.opacity = 0; setTimeout(() => t.remove(), 300); }, 2500);
  }
}

// تهيئة تلقائية مع الـ PWA
document.addEventListener('DOMContentLoaded', () => {
  if (window.omnifileCrypto) {
    window.smartSave = new SmartSaveHandler(window.omnifileCrypto);
  }
});
