#!/bin/bash

echo "🚀 Deploying Mobile Dashboard Final Fixes to VPS..."
echo "==========================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the updated files
echo "📦 Copying updated files..."
scp src/api/routes/dashboard_cached.py $VPS_HOST:$PROJECT_DIR/src/api/routes/
scp scripts/fix_mobile_dashboard_final.py $VPS_HOST:$PROJECT_DIR/scripts/

# Run the fix script on VPS
echo ""
echo "🔧 Running fix script on VPS..."
ssh $VPS_HOST "cd $PROJECT_DIR && echo 'n' | ./venv311/bin/python scripts/fix_mobile_dashboard_final.py"

# Restart web service
echo ""
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

# Test the endpoints
echo ""
echo "🧪 Testing fixed endpoints..."
echo ""

echo "1. Market Breadth Test:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.market_breadth'

echo ""
echo "2. Top Movers Test:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '{gainers: .top_movers.gainers | length, losers: .top_movers.losers | length}'

echo ""
echo "3. First Confluence Score with Price:"
curl -s "http://45.77.40.77:8001/api/dashboard-cached/mobile-data" | jq '.confluence_scores[0] | {symbol, score, price, change_24h}'

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Test mobile dashboard at: http://45.77.40.77:8001/dashboard/mobile"