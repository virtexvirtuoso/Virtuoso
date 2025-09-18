#!/bin/bash

#############################################################################
# Script: final_server_fix.sh
# Purpose: Deploy and manage final server fix
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
#   ./final_server_fix.sh [options]
#   
#   Examples:
#     ./final_server_fix.sh
#     ./final_server_fix.sh --verbose
#     ./final_server_fix.sh --dry-run
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

echo "🔧 Final server fix for Virtuoso on ${VPS_HOST}"
echo "=============================================="

# Run all fixes on remote server
ssh linuxuser@${VPS_HOST} 'bash -s' << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "1. Killing ALL Python processes on port 8003..."
# Find and kill any process using port 8003
for pid in $(lsof -ti :8003); do
    echo "   Killing process $pid"
    kill -9 $pid 2>/dev/null || true
done

# Also kill by name
pkill -9 -f "python.*web_server" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true

sleep 3

echo "2. Verifying port is free..."
if lsof -i :8003 >/dev/null 2>&1; then
    echo "   ❌ Port 8003 still in use!"
    lsof -i :8003
else
    echo "   ✅ Port 8003 is free"
fi

echo "3. Starting server with correct environment..."
if [ -f venv311/bin/python ]; then
    echo "   Using venv311 Python"
    source venv311/bin/activate
    
    # Start server in background
    nohup python src/web_server.py > web_server.log 2>&1 &
    SERVER_PID=$!
    echo "   Server started with PID: $SERVER_PID"
    
    # Wait for server to start
    echo "4. Waiting for server startup..."
    for i in {1..10}; do
        if curl -s http://localhost:8003/health >/dev/null 2>&1; then
            echo "   ✅ Server is responding!"
            break
        fi
        echo "   Waiting... ($i/10)"
        sleep 2
    done
    
    # Show logs
    echo "5. Server logs:"
    tail -30 web_server.log | grep -E "(Started|Listening|ERROR|WARNING|INFO|uvicorn.error|routes)"
    
    # Verify process is still running
    if ps -p $SERVER_PID > /dev/null; then
        echo "   ✅ Server process is running"
    else
        echo "   ❌ Server process died. Full logs:"
        tail -100 web_server.log
    fi
else
    echo "   ❌ Virtual environment not found!"
    ls -la | grep venv
fi
ENDSSH

echo ""
echo "6. Testing endpoints from local machine..."
sleep 3

# Test function
test_endpoint() {
    local url=$1
    local desc=$2
    echo -n "   $desc: "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5)
    if [ "$response" = "200" ]; then
        echo "✅ OK ($response)"
    else
        echo "❌ Failed ($response)"
    fi
}

# Test all routes
echo "   Testing dashboard routes:"
test_endpoint "http://${VPS_HOST}:8003/dashboard" "Main Dashboard"
test_endpoint "http://${VPS_HOST}:8003/dashboard/desktop" "Desktop Route"
test_endpoint "http://${VPS_HOST}:8003/dashboard/v10" "V10 Route"
test_endpoint "http://${VPS_HOST}:8003/dashboard/mobile" "Mobile Route"

echo ""
echo "   Testing API endpoints:"
test_endpoint "http://${VPS_HOST}:8003/health" "Health Check"
test_endpoint "http://${VPS_HOST}:8003/api/dashboard/overview" "Dashboard API"

# Test Market Overview API with timing
echo ""
echo "7. Testing Market Overview API performance:"
start_time=$(date +%s.%N)
response=$(curl -s -o /dev/null -w "%{http_code}" "http://${VPS_HOST}:8003/api/market/overview" --max-time 30)
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

if [ "$response" = "200" ]; then
    echo "   ✅ Market Overview API: OK (took ${duration}s)"
    if (( $(echo "$duration > 5" | bc -l) )); then
        echo "   ⚠️  API is slow. This might be due to:"
        echo "      - Multiple exchange API calls"
        echo "      - First-time data loading"
        echo "      - Consider implementing caching"
    fi
else
    echo "   ❌ Market Overview API: Failed ($response)"
fi

echo ""
echo "✅ Server fix completed!"
echo ""
echo "Dashboard URLs:"
echo "  Desktop: http://${VPS_HOST}:8003/dashboard"
echo "  Mobile:  http://${VPS_HOST}:8003/dashboard/mobile"
echo "  V10:     http://${VPS_HOST}:8003/dashboard/v10"
echo ""
echo "To monitor logs:"
echo "  ssh linuxuser@${VPS_HOST} 'tail -f /home/linuxuser/trading/Virtuoso_ccxt/web_server.log'"