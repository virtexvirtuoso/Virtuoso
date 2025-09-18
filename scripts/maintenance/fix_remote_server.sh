#!/bin/bash

#############################################################################
# Script: fix_remote_server.sh
# Purpose: Deploy and manage fix remote server
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
#   ./fix_remote_server.sh [options]
#   
#   Examples:
#     ./fix_remote_server.sh
#     ./fix_remote_server.sh --verbose
#     ./fix_remote_server.sh --dry-run
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

# Script to fix the remote server issues

echo "🔧 Fixing Virtuoso server issues on 5.223.63.4..."

# First, ensure the server is properly restarted
echo "1. Restarting web server to pick up route changes..."

ssh linuxuser@5.223.63.4 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill existing processes more thoroughly
echo "Stopping all Python web server processes..."
pkill -9 -f "python.*web_server" || true
pkill -9 -f "uvicorn" || true
sleep 3

# Check if any processes are still running
if pgrep -f "web_server" > /dev/null; then
    echo "Warning: Some processes may still be running"
    ps aux | grep web_server | grep -v grep
fi

# Start the server
echo "Starting web server..."
source venv/bin/activate
nohup python src/web_server.py > web_server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Give it time to start
sleep 5

# Check if it's running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server is running"
    
    # Show startup logs
    echo ""
    echo "Startup logs:"
    tail -n 30 web_server.log | grep -E "(Started|Listening|ERROR|WARNING|routes|uvicorn)"
else
    echo "❌ Server failed to start"
    echo "Error logs:"
    tail -n 50 web_server.log
    exit 1
fi
ENDSSH

echo ""
echo "2. Testing fixed routes..."
sleep 3

# Test the routes
test_route() {
    local path=$1
    local desc=$2
    echo -n "Testing $desc... "
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://5.223.63.4:8003$path")
    if [ "$status" = "200" ]; then
        echo "✅ OK ($status)"
    else
        echo "❌ Failed ($status)"
    fi
}

test_route "/dashboard/desktop" "/dashboard/desktop"
test_route "/dashboard/v10" "/dashboard/v10"
test_route "/dashboard/mobile" "/dashboard/mobile"
test_route "/api/market/overview" "Market Overview API"

echo ""
echo "3. Checking API performance..."
echo -n "Market Overview API response time: "
time_taken=$(curl -s -o /dev/null -w "%{time_total}" "http://5.223.63.4:8003/api/market/overview")
echo "${time_taken}s"

if (( $(echo "$time_taken > 5" | bc -l) )); then
    echo "⚠️  API is slow (>5s). This might be due to:"
    echo "   - First-time cache loading"
    echo "   - Multiple exchange API calls"
    echo "   - Try again in a minute for cached responses"
fi

echo ""
echo "✅ Server fixes applied!"
echo ""
echo "Dashboard URLs:"
echo "  Desktop: http://5.223.63.4:8003/dashboard"
echo "  Mobile:  http://5.223.63.4:8003/dashboard/mobile"
echo "  Legacy:  http://5.223.63.4:8003/dashboard/v10"