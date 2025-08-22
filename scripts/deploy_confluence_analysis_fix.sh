#!/bin/bash

echo "🔧 Deploying Confluence Analysis Fix to VPS..."
echo "==============================================="

# Copy updated web server
echo "📤 Copying updated web_server.py..."
scp src/web_server.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/

# Restart web service
echo "🔄 Restarting web service..."
ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && sudo systemctl restart virtuoso-web"

# Wait a moment for restart
echo "⏳ Waiting for service restart..."
sleep 5

# Check service status
echo "✅ Checking service status..."
ssh linuxuser@45.77.40.77 "sudo systemctl status virtuoso-web --no-pager -l"

echo ""
echo "🧪 Testing Analysis Button Endpoints..."
echo "======================================"

# Test confluence breakdown endpoint
echo "Testing /api/confluence/latest:"
curl -s http://45.77.40.77:8001/api/confluence/latest | jq -C '.' || echo "❌ Latest confluence endpoint not responding"

echo ""
echo "Testing /api/dashboard/confluence-analysis/BTCUSDT:"
curl -s "http://45.77.40.77:8001/api/dashboard/confluence-analysis/BTCUSDT" | jq -C '.' || echo "❌ Analysis endpoint not responding"

echo ""
echo "Testing /api/dashboard/confluence-analysis-page:"
curl -s -I "http://45.77.40.77:8001/api/dashboard/confluence-analysis-page?symbol=BTCUSDT" | head -1

echo ""
echo "🎯 Confluence Analysis Fix Deployment Complete!"
echo "✅ Analysis button should now show full terminal breakdown"
echo "📱 Test on mobile dashboard: http://45.77.40.77:8001/dashboard/mobile"