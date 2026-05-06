// session_crypto.js - Encrypted sessionStorage for PWA

/**
 * 🔐 SecureSessionStorage: تشفير شفاف لبيانات الجلسة
 * - يستخدم Web Crypto API (AES-GCM)
 * - المفتاح يُولد في RAM فقط (لا يُخزن محلياً)
 * - يُمسح تلقائياً عند إغلاق المتصفح/التبويب
 */
class SecureSessionStorage {
    constructor(prefix = 'omnifile_') {
        this.prefix = prefix;
        this.sessionKey = null;
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;
        // توليد مفتاح AES-256 عشوائي للجلسة الحالية
        this.sessionKey = await crypto.subtle.generateKey(
            { name: "AES-GCM", length: 256 },
            true,
            ["encrypt", "decrypt"]
        );
        this.initialized = true;
        console.log("🔐 مفتاح جلسة مشفر تم توليده بنجاح");
    }

    async store(key, data) {
        if (!this.initialized) await this.init();
        const payload = typeof data === 'string' ? data : JSON.stringify(data);
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const encoded = new TextEncoder().encode(payload);

        const cipherBuffer = await crypto.subtle.encrypt(
            { name: "AES-GCM", iv: iv },
            this.sessionKey,
            encoded
        );

        // دمج IV + النص المشفر + تحويل لـ Base64 للتخزين الآمن
        const combined = new Uint8Array(iv.length + cipherBuffer.byteLength);
        combined.set(iv);
        combined.set(new Uint8Array(cipherBuffer), iv.length);

        sessionStorage.setItem(this.prefix + key, btoa(String.fromCharCode(...combined)));
    }

    async retrieve(key) {
        if (!this.initialized) await this.init();
        const stored = sessionStorage.getItem(this.prefix + key);
        if (!stored) return null;

        try {
            const combined = Uint8Array.from(atob(stored), c => c.charCodeAt(0));
            const iv = combined.slice(0, 12);
            const cipher = combined.slice(12);

            const plainBuffer = await crypto.subtle.decrypt(
                { name: "AES-GCM", iv: iv },
                this.sessionKey,
                cipher
            );
            const decoded = new TextDecoder().decode(plainBuffer);
            // محاولة فك JSON تلقائياً
            try { return JSON.parse(decoded); } catch { return decoded; }
        } catch (e) {
            console.warn("⚠️ فشل فك التشفير (جلسة جديدة أو بيانات تالفة)", e);
            return null;
        }
    }

    clear() {
        Object.keys(sessionStorage)
            .filter(k => k.startsWith(this.prefix))
            .forEach(k => sessionStorage.removeItem(k));
    }
}

// 🔧 تهيئة تلقائية عند تحميل الـ PWA
window.omnifileCrypto = new SecureSessionStorage();
window.addEventListener('load', () => window.omnifileCrypto.init().catch(console.error));
