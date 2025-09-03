#!/bin/bash
#
# Setup automatic log rotation for Virtuoso CCXT
# This script creates a cron job for regular log cleanup
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
CLEAN_LOGS_SCRIPT="$SCRIPT_DIR/clean_logs.py"

echo "=========================================="
echo "Virtuoso CCXT Log Rotation Setup"
echo "=========================================="

# Function to add cron job
add_cron_job() {
    local schedule="$1"
    local command="$2"
    local description="$3"
    
    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "$command"; then
        echo "✓ Cron job already exists: $description"
    else
        # Add new cron job
        (crontab -l 2>/dev/null; echo "$schedule $command # $description") | crontab -
        echo "✓ Added cron job: $description"
    fi
}

# Daily log cleanup at 3 AM
DAILY_CLEANUP="0 3 * * * cd $PROJECT_ROOT && /usr/bin/python3 $CLEAN_LOGS_SCRIPT --execute >> $PROJECT_ROOT/logs/cleanup.log 2>&1"
add_cron_job "0 3 * * *" "$DAILY_CLEANUP" "Virtuoso daily log cleanup"

# Weekly aggressive cleanup on Sunday at 2 AM  
WEEKLY_CLEANUP="0 2 * * 0 cd $PROJECT_ROOT && /usr/bin/python3 $CLEAN_LOGS_SCRIPT --execute --aggressive >> $PROJECT_ROOT/logs/cleanup.log 2>&1"
add_cron_job "0 2 * * 0" "$WEEKLY_CLEANUP" "Virtuoso weekly aggressive log cleanup"

echo ""
echo "Current cron jobs for log cleanup:"
echo "-----------------------------------"
crontab -l | grep "Virtuoso.*log cleanup"

echo ""
echo "✅ Log rotation setup complete!"
echo ""
echo "To manually run cleanup:"
echo "  Regular: python3 $CLEAN_LOGS_SCRIPT --execute"
echo "  Aggressive: python3 $CLEAN_LOGS_SCRIPT --execute --aggressive"
echo ""
echo "To view cleanup logs:"
echo "  tail -f $PROJECT_ROOT/logs/cleanup.log"
echo ""
echo "To remove cron jobs:"
echo "  crontab -e  # Then delete the Virtuoso lines"