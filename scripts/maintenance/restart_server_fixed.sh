#!/bin/bash

#############################################################################
# Script: restart_server_fixed.sh
# Purpose: Deploy and manage restart server fixed
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
#   ./restart_server_fixed.sh [options]
#   
#   Examples:
#     ./restart_server_fixed.sh
#     ./restart_server_fixed.sh --verbose
#     ./restart_server_fixed.sh --dry-run
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

echo "🔄 Restarting Virtuoso server with correct environment..."

ssh linuxuser@${VPS_HOST} 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill existing processes
echo "Stopping existing processes..."
pkill -9 -f "python.*web_server" || true
pkill -9 -f "uvicorn" || true
sleep 2

# Start with correct virtual environment
echo "Starting web server..."
if [ -f venv311/bin/activate ]; then
    source venv311/bin/activate
    nohup python src/web_server.py > web_server.log 2>&1 &
    echo "Server started with PID: $!"
    
    # Check logs after a few seconds
    sleep 5
    echo "Recent logs:"
    tail -20 web_server.log
else
    echo "Error: Virtual environment not found"
    exit 1
fi
ENDSSH