#!/bin/bash

# Deploy critical updates to VPS
# Created: 2025-08-19

VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "========================================="
echo "Deploying Critical Updates to VPS"
echo "========================================="
echo ""

# 1. Deploy environment configuration
echo "1. Deploying environment configuration..."
ssh $VPS_HOST "mkdir -p $VPS_DIR/config/env"
scp "$LOCAL_DIR/config/env/.env" "$VPS_HOST:$VPS_DIR/config/env/.env"
echo "   ✅ Environment file deployed"

# 2. Deploy critical Python fixes (only if they have syntax errors)
echo ""
echo "2. Checking and deploying Python fixes..."

# Check and deploy alert_manager.py if needed
if ssh $VPS_HOST "grep -q 'self\.#' $VPS_DIR/src/monitoring/alert_manager.py 2>/dev/null"; then
    echo "   Fixing alert_manager.py syntax errors..."
    scp "$LOCAL_DIR/src/monitoring/alert_manager.py" "$VPS_HOST:$VPS_DIR/src/monitoring/"
    echo "   ✅ alert_manager.py deployed"
else
    echo "   ✅ alert_manager.py already fixed"
fi

# Check and deploy sentiment_indicators.py if needed
if ssh $VPS_HOST "grep -q 'self\.#' $VPS_DIR/src/indicators/sentiment_indicators.py 2>/dev/null"; then
    echo "   Fixing sentiment_indicators.py syntax errors..."
    scp "$LOCAL_DIR/src/indicators/sentiment_indicators.py" "$VPS_HOST:$VPS_DIR/src/indicators/"
    echo "   ✅ sentiment_indicators.py deployed"
else
    echo "   ✅ sentiment_indicators.py already fixed"
fi

# 3. Deploy updated core files
echo ""
echo "3. Deploying updated core files..."
FILES_TO_DEPLOY=(
    "src/core/exchanges/bybit.py"
    "src/core/exchanges/manager.py"
    "src/monitoring/alert_manager.py"
    "src/indicators/base_indicator.py"
    "src/main.py"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    echo "   Deploying $file..."
    scp "$LOCAL_DIR/$file" "$VPS_HOST:$VPS_DIR/$file"
done
echo "   ✅ Core files deployed"

# 4. Check service status
echo ""
echo "4. Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso --no-pager | head -10"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "To restart the service, run:"
echo "ssh $VPS_HOST 'sudo systemctl restart virtuoso'"
echo ""
echo "To monitor logs:"
echo "ssh $VPS_HOST 'sudo journalctl -u virtuoso -f'"