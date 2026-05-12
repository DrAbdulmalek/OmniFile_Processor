#!/usr/bin/env python3
"""
webhook_receiver.py
===================
Simple webhook receiver for testing Prometheus Alertmanager notifications.
خادم بسيط لاستقبال تنبيهات Alertmanager للاختبار.

Usage:
    python webhook_receiver.py
    # Listens on http://localhost:5000
"""

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/alert-webhook', methods=['POST'])
def alert_webhook():
    """استقبال التنبيهات العادية."""
    data = request.json
    print("[ALERT] Received alert:", data)
    return jsonify(status="ok"), 200


@app.route('/critical-alert', methods=['POST'])
def critical_webhook():
    """استقبال التنبيهات الحرجة."""
    data = request.json
    print("[CRITICAL] Received critical alert:", data)
    return jsonify(status="ok"), 200


@app.route('/health', methods=['GET'])
def health():
    """فحص الحالة."""
    return jsonify(status="healthy"), 200


if __name__ == '__main__':
    print("Webhook receiver listening on http://localhost:5000")
    print("Endpoints: /alert-webhook, /critical-alert, /health")
    app.run(host='0.0.0.0', port=5000, debug=False)
