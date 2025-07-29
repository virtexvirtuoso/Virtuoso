#!/bin/bash

# Deploy VWAP fix to VPS
# Usage: ./deploy_vwap_fix.sh

echo "=== Deploying VWAP Fix to VPS ==="
echo "Date: $(date)"

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Local paths
PATCH_FILE="patches/vwap_fix_20250727.patch"
INDICATOR_FILE="src/indicators/price_structure_indicators.py"

# Check if patch file exists
if [ ! -f "$PATCH_FILE" ]; then
    echo "Error: Patch file not found: $PATCH_FILE"
    exit 1
fi

# Check if local indicator file exists
if [ ! -f "$INDICATOR_FILE" ]; then
    echo "Error: Local indicator file not found: $INDICATOR_FILE"
    exit 1
fi

echo "1. Creating backup on VPS..."
ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && cp $INDICATOR_FILE ${INDICATOR_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "2. Creating patches directory and copying patch file to VPS..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $VPS_PATH/patches"
scp $PATCH_FILE $VPS_USER@$VPS_HOST:$VPS_PATH/$PATCH_FILE

echo "3. Copying updated indicator file to VPS..."
scp $INDICATOR_FILE $VPS_USER@$VPS_HOST:$VPS_PATH/$INDICATOR_FILE

echo "4. Restarting Virtuoso service..."
ssh $VPS_USER@$VPS_HOST "sudo systemctl restart virtuoso"

echo "5. Checking service status..."
ssh $VPS_USER@$VPS_HOST "sudo systemctl status virtuoso | head -10"

echo "6. Tailing logs for VWAP entries..."
ssh $VPS_USER@$VPS_HOST "sudo journalctl -u virtuoso -n 50 | grep -i vwap || echo 'No VWAP entries in recent logs'"

echo "=== Deployment Complete ==="
echo "Monitor logs with: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso -f | grep -i vwap'"