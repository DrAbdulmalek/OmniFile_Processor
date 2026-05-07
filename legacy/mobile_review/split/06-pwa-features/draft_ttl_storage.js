// draft_ttl_storage.js - localStorage with TTL for drafts

/**
 * 🕒 TTLStorageManager: طبقة تخزين احتياطية ذاتية التنظيف
 * - يخزن في localStorage مع تاريخ انتهاء صلاحية
 * - ينظف تلقائياً عند التهيئة وكل 5 دقائق
 * - يتعامل بذكاء مع حدود التخزين (Quota Exceeded)
 */
class TTLStorageManager {
    constructor(prefix = 'omnifile_draft_', ttlMs = 3600000) { // افتراضي: ساعة واحدة
        this.prefix = prefix;
        this.ttl = ttlMs;
        this.cleanupInterval = null;
        this.init();
    }

    init() {
        this.cleanupExpired();
        this.cleanupInterval = setInterval(() => this.cleanupExpired(), 300000); // كل 5 دقائق
    }

    set(key, data) {
        const payload = { data, expiry: Date.now() + this.ttl, savedAt: Date.now() };
        try {
            localStorage.setItem(this.prefix + key, JSON.stringify(payload));
        } catch (e) {
            if (e.name === 'QuotaExceededError') {
                this.cleanupExpired(true); // تنظيف إجباري عند امتلاء الذاكرة
                try { localStorage.setItem(this.prefix + key, JSON.stringify(payload)); }
                catch (e2) { console.warn('⚠️ فشل الحفظ الاحتياطي: الذاكرة ممتلئة'); }
            }
        }
    }

    get(key) {
        const raw = localStorage.getItem(this.prefix + key);
        if (!raw) return null;
        try {
            const payload = JSON.parse(raw);
            if (Date.now() > payload.expiry) {
                localStorage.removeItem(this.prefix + key);
                return null;
            }
            return payload.data;
        } catch { return null; }
    }

    remove(key) { localStorage.removeItem(this.prefix + key); }

    cleanupExpired(force = false) {
        const keys = Object.keys(localStorage).filter(k => k.startsWith(this.prefix));
        let removed = 0;
        for (const k of keys) {
            try {
                const val = JSON.parse(localStorage.getItem(k));
                if (force || Date.now() > val.expiry) {
                    localStorage.removeItem(k);
                    removed++;
                }
            } catch { localStorage.removeItem(k); removed++; } // حذف التالف
        }
        if (removed > 0) console.log(`🧹 تم تنظيف ${removed} مسودة منتهية الصلاحية`);
    }

    destroy() { clearInterval(this.cleanupInterval); }
}
