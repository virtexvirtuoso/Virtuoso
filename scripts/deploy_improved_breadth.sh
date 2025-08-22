#!/bin/bash

echo "🎨 Deploying Improved Market Breadth Visualization..."
echo "===================================================="

VPS_HOST="linuxuser@45.77.40.77"
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Backup current version on VPS
echo "📦 Backing up current version on VPS..."
ssh $VPS_HOST "cp $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html $PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1_backup_$(date +%Y%m%d_%H%M%S).html"

# Copy the improved version
echo "📤 Deploying improved mobile dashboard..."
scp src/dashboard/templates/dashboard_mobile_v1_improved.html $VPS_HOST:$PROJECT_DIR/src/dashboard/templates/dashboard_mobile_v1.html

# Restart web service
echo "🔄 Restarting web service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-web.service"

# Wait for service to start
sleep 3

echo ""
echo "✅ Deployment Complete!"
echo ""
echo "🎨 Visual Improvements Made:"
echo "   • Market sentiment icon (📈/📉/➡️) shows at-a-glance market direction"
echo "   • Visual percentage bar with bulls (green) vs bears (red)"
echo "   • Clear 'Bulls Leading/Bears Leading/Market Balanced' label"
echo "   • Rising/falling terminology instead of up/down"
echo "   • Live indicator shows real-time updates"
echo "   • Smooth animations for all transitions"
echo ""
echo "📱 Access the improved dashboard at:"
echo "   http://45.77.40.77:8001/dashboard/mobile"
echo ""
echo "💡 Features:"
echo "   • Clearer visualization of market sentiment"
echo "   • Easy-to-understand terminology"
echo "   • Professional trading dashboard appearance"
echo "   • Mobile-optimized for quick market assessment"