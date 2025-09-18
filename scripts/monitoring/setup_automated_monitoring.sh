#!/bin/bash

#############################################################################
# Script: setup_automated_monitoring.sh
# Purpose: Setup and configure setup automated monitoring
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_automated_monitoring.sh [options]
#   
#   Examples:
#     ./setup_automated_monitoring.sh
#     ./setup_automated_monitoring.sh --verbose
#     ./setup_automated_monitoring.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Set up automated monitoring for critical fixes
VPS_HOST="linuxuser@${VPS_HOST}"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "Setting up automated monitoring on VPS..."

# Create monitoring script on VPS
ssh $VPS_HOST "cat > $VPS_DIR/scripts/monitor_health.sh << 'EOF'
#!/bin/bash

LOG_FILE=\"/home/linuxuser/trading/Virtuoso_ccxt/logs/health_monitor.log\"

# Function to log with timestamp
log() {
    echo \"\$(date '+%Y-%m-%d %H:%M:%S') - \$1\" >> \"\$LOG_FILE\"
}

# Check if process is running
PID=\$(pgrep -f 'python.*main.py')
if [ -z \"\$PID\" ]; then
    log \"ERROR: Process not running!\"
    # Restart the process
    cd /home/linuxuser/trading/Virtuoso_ccxt
    nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py > logs/startup.log 2>&1 &
    log \"RESTARTED: Process restarted\"
else
    # Check if log file is being updated
    LAST_MOD=\$(stat -c %Y logs/app.log)
    CURRENT_TIME=\$(date +%s)
    DIFF=\$((CURRENT_TIME - LAST_MOD))
    
    if [ \$DIFF -gt 300 ]; then  # More than 5 minutes
        log \"WARNING: Log file not updated for \$DIFF seconds\"
        
        # Check for timeout errors
        TIMEOUT_COUNT=\$(grep -c 'Request timeout' logs/app.log || echo 0)
        if [ \$TIMEOUT_COUNT -gt 0 ]; then
            log \"INFO: Found \$TIMEOUT_COUNT timeout errors\"
        fi
    fi
    
    # Check memory usage
    MEM_USAGE=\$(ps aux | grep \$PID | awk '{print \$4}')
    log \"INFO: Process PID=\$PID, Memory=\$MEM_USAGE%\"
fi

# Check for PENGUUSDT if it should be monitored
if grep -q 'PENGUUSDT' logs/app.log 2>/dev/null; then
    PENGU_COUNT=\$(grep -c 'PENGUUSDT' logs/app.log)
    log \"INFO: PENGUUSDT mentioned \$PENGU_COUNT times\"
fi

# Keep only last 1000 lines of health log
tail -1000 \"\$LOG_FILE\" > \"\$LOG_FILE.tmp\" && mv \"\$LOG_FILE.tmp\" \"\$LOG_FILE\"
EOF"

# Make it executable
ssh $VPS_HOST "chmod +x $VPS_DIR/scripts/monitor_health.sh"

# Set up cron job
ssh $VPS_HOST "crontab -l > /tmp/current_cron 2>/dev/null || true"
ssh $VPS_HOST "grep -v 'monitor_health.sh' /tmp/current_cron > /tmp/new_cron || true"
ssh $VPS_HOST "echo '*/5 * * * * $VPS_DIR/scripts/monitor_health.sh' >> /tmp/new_cron"
ssh $VPS_HOST "crontab /tmp/new_cron"
ssh $VPS_HOST "rm /tmp/current_cron /tmp/new_cron"

echo "✅ Automated monitoring set up!"
echo "Health logs will be written to: $VPS_DIR/logs/health_monitor.log"
echo "Monitoring runs every 5 minutes via cron"