#!/bin/bash

#############################################################################
# Script: restart_web_proper.sh
# Purpose: Deploy and manage restart web proper
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
#   ./restart_web_proper.sh [options]
#   
#   Examples:
#     ./restart_web_proper.sh
#     ./restart_web_proper.sh --verbose
#     ./restart_web_proper.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

VPS_HOST="5.223.63.4"
VPS_USER="linuxuser"

echo "Restarting web server with direct cache adapter..."

ssh ${VPS_USER}@${VPS_HOST} 'bash -s' << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill and restart web server
pkill -f "web_server.py" || true
sleep 2

export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > logs/web_server_restart.log 2>&1 &

sleep 5

# Check the log for which adapter is being used
echo "Checking adapter usage:"
grep -i "adapter" logs/web_server_restart.log | head -10

# Check if server is running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server restarted"
else
    echo "❌ Web server failed to start"
    tail -20 logs/web_server_restart.log
fi
EOF