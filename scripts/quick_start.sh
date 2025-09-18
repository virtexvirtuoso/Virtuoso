#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Virtuoso CCXT Quick Start"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python3 --version || { echo "❌ Python3 not found"; exit 1; }

if [ ! -d "venv311" ]; then
  echo "📦 Creating Python 3.11 virtual environment..."
  python3 -m venv venv311
fi

source venv311/bin/activate
python -m pip install --upgrade pip

if [ -f requirements.txt ]; then
  echo "📥 Installing dependencies..."
  pip install -r requirements.txt
fi

echo "📋 Running configuration wizard (non-interactive stub)..."
python - << 'PY'
try:
    from src.config.wizard import run_wizard
    run_wizard(non_interactive=True)
except Exception as e:
    print(f"⚠️ Config wizard skipped: {e}")
PY

echo "🔍 Validating health endpoint locally (if server running)..."
if command -v curl >/dev/null 2>&1; then
  curl -sS http://localhost:8003/health || true
fi

echo "✅ Quick start complete. To run the app:"
echo "   source venv311/bin/activate && python src/main.py"


