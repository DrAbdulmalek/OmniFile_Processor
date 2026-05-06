#!/usr/bin/env bash
set -euo pipefail

PDF_PATH="${1:-}"
if [[ -z "$PDF_PATH" ]]; then
  echo "Usage: bash scripts/launch_local.sh /path/to/input.pdf [extra args...]"
  exit 1
fi
shift || true
python run.py --local --pdf "$PDF_PATH" "$@"
