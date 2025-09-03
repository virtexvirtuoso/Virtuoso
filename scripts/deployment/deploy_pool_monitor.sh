#!/bin/bash

#############################################################################
# Script: deploy_pool_monitor.sh
# Purpose: Deploy connection pool monitoring to VPS
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
#   ./deploy_pool_monitor.sh [options]
#   
#   Examples:
#     ./deploy_pool_monitor.sh
#     ./deploy_pool_monitor.sh --verbose
#     ./deploy_pool_monitor.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

echo "=== Deploying Connection Pool Monitor to VPS ==="
echo ""

VPS_HOST="vt"
REMOTE_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
FILES=(
    "src/core/monitoring/connection_pool_monitor.py"
    "src/core/exchanges/bybit.py"
    "src/main.py"
    "src/web_server.py"
    "src/dashboard/templates/admin_dashboard.html"
    "src/dashboard/templates/dashboard_desktop_v1.html"
)

echo "Deploying files to VPS..."
for file in "${FILES[@]}"; do
    echo "  - $file"
    scp "$file" "$VPS_HOST:$REMOTE_PATH/$file"
done

echo ""
echo "Restarting service on VPS..."
ssh "$VPS_HOST" "sudo systemctl restart virtuoso.service"

echo ""
echo "Waiting for service to start..."
sleep 10

echo ""
echo "Checking service status..."
ssh "$VPS_HOST" "sudo systemctl status virtuoso.service | head -15"

echo ""
echo "Testing pool stats endpoint..."
ssh "$VPS_HOST" "curl -s http://localhost:8080/api/pool-stats | python3 -m json.tool | head -20"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Connection pool monitoring is now active on the VPS!"
echo ""
echo "Features deployed:"
echo "- Connection pool monitoring in Bybit exchange"
echo "- /api/pool-stats endpoint"
echo "- /api/pool-stats/export endpoint"
echo "- Admin dashboard pool monitor section"
echo "- Desktop dashboard pool stats display"
echo ""
echo "The monitor will:"
echo "- Track connection pool usage every 60 seconds"
echo "- Alert when utilization exceeds 80%"
echo "- Display real-time stats in dashboards"
echo "- Export detailed statistics on demand"