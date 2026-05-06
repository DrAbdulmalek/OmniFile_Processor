# PWA Features Guide
# Progressive Web App features for OmniFile Processor mobile review.

## Features

### 1. Encrypted Session Storage (session_crypto.js)
AES-GCM encryption for sessionStorage. Password-derived key via PBKDF2.

### 2. Smart Save Handler (smart_save_handler.js)
beforeunload protection. Auto-save every 30s. Queue-based offline support.

### 3. Draft TTL Storage (draft_ttl_storage.js)
Time-to-live for localStorage drafts. Default: 7 days. Auto-cleanup.

### 4. PWA Generator (pwa_generator.py)
Generates manifest.json, service worker, and app icons.

### 5. Gradio PWA Wrapper (gradio_pwa_wrapper.py)
Wraps Gradio Blocks as installable PWA with QR code generation.
