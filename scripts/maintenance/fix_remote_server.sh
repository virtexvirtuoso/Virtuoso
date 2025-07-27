#!/bin/bash

# Script to fix the remote server issues

echo "🔧 Fixing Virtuoso server issues on 45.77.40.77..."

# First, ensure the server is properly restarted
echo "1. Restarting web server to pick up route changes..."

ssh linuxuser@45.77.40.77 'bash -s' << 'ENDSSH'
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
    status=$(curl -s -o /dev/null -w "%{http_code}" "http://45.77.40.77:8003$path")
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
time_taken=$(curl -s -o /dev/null -w "%{time_total}" "http://45.77.40.77:8003/api/market/overview")
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
echo "  Desktop: http://45.77.40.77:8003/dashboard"
echo "  Mobile:  http://45.77.40.77:8003/dashboard/mobile"
echo "  Legacy:  http://45.77.40.77:8003/dashboard/v10"