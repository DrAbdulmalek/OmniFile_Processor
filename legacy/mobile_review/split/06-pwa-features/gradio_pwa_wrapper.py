# gradio_pwa_wrapper.py - Wraps Gradio as installable PWA
"""
🌐 يحوّل واجهة Gradio العادية إلى PWA قابلة للتثبيت على الأندرويد/iOS
يعمل مع Colab عبر ngrok (يتطلب HTTPS)
"""
import gradio as gr
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

def mount_pwa(app: FastAPI, assets_dir: str = "pwa_static"):
    """تسجيل الملفات الساكنة و manifest/service-worker"""
    app.mount("/pwa", StaticFiles(directory=assets_dir), name="pwa_assets")

def inject_pwa_head() -> str:
    return """
    <link rel="manifest" href="/pwa/manifest.json">
    <meta name="theme-color" content="#2563eb">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="/pwa/icon-192.png">
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/pwa/sw.js')
                .then(() => console.log('✅ PWA Service Worker Registered'))
                .catch(e => console.warn('⚠️ SW failed:', e));
        }
    </script>
    """

def launch_pwa_dashboard(dashboard_builder_func, port: int = 7860, share: bool = True):
    app = FastAPI()
    mount_pwa(app, "pwa_static")

    # بناء واجهة Gradio الأصلية
    dashboard = dashboard_builder_func()
    dashboard.head = inject_pwa_head()  # حقن رأس الصفحة

    # دمج Gradio مع FastAPI
    gr.mount_gradio_app(app, dashboard, path="/")

    import uvicorn
    print(f"🚀 PWA جاهزة. افتح الرابط في متصفح الهاتف واختر 'إضافة إلى الشاشة الرئيسية'")
    uvicorn.run(app, host="0.0.0.0", port=port)
