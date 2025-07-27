#!/bin/bash

# Simple focused test for core functionality

echo "🧪 SIMPLE VIRTUOSO TEST"
echo "======================="
echo ""

# First ensure server is running
echo "1. Checking server status..."
ssh linuxuser@45.77.40.77 'cd /home/linuxuser/trading/Virtuoso_ccxt && pgrep -f "python.*web_server" > /dev/null || (source venv311/bin/activate && nohup python src/web_server.py > web_server.log 2>&1 & echo "Started new server process")'

# Wait for server startup
echo "   Waiting for server to start..."
sleep 10

echo ""
echo "2. Testing core endpoints:"
echo "   Dashboard: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://45.77.40.77:8003/dashboard)"
echo "   Mobile: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://45.77.40.77:8003/dashboard/mobile)"
echo "   API Overview: $(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://45.77.40.77:8003/api/dashboard/overview)"

echo ""
echo "3. Testing Market Overview API Performance:"

# First call (uncached)
echo -n "   First call (uncached): "
start_time=$(date +%s.%N)
response=$(curl -s --max-time 15 http://45.77.40.77:8003/api/market/overview)
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
    echo "✅ Success in ${duration}s"
    
    # Check if it has optimization fields
    if echo "$response" | grep -q "fetch_time_seconds"; then
        fetch_time=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('fetch_time_seconds', 'N/A'))")
        echo "   Parallel fetch time: ${fetch_time}s"
    fi
else
    echo "❌ Failed"
fi

# Second call (should be cached)
sleep 2
echo -n "   Second call (cached): "
start_time=$(date +%s.%N)
response=$(curl -s --max-time 5 http://45.77.40.77:8003/api/market/overview)
end_time=$(date +%s.%N)
duration=$(echo "$end_time - $start_time" | bc)

if echo "$response" | python3 -m json.tool > /dev/null 2>&1; then
    echo "✅ Success in ${duration}s"
    
    # Check cache status
    cached=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cached', False))" 2>/dev/null || echo "unknown")
    echo "   Cached: ${cached}"
else
    echo "❌ Failed"
fi

echo ""
echo "4. Exchange Manager Status:"
# Check if Exchange Manager is working
response=$(curl -s --max-time 5 http://45.77.40.77:8003/api/market/overview 2>&1)
if echo "$response" | grep -q "Exchange manager not initialized"; then
    echo "   ❌ Exchange Manager NOT initialized"
else
    echo "   ✅ Exchange Manager working"
fi

echo ""
echo "Test complete!"