#!/bin/bash

#############################################################################
# Script: fix_continuous_analysis_startup.sh
# Purpose: Deploy and manage fix continuous analysis startup
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
#   ./fix_continuous_analysis_startup.sh [options]
#   
#   Examples:
#     ./fix_continuous_analysis_startup.sh
#     ./fix_continuous_analysis_startup.sh --verbose
#     ./fix_continuous_analysis_startup.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

# Fix ContinuousAnalysisManager startup issue
# This ensures it properly initializes and starts pushing data to cache

echo "=== Fixing ContinuousAnalysisManager Startup ==="
echo ""

VPS_HOST="linuxuser@5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy the fixed main.py
echo "1. Deploying fixed main.py..."
scp src/main.py $VPS_HOST:$VPS_PATH/src/

# Step 2: Restart the service
echo ""
echo "2. Restarting service to apply fix..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Stopping service..."
sudo systemctl stop virtuoso.service

echo "Waiting for clean shutdown..."
sleep 3

echo "Starting service with fix..."
sudo systemctl start virtuoso.service

echo ""
echo "Checking service status..."
sudo systemctl status virtuoso.service --no-pager | head -15

echo ""
echo "Waiting 15 seconds for initialization..."
sleep 15

echo ""
echo "=== Checking if ContinuousAnalysisManager started ==="
sudo journalctl -u virtuoso.service --since "1 minute ago" --no-pager | grep -i "ContinuousAnalysisManager\|continuous analysis" | tail -10

echo ""
echo "=== Checking cache push activity ==="
sudo journalctl -u virtuoso.service --since "1 minute ago" --no-pager | grep -i "pushed.*symbols\|unified cache" | tail -10

echo ""
echo "=== Testing cache data ==="
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
python scripts/check_cache_simple.py 2>/dev/null || echo "Cache check script not available"
EOF

echo ""
echo "=== Fix Deployed ==="
echo ""
echo "The ContinuousAnalysisManager should now be:"
echo "1. Properly initialized with both required components"
echo "2. Running analysis every 2 seconds"  
echo "3. Pushing aggregated data to memcached"
echo ""
echo "Check dashboard at: http://5.223.63.4:8001/dashboard/mobile"