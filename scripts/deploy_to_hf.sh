#!/usr/bin/env bash
# ================================================================
# OmniFile AI Processor — HuggingFace Space Deployment Script
# تشغيل: bash deploy_to_hf.sh
# ================================================================
set -e

HF_TOKEN="${HF_TOKEN:-your_hf_token_here}"
HF_USER="DrAbdulmalek"
SPACE_NAME="OmniFile-Processor"
REPO_DIR="/tmp/omnifile_push"
SPACE_DIR="/tmp/hf_space_deploy"

echo "================================================"
echo "  OmniFile → HuggingFace Space Deployment"
echo "================================================"

# ── Step 1: Check if Space exists, create if not ──────────────────
echo ""
echo "Step 1: Checking/Creating HF Space..."
SPACE_CHECK=$(curl -sL \
  -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/$HF_USER/$SPACE_NAME")

if echo "$SPACE_CHECK" | grep -q '"error"'; then
  echo "Creating new Space: $HF_USER/$SPACE_NAME"
  curl -sL -X POST \
    -H "Authorization: Bearer $HF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"type\":\"space\",\"name\":\"$SPACE_NAME\",\"private\":false,\"sdk\":\"docker\"}" \
    "https://huggingface.co/api/repos/create"
  echo "Space created!"
else
  echo "Space exists: $HF_USER/$SPACE_NAME"
fi

# ── Step 2: Clone or init Space repo ──────────────────────────────
echo ""
echo "Step 2: Setting up Space repo..."
rm -rf "$SPACE_DIR"
git clone \
  "https://DrAbdulmalek:$HF_TOKEN@huggingface.co/spaces/$HF_USER/$SPACE_NAME" \
  "$SPACE_DIR" 2>/dev/null \
  || {
    mkdir -p "$SPACE_DIR"
    cd "$SPACE_DIR"
    git init
    git remote add origin "https://DrAbdulmalek:$HF_TOKEN@huggingface.co/spaces/$HF_USER/$SPACE_NAME"
  }

# ── Step 3: Copy project files to Space ───────────────────────────
echo ""
echo "Step 3: Copying project files..."
cd "$SPACE_DIR"

# Copy key files (exclude heavy/unnecessary items)
rsync -a --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='data/' \
  --exclude='data_seed/' \
  --exclude='artifacts/' \
  --exclude='k8s/' \
  --exclude='terraform/' \
  --exclude='ansible/' \
  --exclude='notebooks/' \
  --exclude='*.db' \
  --exclude='*.sqlite' \
  "$REPO_DIR/" "$SPACE_DIR/"

# ── Step 4: Push to HF ────────────────────────────────────────────
echo ""
echo "Step 4: Pushing to HF Space..."
git config user.email "DrAbdulmalek@users.noreply.github.com"
git config user.name "Dr. Abdulmalek"
git add -A
git commit -m "deploy: OmniFile AI Processor v6.0.0" 2>/dev/null || echo "Nothing to commit"
git push origin main --force 2>&1

echo ""
echo "================================================"
echo "  Deployment complete!"
echo "  Space URL: https://huggingface.co/spaces/$HF_USER/$SPACE_NAME"
echo "================================================"
