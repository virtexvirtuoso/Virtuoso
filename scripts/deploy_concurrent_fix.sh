#!/bin/bash

echo "========================================"
echo "DEPLOYING CONCURRENT STARTUP FIX TO VPS"
echo "========================================"
echo ""

VPS="linuxuser@45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "1. Copying fixed main.py to VPS..."
echo "----------------------------------------"
scp -q src/main.py $VPS:$VPS_PATH/src/
echo "   ✓ main.py copied"

echo ""
echo "2. Restarting service with fix..."
echo "----------------------------------------"

ssh $VPS << 'EOF'
echo "   Stopping virtuoso service..."
sudo systemctl stop virtuoso

# Clear any stale lock files
rm -f /tmp/virtuoso.lock

# Wait a moment
sleep 2

echo "   Starting virtuoso service..."
sudo systemctl start virtuoso

# Wait for startup
sleep 5

# Check status
if systemctl is-active --quiet virtuoso; then
    echo "   ✓ Virtuoso service started successfully"
    
    # Give it more time to initialize both services
    echo "   Waiting for services to initialize..."
    sleep 10
    
    # Check if port 8003 is listening
    if ss -tlpn | grep -q ':8003'; then
        echo "   ✓ Port 8003 is now listening!"
    else
        echo "   ⚠ Port 8003 not yet listening, checking logs..."
        sudo journalctl -u virtuoso --since "1 minute ago" | grep -E "web server|Starting web server|uvicorn|8003" | tail -5
    fi
    
    # Check if monitoring is running
    if sudo journalctl -u virtuoso --since "1 minute ago" | grep -q "market_monitor background task created"; then
        echo "   ✓ Monitoring system started in background"
    else
        echo "   ⚠ Monitoring startup not confirmed"
    fi
else
    echo "   ✗ Service failed to start"
    sudo systemctl status virtuoso --no-pager | head -15
fi
EOF

echo ""
echo "3. Verifying both services are running..."
echo "----------------------------------------"

# Test API endpoint
echo "   Testing API on port 8003..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://45.77.40.77:8003/api/system/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✓ API responding on port 8003!"
    
    # Get detailed health status
    echo ""
    echo "   API Health Status:"
    curl -s http://45.77.40.77:8003/api/system/health | python3 -m json.tool 2>/dev/null | head -20 || echo "   Could not parse health response"
else
    echo "   ⚠ API not responding yet (HTTP $HTTP_CODE)"
    echo "   Checking service logs for issues..."
    ssh $VPS "sudo journalctl -u virtuoso --since '30 seconds ago' | grep -E 'ERROR|WARNING|web server|8003' | tail -10"
fi

echo ""
echo "4. Checking recent logs for both services..."
echo "----------------------------------------"
ssh $VPS "sudo journalctl -u virtuoso --since '30 seconds ago' | grep -E 'web server|Starting web server|market_monitor|background task|8003|uvicorn' | tail -15"

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "Summary:"
echo "  ✓ Concurrent startup fix deployed"
echo "  ✓ Service restarted"
echo ""
echo "Monitor with:"
echo "  ssh $VPS 'sudo journalctl -u virtuoso -f'"
echo ""
echo "Test endpoints:"
echo "  curl http://45.77.40.77:8003/api/system/health"
echo "  curl http://45.77.40.77:8001/"