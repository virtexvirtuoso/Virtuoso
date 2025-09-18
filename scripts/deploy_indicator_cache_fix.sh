#!/bin/bash
# Deploy indicator cache fix to VPS

echo "🚀 Deploying Indicator Cache Fix to VPS"
echo "======================================"

# VPS connection details
VPS_HOST="linuxuser@VPS_HOST_REDACTED"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
echo "📦 Deploying fixed indicator cache module..."
rsync -avz --progress \
    src/core/cache/indicator_cache.py \
    ${VPS_HOST}:${VPS_DIR}/src/core/cache/

echo ""
echo "🔧 Restarting services on VPS..."
ssh ${VPS_HOST} "cd ${VPS_DIR} && sudo systemctl restart virtuoso-web.service"
sleep 2
ssh ${VPS_HOST} "cd ${VPS_DIR} && sudo systemctl restart virtuoso.service"

echo ""
echo "✅ Checking service status..."
ssh ${VPS_HOST} "sudo systemctl status virtuoso-web.service --no-pager | head -10"

echo ""
echo "📊 Testing technical indicators on VPS..."
ssh ${VPS_HOST} "cd ${VPS_DIR} && curl -s http://localhost:8003/api/dashboard/data | python3 -m json.tool | grep -A 5 'technical'"

echo ""
echo "✅ Indicator cache fix deployed successfully!"
echo "======================================"