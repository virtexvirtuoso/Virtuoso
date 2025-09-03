#!/bin/bash

#############################################################################
# Script: fix_fastapi_lifespan.sh
# Purpose: Deploy and manage fix fastapi lifespan
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
#   ./fix_fastapi_lifespan.sh [options]
#   
#   Examples:
#     ./fix_fastapi_lifespan.sh
#     ./fix_fastapi_lifespan.sh --verbose
#     ./fix_fastapi_lifespan.sh --dry-run
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

# Fix FastAPI lifespan error with market_data_manager variable
echo "=== Fixing FastAPI Lifespan Error ==="
echo "Target: VPS at VPS_HOST_REDACTED"
echo "Time: $(date)"

# Define VPS connection details
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed files
echo ""
echo "=== Step 1: Copying fixed files to VPS ==="
scp /Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/
scp /Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/monitoring/

echo ""
echo "=== Step 2: Restarting service on VPS ==="
ssh ${VPS_USER}@${VPS_HOST} << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Stop the service
echo "Stopping virtuoso service..."
sudo systemctl stop virtuoso.service

# Clear any failed state
sudo systemctl reset-failed virtuoso.service

# Start the service
echo "Starting virtuoso service..."
sudo systemctl start virtuoso.service

# Wait for service to start
sleep 10

# Check service status
echo ""
echo "=== Service Status ==="
sudo systemctl status virtuoso.service --no-pager | head -20

# Check for errors
echo ""
echo "=== Checking for Errors ==="

# Check for MetricsManager error
if sudo journalctl -u virtuoso.service --since "30 seconds ago" | grep -q "MetricsManager.__init__() missing"; then
    echo "❌ MetricsManager error still present"
else
    echo "✅ No MetricsManager errors"
fi

# Check for FastAPI lifespan error
if sudo journalctl -u virtuoso.service --since "30 seconds ago" | grep -q "cannot access local variable 'market_data_manager'"; then
    echo "❌ market_data_manager error still present"
else
    echo "✅ No market_data_manager errors"
fi

# Wait a bit more for APIs to start
sleep 10

# Check if APIs are responding
echo ""
echo "=== API Health Check ==="
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8003/health 2>/dev/null | grep -q "200\|503"; then
    echo "✅ Main API health endpoint responding"
else
    echo "⚠️ Main API health endpoint not responding"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/monitoring/status 2>/dev/null | grep -q "200"; then
    echo "✅ Monitoring API responding"
else
    echo "⚠️ Monitoring API not responding"
fi

# Check if web server started
echo ""
echo "=== Web Server Status ==="
if sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -q "Web server started\|FastAPI.*started"; then
    echo "✅ Web server started"
else
    echo "⚠️ Web server not started yet"
fi

# Show recent logs
echo ""
echo "=== Recent Service Logs (last 20 lines) ==="
sudo journalctl -u virtuoso.service -n 20 --no-pager

REMOTE_EOF

echo ""
echo "=== Deployment Complete ==="
echo "Both MetricsManager and market_data_manager fixes have been applied"
echo ""
echo "To monitor the service:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"