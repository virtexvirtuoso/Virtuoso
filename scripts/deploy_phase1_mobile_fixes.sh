#!/bin/bash

# Deploy Phase 1 Mobile Dashboard Fixes to VPS
# Comprehensive backend fixes to eliminate SYSTEM_STATUS contamination

set -e  # Exit on any error

VPS_HOST="linuxuser@5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "🚀 Deploying Phase 1 Mobile Dashboard Fixes..."
echo "=================================="

# Phase 1 Fix 1: Remove SYSTEM_STATUS contamination source
echo "📦 Fix 1: Deploying cache_data_bridge.py fix..."
scp "$LOCAL_PATH/src/core/cache_data_bridge.py" "$VPS_HOST:$VPS_PATH/src/core/cache_data_bridge.py"

# Phase 1 Fix 2: Fix initialization race conditions
echo "📦 Fix 2: Deploying main.py race condition fix..."
scp "$LOCAL_PATH/src/main.py" "$VPS_HOST:$VPS_PATH/src/main.py"

# Phase 1 Fix 3: Add data validation
echo "📦 Fix 3: Deploying symbol validation system..."
ssh "$VPS_HOST" "mkdir -p $VPS_PATH/src/api/validation"
scp "$LOCAL_PATH/src/api/validation/__init__.py" "$VPS_HOST:$VPS_PATH/src/api/validation/__init__.py"
scp "$LOCAL_PATH/src/api/validation/symbol_validator.py" "$VPS_HOST:$VPS_PATH/src/api/validation/symbol_validator.py"

# Update dashboard routes with validation
echo "📦 Deploying updated dashboard routes with validation..."
scp "$LOCAL_PATH/src/api/routes/dashboard_cached.py" "$VPS_HOST:$VPS_PATH/src/api/routes/dashboard_cached.py"

# Phase 1 Fix 4: Direct exchange fallback service
echo "📦 Fix 4: Deploying mobile fallback service..."
ssh "$VPS_HOST" "mkdir -p $VPS_PATH/src/api/services"
scp "$LOCAL_PATH/src/api/services/mobile_fallback_service.py" "$VPS_HOST:$VPS_PATH/src/api/services/mobile_fallback_service.py"

echo ""
echo "🔄 Restarting services on VPS..."

# Restart the systemd service
ssh "$VPS_HOST" << 'ENDSSH'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Stop the service
    sudo systemctl stop virtuoso.service
    echo "✋ Service stopped"
    
    # Clear memcache to remove contaminated data
    echo 'flush_all' | nc localhost 11211 2>/dev/null || echo "⚠️ Memcached not available"
    echo "🧹 Cache cleared"
    
    # Start the service
    sudo systemctl start virtuoso.service
    echo "🚀 Service restarted"
    
    # Wait a moment for startup
    sleep 5
    
    # Check service status
    sudo systemctl status virtuoso.service --no-pager -l
ENDSSH

echo ""
echo "✅ Phase 1 deployment complete!"
echo ""
echo "🧪 Testing endpoints..."

# Test the mobile endpoint
echo "Testing mobile data endpoint..."
MOBILE_RESPONSE=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-data" | jq -r '.status // "no_status"')
echo "Mobile endpoint status: $MOBILE_RESPONSE"

# Check for SYSTEM_STATUS contamination
CONFLUENCE_COUNT=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-data" | jq '.confluence_scores | length')
echo "Confluence scores count: $CONFLUENCE_COUNT"

# Check if any system symbols remain
SYSTEM_SYMBOLS=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-data" | jq -r '.confluence_scores[]? | select(.symbol | contains("SYSTEM") or contains("STATUS") or contains("LOADING")) | .symbol' 2>/dev/null || echo "")

if [ -n "$SYSTEM_SYMBOLS" ]; then
    echo "⚠️  WARNING: System symbols still detected:"
    echo "$SYSTEM_SYMBOLS"
else
    echo "✅ No system symbols detected in response"
fi

echo ""
echo "📊 Phase 1 Summary:"
echo "- Fixed SYSTEM_STATUS contamination source"
echo "- Fixed initialization race conditions" 
echo "- Added comprehensive symbol validation"
echo "- Implemented direct exchange fallback"
echo ""
echo "🎯 Next: Monitor logs for successful data flow"
echo "   sudo journalctl -u virtuoso.service -f"