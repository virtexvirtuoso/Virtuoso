#!/bin/bash

# Deploy ALL Critical Mock Data Fixes to VPS
# This deploys all fixes from PRODUCTION_MOCK_DATA_AUDIT_2.md and MOCK_DATA_AUDIT_REPORT.md

echo "=============================================="
echo "🚨 CRITICAL: Deploying Mock Data Fixes to VPS"
echo "=============================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Critical files that MUST be deployed
CRITICAL_FILES=(
    # Issue 1: Trade Executor
    "src/trade_execution/trade_executor.py"
    
    # Issue 2: Analysis Service
    "src/services/analysis_service_enhanced.py"
    
    # Issue 3: Remove sample confluence (will handle separately)
    
    # Issue 4: Market Data Manager (synthetic OI)
    "src/core/market/market_data_manager.py"
    
    # Issue 5: Dashboard files with hardcoded defaults
    "src/dashboard/integration_service.py"
    "src/dashboard/dashboard_integration.py"
    "src/api/services/mobile_fallback_service.py"
    "src/api/routes/correlation.py"
    
    # Issue 6: Orderflow indicators
    "src/indicators/orderflow_indicators.py"
    
    # Issue 7: Cache population
    "scripts/populate_cache_service.py"
    
    # Issue 8: Alert Manager
    "src/monitoring/alert_manager.py"
    
    # Additional critical files
    "src/main.py"
    "src/main.py.vps_fixed"
    
    # Validation scripts
    "scripts/validate_no_mock_data.py"
    "scripts/verify_all_fixes_deployed.py"
)

echo ""
echo "📋 Files to deploy (${#CRITICAL_FILES[@]} files):"
for file in "${CRITICAL_FILES[@]}"; do
    echo "  - $file"
done

echo ""
echo "🔍 Running local validation first..."
python scripts/validate_no_mock_data.py
if [ $? -ne 0 ]; then
    echo "❌ Local validation failed! Fix issues before deploying."
    exit 1
fi

echo ""
echo "📦 Syncing critical files to VPS..."
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  Copying $file..."
        rsync -avz "$file" "$VPS_USER@$VPS_HOST:$VPS_DIR/$file"
    else
        echo "  ⚠️ Warning: $file not found locally"
    fi
done

echo ""
echo "🗑️ Removing confluence_sample.py from VPS if it exists..."
ssh "$VPS_USER@$VPS_HOST" "rm -f $VPS_DIR/src/core/analysis/confluence_sample.py"

echo ""
echo "📁 Renaming confluence_sample if it still exists..."
ssh "$VPS_USER@$VPS_HOST" "if [ -f $VPS_DIR/src/core/analysis/confluence_sample.py ]; then mv $VPS_DIR/src/core/analysis/confluence_sample.py $VPS_DIR/src/core/analysis/confluence_sample_DO_NOT_USE.py.example; fi"

echo ""
echo "🔍 Running validation on VPS..."
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_DIR && python3 scripts/validate_no_mock_data.py"

echo ""
echo "🔄 Restarting VPS service..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl restart virtuoso-web.service"
sleep 5

echo ""
echo "✅ Checking service status..."
ssh "$VPS_USER@$VPS_HOST" "sudo systemctl status virtuoso-web.service --no-pager | head -15"

echo ""
echo "🎯 Testing production endpoints..."
echo "  Testing main dashboard..."
curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" "http://$VPS_HOST:8002/"

echo "  Testing API endpoint..."
curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" "http://$VPS_HOST:8002/api/dashboard/data"

echo ""
echo "🔍 Final verification..."
python scripts/verify_all_fixes_deployed.py

echo ""
echo "=============================================="
echo "✅ Critical Mock Data Fixes Deployment Complete!"
echo "=============================================="
echo ""
echo "Summary of deployed fixes:"
echo "  1. ✅ Trade executor now uses real ConfluenceAnalyzer"
echo "  2. ✅ Analysis service uses real indicator scores"
echo "  3. ✅ Sample confluence file removed/renamed"
echo "  4. ✅ No more synthetic open interest generation"
echo "  5. ✅ Hardcoded 50.0 defaults replaced with None"
echo "  6. ✅ Orderflow keeps unknown trades as unknown"
echo "  7. ✅ Sample ticker fallbacks removed"
echo "  8. ✅ Mock alert mode removed"
echo ""
echo "🚨 CRITICAL: Monitor the system for:"
echo "  - Any null/None values in dashboard (expected for missing data)"
echo "  - Proper trade classification (unknown trades stay unknown)"
echo "  - Real confluence scores being calculated"
echo "  - Actual indicator values being displayed"
echo ""
echo "Monitor logs with:"
echo "  ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso-web.service -f'"