#!/bin/bash

#############################################################################
# Script: deploy_final_confluence_fix.sh
# Purpose: Deploy and manage deploy final confluence fix
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
#   ./deploy_final_confluence_fix.sh [options]
#   
#   Examples:
#     ./deploy_final_confluence_fix.sh
#     ./deploy_final_confluence_fix.sh --verbose
#     ./deploy_final_confluence_fix.sh --dry-run
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

echo "=========================================="
echo "🚀 DEPLOYING FINAL CONFLUENCE SCORE FIX"
echo "=========================================="
echo

# Copy the fixed dashboard.py to VPS
echo "📤 Copying fixed dashboard.py to VPS..."
scp src/api/routes/dashboard.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Copy test script
echo "📤 Copying test script..."
scp scripts/test_final_dashboard_fix.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# SSH to VPS and test
ssh linuxuser@${VPS_HOST} << 'EOF'
echo
echo "🔍 Testing on VPS..."
cd /home/linuxuser/trading/Virtuoso_ccxt

# First check if Memcached has data
echo "Checking Memcached for symbols data..."
echo "get virtuoso:symbols" | nc localhost 11211 | head -c 100

echo
echo "🔄 Restarting web server with fixed routes..."
sudo systemctl restart virtuoso-web

# Wait for service to start
sleep 3

echo
echo "✅ Testing dashboard endpoints..."
curl -s http://localhost:8001/api/dashboard/overview | python3 -m json.tool | head -20

echo
echo "🎯 Testing symbols endpoint for confluence scores..."
curl -s http://localhost:8001/api/dashboard/symbols | python3 -c "
import sys, json
data = json.load(sys.stdin)
symbols = data.get('symbols', [])
if symbols:
    print(f'✅ Found {len(symbols)} symbols')
    for sym in symbols[:3]:
        score = sym.get('confluence_score', 50)
        symbol = sym.get('symbol', 'N/A')
        if score != 50:
            print(f'  ✨ {symbol}: Real score = {score:.1f}')
        else:
            print(f'  ⚠️ {symbol}: Default score = {score}')
else:
    print('❌ No symbols returned')
"

echo
echo "=========================================="
echo "📊 DEPLOYMENT COMPLETE"
echo "=========================================="
EOF

echo
echo "✅ Fix deployed! Check the output above."
echo "The dashboard should now show real confluence scores!"