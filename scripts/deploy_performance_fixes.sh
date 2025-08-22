#!/bin/bash

echo "=================================================="
echo "🚀 Deploying Performance and Logging Fixes to VPS"
echo "=================================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
FILES_TO_DEPLOY=(
    "src/indicators/orderflow_indicators.py"
    "src/core/logger.py"
    "src/analysis/core/confluence.py"
    "src/config/logging_config.py"
    "src/main.py"
)

echo -e "\n📦 Files to deploy:"
for file in "${FILES_TO_DEPLOY[@]}"; do
    echo "   - $file"
done

echo -e "\n📤 Deploying files to VPS..."
for file in "${FILES_TO_DEPLOY[@]}"; do
    echo -n "   Copying $file... "
    scp "$file" "$VPS_USER@$VPS_HOST:$VPS_PATH/$file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅"
    else
        echo "❌ Failed"
    fi
done

echo -e "\n🔄 Restarting Virtuoso service on VPS..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl restart virtuoso.service" 2>/dev/null

echo -e "\n📊 Checking service status..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl status virtuoso.service --no-pager | head -15"

echo -e "\n=================================================="
echo "✅ Deployment complete!"
echo ""
echo "📝 Summary of changes:"
echo "   1. Optimized liquidity_zones calculation (2100ms → ~500ms expected)"
echo "   2. Reduced DEBUG logging to INFO level"
echo "   3. Added centralized logging configuration"
echo "   4. Module-specific log levels for verbose components"
echo ""
echo "🔍 To monitor the logs:"
echo "   ssh $VPS_USER@$VPS_HOST"
echo "   sudo journalctl -u virtuoso.service -f"
echo "=================================================="