#!/bin/bash

echo "======================================"
echo "VPS CACHE PERFORMANCE MONITOR"
echo "======================================"
echo ""

# Test the API endpoints
echo "Testing API performance with caching..."
echo ""

# Test ticker endpoint (should be cached)
echo "1. Market Tickers Endpoint:"
for i in {1..5}; do
    START=$(date +%s%3N)
    RESPONSE=$(curl -s -w "\n%{http_code}" http://45.77.40.77:8003/api/market/tickers 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    END=$(date +%s%3N)
    DURATION=$((END - START))
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   Request $i: ${DURATION}ms (HTTP $HTTP_CODE)"
    else
        echo "   Request $i: Failed (HTTP $HTTP_CODE)"
    fi
    
    sleep 0.5
done

echo ""
echo "2. Dashboard Mobile Endpoint:"
for i in {1..3}; do
    START=$(date +%s%3N)
    RESPONSE=$(curl -s -w "\n%{http_code}" http://45.77.40.77:8001/api/dashboard/mobile 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    END=$(date +%s%3N)
    DURATION=$((END - START))
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   Request $i: ${DURATION}ms (HTTP $HTTP_CODE)"
    else
        echo "   Request $i: Failed (HTTP $HTTP_CODE)"
    fi
    
    sleep 0.5
done

echo ""
echo "3. System Status:"
ssh linuxuser@45.77.40.77 << 'EOF'
echo "   Memcached: $(systemctl is-active memcached)"
echo "   Memory usage: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   CPU load: $(uptime | awk -F'load average:' '{print $2}')"

# Check cache stats from memcached
echo ""
echo "4. Memcached Statistics:"
echo -e "stats\r\nquit" | nc 127.0.0.1 11211 | grep -E "cmd_get|cmd_set|get_hits|get_misses" | head -4
EOF

echo ""
echo "======================================"
echo "Monitoring complete!"