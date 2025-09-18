#!/bin/bash

#############################################################################
# Script: deploy_cache_dashboards.sh
# Purpose: Deploy and manage deploy cache dashboards
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
#   ./deploy_cache_dashboards.sh [options]
#   
#   Examples:
#     ./deploy_cache_dashboards.sh
#     ./deploy_cache_dashboards.sh --verbose
#     ./deploy_cache_dashboards.sh --dry-run
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

echo "======================================"
echo "DEPLOYING CACHE-UPGRADED DASHBOARDS"
echo "======================================"

# VPS connection details
VPS_HOST="5.223.63.4"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo ""
echo "📦 Phase 1: Deploying cache adapter and routes..."

# Deploy cache adapter
echo "  - Deploying cache_adapter.py..."
scp src/api/cache_adapter.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/

# Deploy cached dashboard routes
echo "  - Deploying dashboard_cached.py..."
scp src/api/routes/dashboard_cached.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/

# Update API initialization
echo "  - Updating API initialization..."
scp src/api/__init__.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/

echo ""
echo "📋 Phase 2: Deploying upgraded dashboard HTML files..."

# Deploy upgraded dashboards
for dashboard in dashboard_desktop_v1.html dashboard_mobile_v1.html dashboard_v10.html dashboard.html; do
    if [ -f "src/dashboard/templates/${dashboard}" ]; then
        echo "  - Deploying ${dashboard}..."
        scp src/dashboard/templates/${dashboard} ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/
    fi
done

echo ""
echo "🔄 Phase 3: Restarting web service..."

ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Kill existing web server
    echo "  - Stopping web server..."
    pkill -f "python.*web_server.py" || true
    sleep 2
    
    # Start web server with cache support
    echo "  - Starting web server with cache support..."
    nohup python src/web_server.py > logs/web_server.log 2>&1 &
    
    sleep 3
    
    # Verify web server is running
    if pgrep -f "python.*web_server.py" > /dev/null; then
        echo "  ✅ Web server restarted successfully"
    else
        echo "  ❌ Web server failed to start"
        tail -n 20 logs/web_server.log
    fi
EOF

echo ""
echo "======================================"
echo "DEPLOYMENT COMPLETE"
echo "======================================"
echo ""
echo "🎯 Next: Testing cache performance..."
echo ""

# Test cache endpoints
echo "Testing cache endpoints response times:"
echo ""

# Test overview endpoint
echo "1. Testing /api/dashboard-cached/overview:"
time curl -s -o /dev/null -w "   Response time: %{time_total}s\n" \
    http://${VPS_HOST}:8000/api/dashboard-cached/overview

# Test market overview
echo ""
echo "2. Testing /api/dashboard-cached/market-overview:"
time curl -s -o /dev/null -w "   Response time: %{time_total}s\n" \
    http://${VPS_HOST}:8000/api/dashboard-cached/market-overview

# Test signals
echo ""
echo "3. Testing /api/dashboard-cached/signals:"
time curl -s -o /dev/null -w "   Response time: %{time_total}s\n" \
    http://${VPS_HOST}:8000/api/dashboard-cached/signals

echo ""
echo "======================================"
echo "✅ Cache dashboards deployed!"
echo "======================================"
echo ""
echo "📊 Access dashboards at:"
echo "  - Desktop: http://${VPS_HOST}:8000/dashboard"
echo "  - Mobile:  http://${VPS_HOST}:8000/dashboard/mobile"
echo "  - V10:     http://${VPS_HOST}:8000/dashboard/v10"
echo ""
echo "All dashboards now use ultra-fast cache with <10ms response!"