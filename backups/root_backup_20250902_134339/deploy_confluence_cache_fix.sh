#!/bin/bash

# Deploy Confluence Caching Fix to Hetzner VPS
# This script deploys the confluence caching integration fix

set -e  # Exit on any error

echo "🚀 Deploying Confluence Caching Fix to Hetzner VPS..."
echo "=================================================="

# VPS connection details
VPS_HOST="VPS_HOST_REDACTED"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📡 Connecting to VPS: $VPS_USER@$VPS_HOST"

# Step 1: Upload the modified files
echo "📤 Uploading modified files..."

# Upload the fixed signal processor
scp src/monitoring/signal_processor.py $VPS_USER@$VPS_HOST:$VPS_PATH/src/monitoring/

# Upload the confluence cache service
scp src/core/cache/confluence_cache_service.py $VPS_USER@$VPS_HOST:$VPS_PATH/src/core/cache/

echo "✅ Files uploaded successfully"

# Step 2: Create cache directory and __init__.py if needed on VPS
echo "📁 Setting up cache directory on VPS..."
ssh $VPS_USER@$VPS_HOST << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    mkdir -p src/core/cache
    if [ ! -f src/core/cache/__init__.py ]; then
        echo "# Cache package" > src/core/cache/__init__.py
        echo "✅ Created cache package __init__.py"
    fi
EOF

# Step 3: Check if virtuoso.service is running
echo "🔍 Checking service status..."
SERVICE_STATUS=$(ssh $VPS_USER@$VPS_HOST "sudo systemctl is-active virtuoso.service" || echo "inactive")

if [ "$SERVICE_STATUS" = "active" ]; then
    echo "🔄 Service is running, restarting..."
    ssh $VPS_USER@$VPS_HOST "sudo systemctl restart virtuoso.service"
    
    # Wait a moment for service to restart
    sleep 5
    
    # Check if restart was successful
    NEW_STATUS=$(ssh $VPS_USER@$VPS_HOST "sudo systemctl is-active virtuoso.service" || echo "failed")
    if [ "$NEW_STATUS" = "active" ]; then
        echo "✅ Service restarted successfully"
    else
        echo "❌ Service restart failed"
        ssh $VPS_USER@$VPS_HOST "sudo systemctl status virtuoso.service --no-pager -l"
        exit 1
    fi
else
    echo "🔴 Service is not running, starting..."
    ssh $VPS_USER@$VPS_HOST "sudo systemctl start virtuoso.service"
    
    # Wait a moment for service to start
    sleep 5
    
    # Check if start was successful
    NEW_STATUS=$(ssh $VPS_USER@$VPS_HOST "sudo systemctl is-active virtuoso.service" || echo "failed")
    if [ "$NEW_STATUS" = "active" ]; then
        echo "✅ Service started successfully"
    else
        echo "❌ Service start failed"
        ssh $VPS_USER@$VPS_HOST "sudo systemctl status virtuoso.service --no-pager -l"
        exit 1
    fi
fi

# Step 4: Monitor logs for a few seconds to check for errors
echo "📋 Monitoring logs for startup errors..."
ssh $VPS_USER@$VPS_HOST "timeout 10 sudo journalctl -u virtuoso.service -f --since '5 seconds ago'" || true

echo ""
echo "=================================================="
echo "✅ Confluence Caching Fix Deployment Complete!"
echo ""
echo "🔧 What was deployed:"
echo "   - Fixed signal processor with confluence caching"
echo "   - Confluence cache service integration"
echo "   - Proper key format: confluence:breakdown:{symbol}"
echo "   - Includes interpretations and component breakdowns"
echo ""
echo "🌐 Test endpoints:"
echo "   - Mobile data: http://VPS_HOST_REDACTED:8003/api/dashboard/mobile"
echo "   - Health check: http://VPS_HOST_REDACTED:8003/health"
echo "   - Monitoring: http://VPS_HOST_REDACTED:8001/api/monitoring/status"
echo ""
echo "📊 Expected improvements:"
echo "   - Mobile-data endpoint should now return confluence scores"
echo "   - Cache keys confluence:breakdown:{symbol} should be populated"
echo "   - Confluence breakdowns include interpretations"
echo ""

# Final health check
echo "🏥 Final health check..."
HEALTH_CHECK=$(ssh $VPS_USER@$VPS_HOST "curl -s http://localhost:8003/health" | head -c 100 || echo "Health check failed")
echo "   Response: $HEALTH_CHECK"

echo "🎉 Deployment completed successfully!"