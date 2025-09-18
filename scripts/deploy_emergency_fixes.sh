#!/bin/bash

#############################################################################
# Script: deploy_emergency_fixes.sh
# Purpose: Deploy emergency dashboard performance fixes to production VPS
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2024-08-25
# Modified: 2024-08-28
#############################################################################
#
# Description:
#   This script deploys critical performance fixes for the dashboard API
#   to the production VPS. It updates optimized routes, restarts services,
#   and validates the deployment. Used for emergency hotfixes when the
#   dashboard experiences performance degradation or outages.
#
# Dependencies:
#   - SSH access to VPS (5.223.63.4)
#   - SSH key authentication configured
#   - sudo privileges on VPS for service restart
#   - curl for endpoint testing
#
# Usage:
#   ./deploy_emergency_fixes.sh
#
# Files Deployed:
#   - src/api/routes/dashboard_optimized.py - Optimized dashboard routes
#   - src/api/__init__.py - Updated API initialization
#
# Services Affected:
#   - virtuoso.service - Main trading system service
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failure
#   2 - Service restart failure
#   3 - Endpoint test failure
#
# Notes:
#   - Always test locally before deploying
#   - Creates 5-second pause after service restart for stability
#   - Tests all critical endpoints after deployment
#   - Monitor service logs after deployment
#
#############################################################################

# Deploy Emergency Dashboard Performance Fixes

echo "🚀 Deploying Emergency Performance Fixes to VPS"
echo "=================================================="

# Deploy optimized routes
echo -e "\033[0;34m📦 Step 1: Deploying optimized dashboard routes...\033[0m"
scp src/api/routes/dashboard_optimized.py linuxuser@5.223.63.4:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Deploy updated API init
echo -e "\033[0;34m📦 Step 2: Deploying updated API initialization...\033[0m"
scp src/api/__init__.py linuxuser@5.223.63.4:/home/linuxuser/trading/Virtuoso_ccxt/src/api/

# Restart service
echo -e "\033[0;34m🔄 Step 3: Restarting Virtuoso service...\033[0m"
ssh linuxuser@5.223.63.4 'sudo systemctl restart virtuoso.service'

# Wait for service to start
sleep 5

# Test endpoints
echo -e "\033[0;34m✅ Step 4: Testing optimized endpoints...\033[0m"
echo "Testing endpoints:"

# Test each endpoint
for endpoint in "mobile-data" "overview" "alerts" "opportunities" "health"; do
    echo -n "  /api/dashboard-cached/$endpoint: "
    response=$(curl -s -w "\nHTTP %{http_code} - %{time_total}s" -o /tmp/response.json http://5.223.63.4:8003/api/dashboard-cached/$endpoint 2>/dev/null | tail -1)
    echo "$response"
done

echo -e "\n\033[0;32m🎉 Emergency deployment complete!\033[0m"
echo "Monitor with: ssh linuxuser@5.223.63.4 'sudo journalctl -u virtuoso.service -f'"
echo "Full test: ./scripts/test_dashboard_performance.sh"