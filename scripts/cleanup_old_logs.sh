#!/bin/bash
# Cleanup old log files to free up space
# Keeps DEBUG level but manages storage efficiently

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../logs"
cd "$LOG_DIR" || exit 1

echo "🧹 Cleaning up old log files..."
echo "Current log directory size: $(du -sh . | cut -f1)"

# Remove logs older than 60 days
find . -name "*.log.2025-*" -type f -mtime +60 -delete 2>/dev/null
find . -name "*.gz" -type f -mtime +60 -delete 2>/dev/null

# Remove very large test logs that are no longer needed
find . -name "*test*.log" -size +50M -mtime +7 -delete 2>/dev/null

# Keep only last 5 deployment logs
ls -t deployment_*.log 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null

# Keep only last 10 enhanced scoring test logs
ls -t enhanced_scoring*.log 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null

echo "After cleanup: $(du -sh . | cut -f1)"
echo "✅ Old log cleanup complete!"