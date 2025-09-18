#!/bin/bash
#
# Deploy LSR Fix to VPS
# Ensures Long/Short Ratio data is properly fetched and displayed
#

set -e  # Exit on error

echo "========================================"
echo "   DEPLOYING LSR FIX TO VPS"
echo "========================================"

# Configuration
VPS_HOST="linuxuser@${VPS_HOST}"
PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo ""
echo "Step 1: Syncing updated source files with LSR fixes..."
# Sync the specific files that have LSR fixes
rsync -avz --relative \
    $LOCAL_PATH/./src/core/exchanges/bybit.py \
    $LOCAL_PATH/./src/indicators/sentiment_indicators.py \
    $LOCAL_PATH/./src/core/analysis/confluence.py \
    $LOCAL_PATH/./src/api/routes/dashboard.py \
    $VPS_HOST:$PROJECT_PATH/

echo ""
echo "Step 2: Restarting services..."
ssh $VPS_HOST "sudo systemctl restart virtuoso.service"
sleep 5

echo ""
echo "Step 3: Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso.service | head -20"

echo ""
echo "Step 4: Checking recent logs for LSR..."
ssh $VPS_HOST "sudo journalctl -u virtuoso.service -n 100 | grep -E 'LSR|long_short_ratio' | tail -20" || true

echo ""
echo "========================================"
echo "   LSR FIX DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "Monitor live LSR data:"
echo "ssh vps 'sudo journalctl -u virtuoso.service -f | grep -E \"LSR|long_short\"'"
