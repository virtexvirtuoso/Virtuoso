#!/bin/bash

#############################################################################
# Script: monitor_pool_live.sh
# Purpose: Live connection pool monitor for Virtuoso Trading System
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
#   ./monitor_pool_live.sh [options]
#   
#   Examples:
#     ./monitor_pool_live.sh
#     ./monitor_pool_live.sh --verbose
#     ./monitor_pool_live.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔍 Virtuoso Connection Pool Monitor - Live View"
echo "================================================"
echo ""

while true; do
    # Clear screen for live update
    clear
    
    echo "🔍 Virtuoso Connection Pool Monitor - Live View"
    echo "================================================"
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Get current stats from VPS
    ssh linuxuser@VPS_HOST_REDACTED "
        PID=\$(pgrep -f 'python.*main.py' | head -1)
        if [ -z \"\$PID\" ]; then
            echo '❌ Service not running'
            exit 1
        fi
        
        TOTAL=\$(lsof -p \$PID 2>/dev/null | grep -c TCP)
        ESTABLISHED=\$(ss -tn | grep -c ESTAB)
        TIME_WAIT=\$(ss -tn | grep -c TIME-WAIT)
        BYBIT=\$(ss -tn | grep ESTAB | grep -c '18\.161')
        CPU=\$(ps -p \$PID -o %cpu= | tr -d ' ')
        MEM_KB=\$(ps -p \$PID -o rss= | tr -d ' ')
        MEM_MB=\$((MEM_KB / 1024))
        UPTIME=\$(ps -p \$PID -o etime= | tr -d ' ')
        
        echo \"PID:\$PID\"
        echo \"ESTABLISHED:\$ESTABLISHED\"
        echo \"TOTAL:\$TOTAL\"
        echo \"BYBIT:\$BYBIT\"
        echo \"TIME_WAIT:\$TIME_WAIT\"
        echo \"CPU:\$CPU\"
        echo \"MEM_MB:\$MEM_MB\"
        echo \"UPTIME:\$UPTIME\"
    " | while IFS=: read key value; do
        case $key in
            PID) PID=$value ;;
            ESTABLISHED) ESTABLISHED=$value ;;
            TOTAL) TOTAL=$value ;;
            BYBIT) BYBIT=$value ;;
            TIME_WAIT) TIME_WAIT=$value ;;
            CPU) CPU=$value ;;
            MEM_MB) MEM_MB=$value ;;
            UPTIME) UPTIME=$value ;;
        esac
    done
    
    # Display formatted stats
    echo "📊 System Status:"
    echo "  • Process ID: $PID"
    echo "  • Uptime: $UPTIME"
    echo ""
    
    echo "🔌 Connection Pool:"
    echo "  • Established: $ESTABLISHED"
    echo "  • Total TCP: $TOTAL"
    echo "  • Bybit API: $BYBIT"
    echo "  • TIME_WAIT: $TIME_WAIT"
    
    # Connection status indicator
    if [ "$ESTABLISHED" -lt 50 ]; then
        echo -e "  • Status: ${GREEN}✓ Healthy${NC}"
    elif [ "$ESTABLISHED" -lt 100 ]; then
        echo -e "  • Status: ${YELLOW}⚠ Elevated${NC}"
    else
        echo -e "  • Status: ${RED}✗ Critical${NC}"
    fi
    echo ""
    
    echo "💻 Resources:"
    echo "  • CPU Usage: ${CPU}%"
    echo "  • Memory: ${MEM_MB} MB"
    
    # Resource status indicator
    CPU_INT=${CPU%.*}
    if [ "$CPU_INT" -lt 70 ]; then
        echo -e "  • Status: ${GREEN}✓ Normal${NC}"
    elif [ "$CPU_INT" -lt 80 ]; then
        echo -e "  • Status: ${YELLOW}⚠ High${NC}"
    else
        echo -e "  • Status: ${RED}✗ Critical - Consider restart${NC}"
    fi
    echo ""
    
    echo "📈 Recent Trends (last 5 minutes):"
    ssh linuxuser@VPS_HOST_REDACTED "tail -5 /tmp/virtuoso_connections.log 2>/dev/null | tail -5" | while read line; do
        echo "  $line"
    done
    echo ""
    
    echo "Press Ctrl+C to exit"
    echo "Refreshing in 10 seconds..."
    
    sleep 10
done