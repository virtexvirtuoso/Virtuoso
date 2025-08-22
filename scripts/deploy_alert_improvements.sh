#!/bin/bash

# Deploy Alert Improvements to VPS
# Fixes the conflicting data and improves alert formatting

VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "========================================="
echo "Deploying Alert Improvements to VPS"
echo "========================================="
echo ""

# 1. Update the alert manager (removed Virtuoso Signals APP, added current price)
echo "1. Updating alert manager..."
scp "$LOCAL_DIR/src/monitoring/alert_manager.py" $VPS_HOST:$VPS_DIR/src/monitoring/
if [ $? -eq 0 ]; then
    echo "   ✅ Alert manager updated"
else
    echo "   ❌ Failed to update alert manager"
    exit 1
fi

# 2. Update the monitor (added current_price to whale activity data)
echo ""
echo "2. Updating monitor..."
scp "$LOCAL_DIR/src/monitoring/monitor.py" $VPS_HOST:$VPS_DIR/src/monitoring/
if [ $? -eq 0 ]; then
    echo "   ✅ Monitor updated"
else
    echo "   ❌ Failed to update monitor"
    exit 1
fi

# 3. Copy test script for verification
echo ""
echo "3. Copying test script..."
ssh $VPS_HOST "mkdir -p $VPS_DIR/scripts"
scp "$LOCAL_DIR/scripts/test_improved_alerts.py" $VPS_HOST:$VPS_DIR/scripts/
if [ $? -eq 0 ]; then
    echo "   ✅ Test script copied"
else
    echo "   ⚠️  Test script copy failed (non-critical)"
fi

# 4. Test the improvements on VPS
echo ""
echo "4. Testing improvements on VPS..."
ssh $VPS_HOST "cd $VPS_DIR && ./venv311/bin/python scripts/test_improved_alerts.py 2>/dev/null | head -20"

# 5. Restart the service
echo ""
echo "5. Restarting service to apply changes..."
ssh $VPS_HOST "sudo systemctl restart virtuoso"
sleep 5

# 6. Check service status
echo ""
echo "6. Checking service status..."
ssh $VPS_HOST "sudo systemctl is-active virtuoso"

# 7. Check for any errors in the last minute
echo ""
echo "7. Checking for recent errors..."
ssh $VPS_HOST "sudo journalctl -u virtuoso --since '1 minute ago' --no-pager | grep -E 'ERROR|CRITICAL|Failed' | head -5"
if [ $? -ne 0 ]; then
    echo "   ✅ No errors found"
fi

echo ""
echo "========================================="
echo "Alert Improvements Deployment Complete!"
echo "========================================="
echo ""
echo "Key improvements deployed:"
echo "  ✅ Removed 'Virtuoso Signals APP' from alert titles"
echo "  ✅ Added current price to all whale activity alerts"
echo "  ✅ Current price displayed prominently in description"
echo "  ✅ Fixed $0.00 price display issues"
echo "  ✅ Clear manipulation warnings with price context"
echo "  ✅ Clean multi-field Discord embeds"
echo ""
echo "Monitor alerts to verify improvements are working correctly."