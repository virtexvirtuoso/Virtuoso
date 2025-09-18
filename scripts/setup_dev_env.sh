#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "🔧 Setting up Virtuoso dev environment"

if [ ! -d venv311 ]; then
  python3 -m venv venv311
fi
source venv311/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

echo "▶️ Running quick start"
bash scripts/quick_start.sh || true

echo "✅ Dev environment ready"


