#!/bin/bash

# Deploy AlertManager improvements and cleanup to VPS
# This removes refactored components and uses improved main AlertManager

echo "🚀 Deploying AlertManager fixes to VPS..."

VPS_HOST="linuxuser@5.223.63.4"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📦 Step 1: Backing up VPS alert components..."
ssh $VPS_HOST "cd $VPS_PROJECT_PATH && \
    mkdir -p archived_code/refactored_alert_manager && \
    cp -r src/monitoring/components/alerts/* archived_code/refactored_alert_manager/ 2>/dev/null || true"

echo "🔄 Step 2: Syncing improved AlertManager..."
rsync -avz --progress \
    src/monitoring/alert_manager.py \
    $VPS_HOST:$VPS_PROJECT_PATH/src/monitoring/

echo "📝 Step 3: Updating DI registration files..."
rsync -avz --progress \
    src/core/di/registration.py \
    src/core/di/interface_registration.py \
    $VPS_HOST:$VPS_PROJECT_PATH/src/core/di/

echo "🗑️ Step 4: Removing refactored components on VPS..."
ssh $VPS_HOST "cd $VPS_PROJECT_PATH && \
    rm -rf src/monitoring/components/alerts && \
    rm -f src/monitoring/market_monitor_refactored.py && \
    rm -f src/monitoring/test_refactored_components.py && \
    echo 'Refactored components removed'"

echo "🧹 Step 5: Cleaning Python cache..."
ssh $VPS_HOST "cd $VPS_PROJECT_PATH && \
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    echo 'Python cache cleared'"

echo "🔄 Step 6: Restarting services..."
ssh $VPS_HOST "sudo systemctl restart virtuoso.service && \
    echo 'Services restarted'"

echo "✅ Step 7: Verifying deployment..."
ssh $VPS_HOST "cd $VPS_PROJECT_PATH && \
    echo 'Checking for refactored references:' && \
    grep -r 'alert_manager_refactored' src --exclude-dir='__pycache__' 2>/dev/null | wc -l"

echo "📊 Step 8: Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso.service | head -20"

echo "✅ AlertManager fixes deployed successfully!"
echo ""
echo "Summary of changes:"
echo "- Removed refactored AlertManager components"
echo "- Using improved main AlertManager with:"
echo "  • Advanced throttling (5 min for signals, content dedup)"
echo "  • Session reuse for better performance"
echo "  • Automatic memory cleanup"
echo "- Discord status 204 is now properly handled as success"