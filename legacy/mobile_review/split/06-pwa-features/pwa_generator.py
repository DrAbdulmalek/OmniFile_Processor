# pwa_generator.py - PWA asset generator

"""
📦 يولد manifest.json و service-worker.js ويجهز Gradio للعمل كـ PWA
"""
import json
from pathlib import Path

def generate_pwa_assets(output_dir: str = "pwa_static"):
    d = Path(output_dir); d.mkdir(exist_ok=True)

    (d / "manifest.json").write_text(json.dumps({
        "name": "OmniFile OCR Review",
        "short_name": "OmniFile",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#2563eb",
        "orientation": "any",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }, indent=2), encoding="utf-8")

    (d / "sw.js").write_text("""
    const CACHE = 'omnifile-pwa-v1';
    self.addEventListener('install', e => self.skipWaiting());
    self.addEventListener('activate', e => e.waitUntil(clients.claim()));
    self.addEventListener('fetch', e => {
        if (e.request.method !== 'GET') return;
        e.respondWith(
            caches.match(e.request).then(r => r || fetch(e.request).catch(() => new Response('Offline', {status: 503})))
        );
    });
    """, encoding="utf-8")

    print(f"✅ أصول PWA جاهزة في: {d.absolute()}")
    print("💡 استبدل icon-192.png و icon-512.png بأيقونتك الخاصة.")
    return d
