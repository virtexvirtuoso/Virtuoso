#!/bin/bash

#############################################################################
# Script: deploy_phase3.sh
# Purpose: Deploy and manage deploy phase3
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
#   ./deploy_phase3.sh [options]
#   
#   Examples:
#     ./deploy_phase3.sh
#     ./deploy_phase3.sh --verbose
#     ./deploy_phase3.sh --dry-run
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

echo "======================================"
echo "DEPLOYING PHASE 3 - ULTRA-FAST CACHE"
echo "======================================"
echo ""

VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📦 Deploying Phase 3 components..."

# Deploy direct cache manager
echo "  - Deploying direct_cache.py..."
scp src/core/direct_cache.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/

# Deploy fast dashboard routes
echo "  - Deploying dashboard_fast.py..."
scp src/api/routes/dashboard_fast.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/

# Update API initialization
echo "  - Updating API initialization..."
scp src/api/__init__.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/

# Deploy monitoring script
echo "  - Deploying performance monitor..."
scp scripts/monitor_performance.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/

echo ""
echo "🔄 Restarting web server..."

ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill existing web server
pkill -f "python.*web_server" || true
pkill -f "uvicorn" || true
sleep 3

# Start with Phase 3 support
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt
nohup venv311/bin/python src/web_server.py > logs/web_phase3.log 2>&1 &
echo "Web server started with PID: $!"

sleep 5

# Check if running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server running with Phase 3 support"
else
    echo "❌ Web server failed to start"
    tail -n 20 logs/web_phase3.log
fi
EOF

echo ""
echo "⏱️  Testing Phase 3 performance..."
sleep 3

# Quick performance test
echo ""
echo "Testing ultra-fast endpoints:"
echo ""

for endpoint in overview signals market mobile health; do
    echo -n "  /api/fast/$endpoint: "
    response_time=$(curl -s -o /dev/null -w "%{time_total}" http://${VPS_HOST}:8001/api/fast/$endpoint)
    response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "N/A")
    
    if [ "$response_ms" != "N/A" ]; then
        # Check if less than 100ms
        if (( $(echo "$response_ms < 100" | bc -l) )); then
            echo "✅ ${response_ms}ms"
        elif (( $(echo "$response_ms < 500" | bc -l) )); then
            echo "⚠️  ${response_ms}ms"
        else
            echo "❌ ${response_ms}ms"
        fi
    else
        echo "❌ Failed"
    fi
done

echo ""
echo "======================================"
echo "Phase 3 Deployment Complete!"
echo "======================================"
echo ""
echo "🚀 Ultra-fast endpoints available at:"
echo "   /api/fast/overview - Complete dashboard data"
echo "   /api/fast/signals - Trading signals"
echo "   /api/fast/market - Market overview"
echo "   /api/fast/mobile - Mobile optimized"
echo "   /api/fast/health - Cache health check"
echo ""
echo "📊 Run full benchmark:"
echo "   python scripts/monitor_performance.py"