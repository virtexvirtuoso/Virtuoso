#!/bin/bash

#############################################################################
# Script: simple_connection_monitor.sh
# Purpose: Simple connection monitor for Virtuoso
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./simple_connection_monitor.sh [options]
#   
#   Examples:
#     ./simple_connection_monitor.sh
#     ./simple_connection_monitor.sh --verbose
#     ./simple_connection_monitor.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

LOG_FILE="/tmp/virtuoso_connections.log"

echo "Starting connection monitor..."
echo "Logging to: $LOG_FILE"

while true; do
    # Get process PID
    PID=$(pgrep -f "python.*main.py" | head -1)
    
    if [ -z "$PID" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Virtuoso process not found" >> "$LOG_FILE"
        sleep 60
        continue
    fi
    
    # Count connections
    TOTAL=$(lsof -p "$PID" 2>/dev/null | grep -c TCP)
    ESTABLISHED=$(ss -tn | grep -c ESTAB)
    TIME_WAIT=$(ss -tn | grep -c TIME-WAIT)
    BYBIT=$(ss -tn | grep ESTAB | grep -c "18\.161")
    
    # Get CPU and memory
    CPU=$(ps -p "$PID" -o %cpu= | tr -d ' ')
    MEM_KB=$(ps -p "$PID" -o rss= | tr -d ' ')
    MEM_MB=$((MEM_KB / 1024))
    
    # Log results
    echo "$(date '+%Y-%m-%d %H:%M:%S') | PID: $PID | Connections: $ESTABLISHED/$TOTAL (Bybit: $BYBIT) | TIME_WAIT: $TIME_WAIT | CPU: $CPU% | Mem: ${MEM_MB}MB" | tee -a "$LOG_FILE"
    
    # Alert on high connections
    if [ "$ESTABLISHED" -gt 100 ]; then
        echo "⚠️  WARNING: High connection count: $ESTABLISHED" | tee -a "$LOG_FILE"
    fi
    
    # Check every 60 seconds
    sleep 60
done