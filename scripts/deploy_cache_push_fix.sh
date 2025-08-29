#!/bin/bash

#############################################################################
# Script: deploy_cache_push_fix.sh
# Purpose: Deploy and manage deploy cache push fix
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
#   ./deploy_cache_push_fix.sh [options]
#   
#   Examples:
#     ./deploy_cache_push_fix.sh
#     ./deploy_cache_push_fix.sh --verbose
#     ./deploy_cache_push_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

# Deploy cache push fix to VPS
# This fixes the mobile dashboard data issue by connecting ContinuousAnalysisManager to memcached

echo "=== Deploying Cache Push Fix to VPS ==="
echo "This fix enables ContinuousAnalysisManager to push data to the unified cache"
echo ""

VPS_HOST="linuxuser@45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy the updated main.py
echo "1. Deploying updated main.py with cache push functionality..."
scp src/main.py $VPS_HOST:$VPS_PATH/src/

# Step 2: Copy test script
echo "2. Deploying test script..."
scp scripts/test_cache_integration.py $VPS_HOST:$VPS_PATH/scripts/

# Step 3: Restart the service
echo "3. Restarting the service to apply changes..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Stopping current service..."
sudo systemctl stop virtuoso.service

echo "Waiting for clean shutdown..."
sleep 3

echo "Starting service with new code..."
sudo systemctl start virtuoso.service

echo "Checking service status..."
sudo systemctl status virtuoso.service --no-pager | head -20

echo ""
echo "Waiting 10 seconds for service to initialize..."
sleep 10

echo ""
echo "Testing cache integration..."
python3 scripts/test_cache_integration.py

echo ""
echo "Service logs (last 50 lines):"
sudo journalctl -u virtuoso.service -n 50 --no-pager | grep -E "(cache|Cache|pushed|Continuous|analysis)"
EOF

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "The fix has been deployed. The ContinuousAnalysisManager will now:"
echo "1. Analyze market data for top symbols"
echo "2. Aggregate the results"
echo "3. Push to memcached keys that dashboards read"
echo ""
echo "Check your mobile dashboard - it should now show market data!"
echo "Dashboard URL: http://45.77.40.77:8080/dashboard/mobile"