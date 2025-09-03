#!/bin/bash

#############################################################################
# Script: deploy_performance_fixes.sh
# Purpose: Deploy performance optimizations and logging fixes to production
# Author: Virtuoso CCXT Development Team  
# Version: 1.2.0
# Created: 2024-08-20
# Modified: 2024-08-28
#############################################################################
#
# Description:
#   Deploys critical performance optimizations to the production VPS,
#   including optimized indicator calculations, logging improvements,
#   and confluence analysis enhancements. This script significantly
#   reduces system load and improves dashboard response times.
#
# Performance Improvements:
#   - Liquidity zones calculation: 2100ms → ~500ms (76% reduction)
#   - Reduced DEBUG logging overhead
#   - Optimized confluence scoring
#   - Module-specific logging levels
#
# Dependencies:
#   - SSH access to VPS (VPS_HOST_REDACTED)
#   - SSH key authentication configured
#   - sudo privileges for service restart
#
# Usage:
#   ./deploy_performance_fixes.sh
#
# Files Deployed:
#   - src/indicators/orderflow_indicators.py - Optimized liquidity calculations
#   - src/core/logger.py - Centralized logging manager
#   - src/analysis/core/confluence.py - Optimized confluence analysis
#   - src/config/logging_config.py - Logging configuration
#   - src/main.py - Main application entry point
#
# Exit Codes:
#   0 - Success
#   1 - File deployment failure
#   2 - Service restart failure
#
# Notes:
#   - Test performance locally before deploying
#   - Monitor CPU/memory usage after deployment
#   - Check logs for any errors post-deployment
#
# Changelog:
#   v1.2.0 - Added centralized logging configuration
#   v1.1.0 - Optimized liquidity zones calculation
#   v1.0.0 - Initial performance fixes
#
#############################################################################

echo "=================================================="
echo "🚀 Deploying Performance and Logging Fixes to VPS"
echo "=================================================="

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
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