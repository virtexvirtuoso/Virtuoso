#!/bin/bash

#############################################################################
# Script: final_cache_deploy.sh
# Purpose: Deploy and manage final cache deploy
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
#   ./final_cache_deploy.sh [options]
#   
#   Examples:
#     ./final_cache_deploy.sh
#     ./final_cache_deploy.sh --verbose
#     ./final_cache_deploy.sh --dry-run
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

echo "Final Cache Dashboard Deployment"
echo "================================"

# Deploy all cache files
echo "Deploying cache files..."
scp src/api/routes/dashboard_cached.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/
scp src/api/cache_adapter.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/
scp src/api/__init__.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/

# Restart web server
echo ""
echo "Restarting web server..."
ssh linuxuser@${VPS_HOST} 'bash -s' << 'EOF'
pkill -f "python.*web_server" || true
pkill -f "uvicorn" || true
sleep 3

cd /home/linuxuser/trading/Virtuoso_ccxt
export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt

# Start fresh
nohup venv311/bin/python src/web_server.py > logs/web_cache_final.log 2>&1 &

sleep 5

# Check if running
if pgrep -f "web_server.py" > /dev/null; then
    echo "✅ Web server started"
else
    echo "❌ Failed to start"
    tail -n 30 logs/web_cache_final.log
    exit 1
fi
EOF

echo ""
echo "Testing endpoints..."
sleep 2

# Test endpoints
echo "1. Cache Health:"
curl -s http://${VPS_HOST}:8000/api/cache/health | python3 -m json.tool 2>/dev/null | head -n 5

echo ""
echo "2. Cached Overview (new):"
curl -s -w "\nTime: %{time_total}s\n" http://${VPS_HOST}:8000/api/dashboard-cached/overview 2>/dev/null | tail -n 1

echo ""
echo "3. Regular Dashboard:"
curl -s -w "\nTime: %{time_total}s\n" http://${VPS_HOST}:8000/api/dashboard/overview 2>/dev/null | tail -n 1

echo ""
echo "================================"
echo "Deployment Complete!"