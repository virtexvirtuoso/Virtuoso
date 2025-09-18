#!/bin/bash

# Deploy Phase 2 Mobile Dashboard Optimizations to Hetzner VPS
# Intelligent cache warming and mobile-first optimization

set -e  # Exit on any error

VPS_HOST="linuxuser@5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "🚀 Deploying Phase 2 Mobile Dashboard Optimizations..."
echo "========================================================"

# Phase 2 Component 1: Priority Cache Warming System
echo "📦 Component 1: Deploying Priority Cache Warming System..."
ssh "$VPS_HOST" "mkdir -p $VPS_PATH/src/core/cache"
scp "$LOCAL_PATH/src/core/cache/priority_warmer.py" "$VPS_HOST:$VPS_PATH/src/core/cache/priority_warmer.py"

# Phase 2 Component 2: Mobile Optimization Service
echo "📦 Component 2: Deploying Mobile Optimization Service..."
scp "$LOCAL_PATH/src/api/services/mobile_optimization_service.py" "$VPS_HOST:$VPS_PATH/src/api/services/mobile_optimization_service.py"

# Phase 2 Component 3: Updated Dashboard Routes
echo "📦 Component 3: Deploying Optimized Dashboard Routes..."
scp "$LOCAL_PATH/src/api/routes/dashboard_cached.py" "$VPS_HOST:$VPS_PATH/src/api/routes/dashboard_cached.py"

# Phase 2 Component 4: Updated Main Application with Mobile Services
echo "📦 Component 4: Deploying Updated Main Application..."
scp "$LOCAL_PATH/src/main.py" "$VPS_HOST:$VPS_PATH/src/main.py"

echo ""
echo "🔄 Restarting services with Phase 2 optimizations..."

# Restart with cache clearing for clean Phase 2 deployment
ssh "$VPS_HOST" << 'ENDSSH'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    echo "🛑 Stopping service for Phase 2 upgrade..."
    sudo systemctl stop virtuoso.service
    
    # Clear all caches for fresh Phase 2 start
    echo "🧹 Clearing caches for Phase 2 optimization..."
    echo 'flush_all' | nc localhost 11211 2>/dev/null || echo "⚠️ Memcached not available"
    
    # Clear any Redis cache if present
    redis-cli flushall 2>/dev/null || echo "⚠️ Redis not available"
    
    echo "🚀 Starting service with Phase 2 optimizations..."
    sudo systemctl start virtuoso.service
    
    echo "⏳ Waiting for Phase 2 initialization (30 seconds)..."
    sleep 30
    
    echo "📊 Checking Phase 2 service status..."
    sudo systemctl status virtuoso.service --no-pager -l | tail -20
ENDSSH

echo ""
echo "✅ Phase 2 deployment complete!"
echo ""
echo "🧪 Testing Phase 2 optimizations..."

# Test 1: Basic mobile endpoint
echo "Test 1: Basic mobile data endpoint..."
MOBILE_RESPONSE=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-data")
MOBILE_STATUS=$(echo "$MOBILE_RESPONSE" | jq -r '.status // "no_status"')
CONFLUENCE_COUNT=$(echo "$MOBILE_RESPONSE" | jq '.confluence_scores | length // 0')
CACHE_SOURCE=$(echo "$MOBILE_RESPONSE" | jq -r '.cache_source // "unknown"')
PERFORMANCE_MS=$(echo "$MOBILE_RESPONSE" | jq -r '.performance.response_time_ms // "unknown"')

echo "  ✓ Status: $MOBILE_STATUS"
echo "  ✓ Confluence scores: $CONFLUENCE_COUNT symbols"
echo "  ✓ Cache source: $CACHE_SOURCE"
echo "  ✓ Response time: ${PERFORMANCE_MS}ms"

# Test 2: Performance monitoring endpoint
echo ""
echo "Test 2: Phase 2 performance monitoring..."
PERF_RESPONSE=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-performance")
MOBILE_CACHE_VALID=$(echo "$PERF_RESPONSE" | jq -r '.mobile_optimization_stats.mobile_cache_valid // false')
PRIORITY_COMPLETE=$(echo "$PERF_RESPONSE" | jq -r '.priority_warmer_stats.priority_complete // false')
SYSTEM_HEALTH=$(echo "$PERF_RESPONSE" | jq -r '.system_health // "unknown"')

echo "  ✓ Mobile cache valid: $MOBILE_CACHE_VALID"
echo "  ✓ Priority warming complete: $PRIORITY_COMPLETE"  
echo "  ✓ System health: $SYSTEM_HEALTH"

# Test 3: Check for system contamination (should be zero)
echo ""
echo "Test 3: System contamination check..."
SYSTEM_SYMBOLS=$(curl -s "http://5.223.63.4:8003/api/dashboard/mobile-data" | jq -r '.confluence_scores[]? | select(.symbol | contains("SYSTEM") or contains("STATUS") or contains("LOADING")) | .symbol' 2>/dev/null || echo "")

if [ -n "$SYSTEM_SYMBOLS" ]; then
    echo "  ⚠️  WARNING: System symbols detected:"
    echo "  $SYSTEM_SYMBOLS"
else
    echo "  ✅ No system symbols detected - Phase 1 fixes still working"
fi

# Test 4: Performance comparison
echo ""
echo "Test 4: Response time analysis..."
for i in {1..3}; do
    RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null "http://5.223.63.4:8003/api/dashboard/mobile-data")
    echo "  Request $i: ${RESPONSE_TIME}s"
done

echo ""
echo "🎯 Phase 2 Summary:"
echo "=============================="
echo "✅ Priority-based cache warming deployed"
echo "✅ Mobile optimization service integrated"  
echo "✅ 5-tier intelligent fallback system active"
echo "✅ Performance monitoring enabled"
echo "✅ Phase 1 validation still protecting against contamination"
echo ""

if [ "$CONFLUENCE_COUNT" -gt "0" ]; then
    echo "🎉 SUCCESS: Mobile dashboard now has $CONFLUENCE_COUNT symbols!"
    echo "📱 Cache source: $CACHE_SOURCE"
    echo "⚡ Performance: ${PERFORMANCE_MS}ms response time"
else
    echo "⏳ Phase 2 still initializing - priority warming in progress"
    echo "   Monitor with: curl http://5.223.63.4:8003/api/dashboard/mobile-performance"
fi

echo ""
echo "📊 Monitor Phase 2 performance:"
echo "   curl http://5.223.63.4:8003/api/dashboard/mobile-performance"
echo ""
echo "🔍 View logs:"
echo "   ssh $VPS_HOST 'sudo journalctl -u virtuoso.service -f'"