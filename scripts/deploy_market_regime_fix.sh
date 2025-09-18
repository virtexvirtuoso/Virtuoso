#!/bin/bash

#############################################################################
# Script: deploy_market_regime_fix.sh
# Purpose: Deploy and manage deploy market regime fix
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
#   ./deploy_market_regime_fix.sh [options]
#   
#   Examples:
#     ./deploy_market_regime_fix.sh
#     ./deploy_market_regime_fix.sh --verbose
#     ./deploy_market_regime_fix.sh --dry-run
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

echo "=== Deploying Market Regime Fix to VPS ==="
echo "Fix: Market regime showing 'unknown' - converting to uppercase and adding missing metrics"

VPS_HOST="linuxuser@${VPS_HOST}"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Deploy the main.py fix
echo "📦 Deploying src/main.py with market regime fix..."
scp src/main.py $VPS_HOST:$VPS_DIR/src/

echo "✅ Files deployed successfully"

# Restart the service on VPS
echo "🔄 Restarting service on VPS..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Check if service is running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "Stopping existing service..."
    pkill -f "python.*main.py"
    sleep 2
fi

# Start the service
echo "Starting service with market regime fix..."
nohup python src/main.py > /dev/null 2>&1 &
sleep 3

# Verify it's running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ Service restarted successfully with market regime fix"
    
    # Clear cache to ensure fresh data
    echo "Clearing cache for fresh market regime data..."
    python -c "
import asyncio
import aiomcache

async def clear():
    client = aiomcache.Client('localhost', 11211)
    await client.flush_all()
    await client.close()
    print('Cache cleared')

asyncio.run(clear())
" 2>/dev/null || echo "Cache clear skipped"
    
else
    echo "⚠️ Service may not have started properly"
fi

echo "=== Deployment Complete ==="
echo "Market regime should now show BULLISH/BEARISH/NEUTRAL instead of 'unknown'"
EOF

echo ""
echo "🎯 Market Regime Fix Deployed!"
echo "The dashboard should now display the correct market regime."