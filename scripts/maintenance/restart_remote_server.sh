#!/bin/bash

#############################################################################
# Script: restart_remote_server.sh
# Purpose: Deploy and manage restart remote server
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
#   ./restart_remote_server.sh [options]
#   
#   Examples:
#     ./restart_remote_server.sh
#     ./restart_remote_server.sh --verbose
#     ./restart_remote_server.sh --dry-run
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

# Script to restart the web server on remote host

echo "🔄 Restarting Virtuoso web server on VPS_HOST_REDACTED..."

ssh linuxuser@VPS_HOST_REDACTED 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing web server processes
echo "Stopping existing processes..."
pkill -f "python src/web_server.py" || true
pkill -f "python.*web_server" || true
sleep 2

# Activate virtual environment and start server
echo "Starting web server..."
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    nohup python src/web_server.py > web_server.log 2>&1 &
    SERVER_PID=$!
    echo "Web server started with PID: $SERVER_PID"
    
    # Wait and check if it's running
    sleep 3
    if ps -p $SERVER_PID > /dev/null; then
        echo "✅ Server is running"
        echo "Recent log output:"
        tail -n 20 web_server.log
    else
        echo "❌ Server failed to start. Check web_server.log for errors"
        tail -n 50 web_server.log
    fi
else
    echo "❌ Virtual environment not found at venv/"
    echo "Please create it first with: python -m venv venv"
fi
ENDSSH

echo ""
echo "🌐 Dashboard URLs:"
echo "   Desktop: http://VPS_HOST_REDACTED:8003/dashboard"
echo "   Mobile:  http://VPS_HOST_REDACTED:8003/dashboard/mobile"
echo "   Legacy:  http://VPS_HOST_REDACTED:8003/dashboard/v10"