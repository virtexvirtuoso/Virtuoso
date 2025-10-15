#!/bin/bash

# Virtuoso: Disk usage monitor
# Emits alerts when disk usage crosses thresholds; suitable for cron.

set -euo pipefail

THRESHOLD_WARN="${THRESHOLD_WARN:-80}"
THRESHOLD_CRIT="${THRESHOLD_CRIT:-90}"
CHECK_PATH="${CHECK_PATH:-/}"

USAGE=$(df -P "$CHECK_PATH" | awk 'NR==2 {print $5}' | tr -d '%')

timestamp=$(date '+%Y-%m-%d %H:%M:%S')
log_file="/var/log/virtuoso-disk-monitor.log"
mkdir -p /var/log || true

status="OK"
code=0
if [ "$USAGE" -ge "$THRESHOLD_CRIT" ]; then
  status="CRITICAL"
  code=2
elif [ "$USAGE" -ge "$THRESHOLD_WARN" ]; then
  status="WARNING"
  code=1
fi

echo "$timestamp disk_usage=$USAGE% status=$status" | tee -a "$log_file"

# Hook for further integrations (email/webhook) if desired
if [ $code -eq 2 ]; then
  # Try to free journal space quickly if journalctl exists
  if command -v journalctl >/dev/null 2>&1; then
    journalctl --vacuum-size=100M >/dev/null 2>&1 || true
  fi
fi

exit $code


