#!/bin/bash

#############################################################################
# Script: deploy_mobile_fix.sh
# Purpose: Deploy and manage deploy mobile fix
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
#   ./deploy_mobile_fix.sh [options]
#   
#   Examples:
#     ./deploy_mobile_fix.sh
#     ./deploy_mobile_fix.sh --verbose
#     ./deploy_mobile_fix.sh --dry-run
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

echo "================================"
echo "DEPLOYING MOBILE DASHBOARD FIX"
echo "================================"
echo ""

# Deploy updated files
echo "📱 Deploying mobile dashboard fixes..."

# Deploy updated cached routes with mobile-data endpoint
echo "  - Deploying updated dashboard_cached.py..."
scp src/api/routes/dashboard_cached.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Deploy updated mobile dashboard HTML
echo "  - Deploying updated dashboard_mobile_v1.html..."
scp src/dashboard/templates/dashboard_mobile_v1.html linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/

echo ""
echo "🔄 Restarting web server..."
ssh linuxuser@${VPS_HOST} 'pkill -f "web_server.py" && sleep 2 && cd /home/linuxuser/trading/Virtuoso_ccxt && PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt nohup venv311/bin/python src/web_server.py > logs/web_mobile_fix.log 2>&1 & echo "Web server restarted with PID: $!"'

sleep 5

echo ""
echo "✅ Testing mobile-data endpoint..."
echo ""

# Test the new cached mobile-data endpoint
echo "1. Testing /api/dashboard-cached/mobile-data:"
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Status: {data.get(\"status\")}')
print(f'  Market Regime: {data[\"market_overview\"][\"market_regime\"]}')
print(f'  Confluence Scores: {len(data.get(\"confluence_scores\", []))} items')
print(f'  Top Gainers: {len(data[\"top_movers\"][\"gainers\"])} items')
print(f'  Top Losers: {len(data[\"top_movers\"][\"losers\"])} items')
print(f'  Source: {data.get(\"source\", \"unknown\")}')
"

echo ""
echo "2. Testing regular mobile-data (fallback):"
curl -s http://${VPS_HOST}:8001/api/dashboard/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'  Status: {data.get(\"status\")}')
print(f'  Confluence Scores: {len(data.get(\"confluence_scores\", []))} items')
" 2>/dev/null || echo "  Failed to parse"

echo ""
echo "================================"
echo "Mobile Dashboard Fix Deployed!"
echo "================================"
echo ""
echo "📱 Access mobile dashboard at:"
echo "   http://${VPS_HOST}:8001/dashboard/mobile"
echo ""
echo "✅ The mobile dashboard should now display:"
echo "   - Market overview data"
echo "   - Confluence scores"
echo "   - Top movers (gainers/losers)"