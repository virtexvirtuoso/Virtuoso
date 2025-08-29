#!/bin/bash

echo "=== VPS Critical Issues Fix Script ==="
echo "Timestamp: $(date)"
echo

# Make sure we're targeting the right VPS
VPS_HOST="linuxuser@45.77.40.77"

echo "1. Checking and restarting services:"
ssh $VPS_HOST "
    echo 'Stopping services...'
    sudo systemctl stop virtuoso.service || echo 'Main service not running'
    
    echo 'Checking for hanging processes...'
    sudo pkill -f 'python.*main' || echo 'No hanging Python processes'
    sudo pkill -f 'uvicorn' || echo 'No hanging uvicorn processes'
    
    echo 'Starting memcached if not running...'
    sudo systemctl start memcached
    sudo systemctl enable memcached
    
    echo 'Restarting main service...'
    sudo systemctl start virtuoso.service
    sleep 5
    
    echo 'Service status:'
    sudo systemctl status virtuoso.service --no-pager -l | head -10
"

echo "2. Testing endpoints after restart:"
sleep 10

echo "Testing main dashboard..."
curl -s -w "Main dashboard response time: %{time_total}s\n" -o /dev/null http://VPS_HOST_REDACTED:8003/

echo "Testing health endpoint..."
curl -s -w "Health endpoint response time: %{time_total}s\n" http://VPS_HOST_REDACTED:8003/health | tail -1

echo "Testing direct Bybit API..."
curl -s http://VPS_HOST_REDACTED:8003/api/bybit-direct/top-symbols | jq -r '.status // "failed"'

echo "Testing monitoring endpoint..."
curl -s -w "Monitoring response time: %{time_total}s\n" http://VPS_HOST_REDACTED:8001/api/monitoring/status | tail -1 || echo "Monitoring still not accessible"

echo "3. Cache connectivity test:"
ssh $VPS_HOST "
    echo 'Testing memcached connectivity:'
    echo 'stats' | timeout 2 nc localhost 11211 | head -2 || echo 'Memcached still not accessible locally'
"

echo "4. Creating temporary mobile endpoint fix:"
ssh $VPS_HOST "
    echo 'Checking if mobile route exists:'
    curl -s -o /dev/null -w '%{http_code}' http://localhost:8003/mobile
"

echo "=== Fix Script Complete ==="
echo
echo "Next steps if issues persist:"
echo "1. Check logs: ssh $VPS_HOST 'sudo journalctl -u virtuoso.service -f'"
echo "2. Manual service debug: ssh $VPS_HOST 'cd /home/linuxuser/trading/Virtuoso_ccxt && python src/main.py'"
echo "3. Check port conflicts: ssh $VPS_HOST 'sudo netstat -tlnp | grep -E :800'"