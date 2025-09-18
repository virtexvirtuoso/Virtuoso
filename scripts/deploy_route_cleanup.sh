#!/bin/bash

# Deploy route cleanup - remove duplicate mobile dashboard routes
# Keep only clean /mobile route to avoid confusion

echo "=========================================="
echo "🧹 DEPLOYING ROUTE CLEANUP"
echo "=========================================="
echo ""
echo "This deployment removes duplicate routes:"
echo "  ❌ Removing /dashboard/mobile alias routes"
echo "  ✅ Keeping clean /mobile route only"
echo "  🔧 Updating HTML template references"
echo ""

# VPS connection details
VPS_USER="linuxuser"
VPS_IP="${VPS_HOST}"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
echo "📦 Files to deploy:"
echo "  - src/main.py (clean /mobile route)"
echo "  - src/web_server.py (removed /dashboard/mobile)"
echo "  - src/api/routes/gateway_routes.py (removed /dashboard/mobile)"
echo "  - src/dashboard/templates/login_mobile.html (updated links)"
echo "  - src/dashboard/templates/dashboard_selector.html (updated links)"
echo ""

# Deploy files
echo "📤 Deploying route cleanup to VPS..."

# Deploy main application files
echo "  Deploying main.py..."
scp src/main.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/

echo "  Deploying web_server.py..."
scp src/web_server.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/

echo "  Deploying gateway_routes.py..."
scp src/api/routes/gateway_routes.py ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/api/routes/

# Deploy updated templates
echo "  Deploying login_mobile.html..."
scp src/dashboard/templates/login_mobile.html ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/dashboard/templates/

echo "  Deploying dashboard_selector.html..."
scp src/dashboard/templates/dashboard_selector.html ${VPS_USER}@${VPS_IP}:${VPS_PATH}/src/dashboard/templates/

echo ""
echo "✅ Files deployed successfully!"
echo ""

# Restart service
echo "🔄 Restarting virtuoso service..."
ssh ${VPS_USER}@${VPS_IP} "sudo systemctl restart virtuoso.service"

echo ""
echo "⏳ Waiting for service to start..."
sleep 5

# Test the clean route
echo "🧪 Testing clean /mobile route..."
MOBILE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}:8003/mobile)

if [ "$MOBILE_STATUS" == "200" ]; then
    echo "✅ /mobile route working (HTTP $MOBILE_STATUS)"
else
    echo "❌ /mobile route failed (HTTP $MOBILE_STATUS)"
fi

# Test that old route is gone
echo "🧪 Testing that /dashboard/mobile is removed..."
OLD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_IP}:8003/dashboard/mobile)

if [ "$OLD_STATUS" == "404" ]; then
    echo "✅ /dashboard/mobile properly removed (HTTP $OLD_STATUS)"
else
    echo "⚠️ /dashboard/mobile still exists (HTTP $OLD_STATUS)"
fi

# Check service status
echo ""
echo "📊 Checking service status..."
ssh ${VPS_USER}@${VPS_IP} "sudo systemctl status virtuoso.service | head -10"

echo ""
echo "=========================================="
echo "✨ ROUTE CLEANUP COMPLETE!"
echo "=========================================="
echo ""
echo "📋 Changes Made:"
echo "  ✅ Clean /mobile route active"
echo "  ❌ Duplicate /dashboard/mobile routes removed"
echo "  🔗 HTML templates updated to use /mobile"
echo ""
echo "🌐 Mobile Dashboard URL:"
echo "  http://${VPS_IP}:8003/mobile"
echo ""
echo "📊 Test Results:"
echo "  /mobile: HTTP $MOBILE_STATUS"
echo "  /dashboard/mobile: HTTP $OLD_STATUS (should be 404)"
echo ""