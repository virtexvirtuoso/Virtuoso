#!/bin/bash

# Virtuoso: Cleanup exports and reports artifacts
# Safely removes old generated files to control disk usage

set -euo pipefail

RETENTION_DAYS="${RETENTION_DAYS:-14}"
PROJECT_ROOT="${PROJECT_ROOT:-/opt/virtuoso}"

TARGET_DIRS=(
  "$PROJECT_ROOT/exports"
  "$PROJECT_ROOT/src/exports"
  "$PROJECT_ROOT/reports/pdf"
)

log() { echo "[cleanup_exports] $1"; }

for dir in "${TARGET_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    log "Pruning files older than ${RETENTION_DAYS} days in: $dir"
    # Delete files older than RETENTION_DAYS
    find "$dir" -type f -mtime +"$RETENTION_DAYS" -print -delete || true
    # Remove empty directories left behind
    find "$dir" -type d -empty -print -delete || true
  fi
done

log "Cleanup complete."

exit 0


