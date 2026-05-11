#!/bin/bash
# OmniFile AI Gateway - Start Script
# A universal AI model proxy for code assistants

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GATEWAY_DIR="$PROJECT_ROOT/modules/ai/gateway"

# Check if .env exists
if [ ! -f "$GATEWAY_DIR/.env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp "$GATEWAY_DIR/.env.example" "$GATEWAY_DIR/.env"
    echo "📝 Please edit $GATEWAY_DIR/.env with your API keys and settings."
    exit 1
fi

echo "🚀 Starting OmniFile AI Gateway..."
echo "📡 Proxy will be available at: http://localhost:8082"
echo ""

cd "$GATEWAY_DIR"
# Load .env file
export $(grep -v '^#' .env | xargs)

python -m uvicorn modules.ai.gateway.server:app \
    --host ${GATEWAY_HOST:-0.0.0.0} \
    --port ${GATEWAY_PORT:-8082} \
    --log-level info
