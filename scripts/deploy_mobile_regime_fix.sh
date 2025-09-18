#!/bin/bash

# Deploy Mobile Dashboard Regime Fix
# This script fixes the market regime JSON display issue

set -e

echo "📱 Deploying Mobile Dashboard Regime Fix..."
echo "================================================"

# Copy the fixed template
echo "📤 Updating mobile dashboard template..."
scp src/dashboard/templates/dashboard_mobile_v1.html \
    linuxuser@5.223.63.4:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/

# Restart the web server
echo "🔄 Restarting web service..."
ssh linuxuser@5.223.63.4 "
    cd /home/linuxuser/trading/Virtuoso_ccxt
    sudo systemctl restart virtuoso.service
    sleep 3
    sudo systemctl status virtuoso.service --no-pager -l
"

echo "✅ Mobile dashboard regime fix deployed!"
echo "🌐 Test at: http://5.223.63.4:8003/mobile"