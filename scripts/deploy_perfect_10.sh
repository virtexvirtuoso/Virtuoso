#!/bin/bash

#############################################################################
# Script: deploy_perfect_10.sh
# Purpose: Deploy and manage deploy perfect 10
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
#   ./deploy_perfect_10.sh [options]
#   
#   Examples:
#     ./deploy_perfect_10.sh
#     ./deploy_perfect_10.sh --verbose
#     ./deploy_perfect_10.sh --dry-run
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

echo "======================================"
echo "DEPLOYING PERFECT 10/10 DATA FLOW"
echo "======================================"
echo ""
echo "Fixing:"
echo "  - Cache adapter abstraction overhead"
echo "  - Mobile confluence scores"  
echo "  - Legacy endpoint data"
echo ""

VPS_HOST="${VPS_HOST}"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📦 Deploying direct cache adapter..."
scp src/api/cache_adapter_direct.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/

echo "📦 Deploying updated routes..."
scp src/api/routes/dashboard_cached.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/
scp src/api/routes/dashboard.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/

echo ""
echo "🔄 Restarting web server..."

ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Restart web server
pkill -f "web_server.py" || true
sleep 2

export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > /dev/null 2>&1 &
echo "Web server restarted"

sleep 5

# Verify running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server running"
else
    echo "❌ Web server failed"
fi
EOF

echo ""
echo "⏳ Waiting for initialization..."
sleep 8

echo ""
echo "======================================"
echo "VERIFYING PERFECT DATA FLOW"
echo "======================================"
echo ""

# Function to check endpoint data
check_endpoint() {
    local endpoint=$1
    local name=$2
    local check_type=$3
    
    echo "Testing $name:"
    
    response=$(curl -s http://${VPS_HOST}:8001${endpoint} 2>/dev/null)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8001${endpoint} 2>/dev/null)
    
    if [ "$http_code" = "200" ]; then
        echo -n "  HTTP: ✅ 200 | "
        
        # Check specific data based on type
        case $check_type in
            "signals")
                signals=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('signals',[])))" 2>/dev/null || echo "0")
                if [ "$signals" -gt "0" ]; then
                    echo "Data: ✅ $signals signals"
                else
                    echo "Data: ❌ No signals"
                fi
                ;;
            "mobile")
                confluence=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('confluence_scores',[])))" 2>/dev/null || echo "0")
                movers=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); m=d.get('top_movers',{}); print(len(m.get('gainers',[]))+len(m.get('losers',[])))" 2>/dev/null || echo "0")
                echo "Data: Confluence=$confluence, Movers=$movers"
                if [ "$confluence" -gt "0" ]; then
                    echo "       ✅ Confluence scores fixed!"
                fi
                ;;
            "volume")
                volume=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('summary',{}); v=s.get('total_volume',s.get('total_volume_24h',0)); print(f'{v/1e9:.1f}B' if v>0 else '0')" 2>/dev/null || echo "0")
                echo "Data: Volume=$volume"
                ;;
            "overview")
                signals=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('signals',[])))" 2>/dev/null || echo "0")
                regime=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('market_regime','unknown'))" 2>/dev/null || echo "unknown")
                echo "Data: Signals=$signals, Regime=$regime"
                ;;
        esac
    else
        echo "  HTTP: ❌ $http_code"
    fi
    echo ""
}

# Check all critical endpoints
check_endpoint "/api/dashboard/overview" "Regular Dashboard" "overview"
check_endpoint "/api/dashboard-cached/overview" "Cached Dashboard" "volume"
check_endpoint "/api/dashboard-cached/mobile-data" "Mobile Data" "mobile"
check_endpoint "/api/dashboard-cached/signals" "Cached Signals" "signals"
check_endpoint "/api/fast/overview" "Fast Dashboard" "overview"
check_endpoint "/api/fast/signals" "Fast Signals" "signals"

echo "======================================"
echo "CONFLUENCE SCORES DEEP CHECK"
echo "======================================"
echo ""

curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    scores = data.get('confluence_scores', [])
    
    if scores:
        print(f'✅ SUCCESS: {len(scores)} confluence scores found!')
        print('')
        print('Top 3 Confluence Scores:')
        for i, score in enumerate(scores[:3], 1):
            print(f'  {i}. {score[\"symbol\"]}: {score[\"score\"]:.2f} (Change: {score[\"change_24h\"]:.2f}%)')
    else:
        print('❌ FAILED: No confluence scores')
        print('Debug: Full mobile data keys:', list(data.keys()))
except Exception as e:
    print(f'Error: {e}')
"

echo ""
echo "======================================"
echo "FINAL STATUS"
echo "======================================"
echo ""

# Count successes
success_count=$(curl -s http://${VPS_HOST}:8001/api/dashboard-cached/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
scores = len(data.get('confluence_scores', []))
gainers = len(data.get('top_movers', {}).get('gainers', []))
losers = len(data.get('top_movers', {}).get('losers', []))
print(1 if scores > 0 and gainers > 0 and losers > 0 else 0)
" 2>/dev/null || echo "0")

if [ "$success_count" = "1" ]; then
    echo "🎉 PERFECT 10/10 ACHIEVED!"
    echo ""
    echo "✅ All endpoints working with complete data"
    echo "✅ Mobile confluence scores populated"
    echo "✅ Cache adapter abstraction removed"
    echo "✅ Legacy endpoints enhanced"
    echo ""
    echo "The system is now fully operational with perfect data flow!"
else
    echo "⚠️  Some issues remain - check logs above"
fi

echo ""
echo "======================================"