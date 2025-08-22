#!/bin/bash
# Deploy market breadth updates to VPS

echo "🚀 Deploying market breadth updates to VPS..."

# Copy updated files to VPS
echo "📦 Copying updated files..."
scp src/api/cache_adapter_direct.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/
scp src/dashboard/templates/dashboard_mobile_v1.html linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/
scp scripts/add_market_breadth.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# Run market breadth update on VPS
echo "📊 Running market breadth data update..."
ssh linuxuser@45.77.40.77 "cd /home/linuxuser/trading/Virtuoso_ccxt && python scripts/add_market_breadth.py"

# Restart web server to pick up changes
echo "🔄 Restarting web server..."
ssh linuxuser@45.77.40.77 "sudo systemctl restart virtuoso-web"

# Give services time to stabilize
sleep 3

# Test the endpoints
echo "✅ Testing market breadth endpoints..."
echo ""
echo "Testing market overview endpoint:"
curl -s http://45.77.40.77:8080/api/market_overview | python -m json.tool | grep -A5 "market_breadth" || echo "No market breadth data"

echo ""
echo "Testing mobile data endpoint:"
curl -s http://45.77.40.77:8080/api/mobile_data | python -m json.tool | head -20

echo ""
echo "✅ Deployment complete!"
echo "📱 Mobile dashboard: http://45.77.40.77:8080/dashboard/mobile"