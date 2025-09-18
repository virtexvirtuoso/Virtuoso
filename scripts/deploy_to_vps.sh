#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/deploy_to_vps.sh user@host:/srv/virtuoso-ccxt virtuoso.service [--dry-run]
TARGET=${1:-}
SERVICE=${2:-virtuoso.service}
DRY_RUN=${3:-}

if [ -z "$TARGET" ]; then
  echo "Usage: $0 user@host:/srv/virtuoso-ccxt [service-name]" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXCLUDE_FILE="$ROOT_DIR/scripts/.rsync-exclude"

echo "📦 Syncing project to $TARGET"
if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "🔎 DRY RUN: rsync preview (no changes)"
  rsync -azn --delete --exclude-from="$EXCLUDE_FILE" "$ROOT_DIR/" "$TARGET/"
  echo "✅ DRY RUN complete"
  exit 0
fi

rsync -az --delete --exclude-from="$EXCLUDE_FILE" "$ROOT_DIR/" "$TARGET/"

SSH_HOST="${TARGET%%:*}"
REMOTE_DIR="${TARGET#*:}"

# Post-deploy: venv, deps, systemd restart
ssh "$SSH_HOST" bash -lc "set -euo pipefail; \
  cd '$REMOTE_DIR'; \
  if [ ! -d venv311 ]; then python3 -m venv venv311; fi; \
  source venv311/bin/activate; \
  python -m pip install --upgrade pip; \
  if [ -f requirements.txt ]; then pip install -r requirements.txt; fi; \
  sudo systemctl daemon-reload || true; \
  sudo systemctl restart '$SERVICE'; \
  sudo systemctl status '$SERVICE' --no-pager --full | tail -n 50; \
  echo '✅ Deployment complete'"
