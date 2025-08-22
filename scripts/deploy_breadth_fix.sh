#!/bin/bash

echo "🔧 Deploying Market Breadth Naming Fix..."
echo "========================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the updated version
echo "📤 Deploying updated mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_updated.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "📱 Improvements Made:"
echo "   • Compact view: 'Breadth' → 'Bulls %' (clearer indicator)"
echo "   • Expanded view: 'Market Breadth' → 'Up vs Down Markets'"
echo "   • Hint text: 'Advancers' → 'Bullish' (more intuitive)"
echo ""
echo "🎯 Result: No redundancy, clearer terminology!"
echo ""
echo "Access at: http://45.77.40.77:8001/dashboard/mobile"