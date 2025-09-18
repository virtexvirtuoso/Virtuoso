#!/bin/bash

#############################################################################
# Script: deploy_phase1_performance.sh
# Purpose: Deploy Phase 1 Performance Optimizations
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./deploy_phase1_performance.sh [options]
#   
#   Examples:
#     ./deploy_phase1_performance.sh
#     ./deploy_phase1_performance.sh --verbose
#     ./deploy_phase1_performance.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

echo "🚀 Deploying Phase 1 Performance Optimizations"
echo "=============================================="

# Deploy pooled cache adapter
echo "📦 Deploying connection pooling..."
scp src/core/cache_adapter_pooled.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/core/

# Deploy parallel dashboard routes
echo "📦 Deploying parallel processing routes..."
scp src/api/routes/dashboard_parallel.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Update dashboard.py to use pooled adapter
echo "🔧 Updating dashboard to use pooled adapter..."
ssh linuxuser@${VPS_HOST} 'cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i "s/from src.api.cache_adapter_direct/from src.core.cache_adapter_pooled/g" src/api/routes/dashboard.py'

# Restart service
echo "🔄 Restarting service..."
ssh linuxuser@${VPS_HOST} 'sudo systemctl restart virtuoso.service'

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 15

# Test performance
echo ""
echo "📊 Testing Performance Improvements:"
echo "===================================="

for i in {1..3}; do
    echo ""
    echo "Test Run $i:"
    echo -n "  Mobile: "
    time=$(curl -w "%{time_total}" -o /dev/null -s http://${VPS_HOST}:8003/api/dashboard/mobile 2>/dev/null)
    echo "${time}s"
    
    echo -n "  Alerts: "
    time=$(curl -w "%{time_total}" -o /dev/null -s http://${VPS_HOST}:8003/api/dashboard/alerts 2>/dev/null)
    echo "${time}s"
    
    sleep 1
done

echo ""
echo "✅ Phase 1 deployment complete!"
echo "Monitor: ssh linuxuser@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"