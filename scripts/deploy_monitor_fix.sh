#!/bin/bash

#############################################################################
# Script: deploy_monitor_fix.sh
# Purpose: Deploy and manage deploy monitor fix
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
#   ./deploy_monitor_fix.sh [options]
#   
#   Examples:
#     ./deploy_monitor_fix.sh
#     ./deploy_monitor_fix.sh --verbose
#     ./deploy_monitor_fix.sh --dry-run
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

# Deploy monitor.py fix to VPS
echo "🚀 Deploying monitor.py fix to VPS..."

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Local file path
LOCAL_FILE="/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py"

# Check if local file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Error: Local monitor.py not found at $LOCAL_FILE"
    exit 1
fi

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cp ${VPS_PATH}/src/monitoring/monitor.py ${VPS_PATH}/src/monitoring/monitor.py.backup_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading fixed monitor.py to VPS..."
scp "$LOCAL_FILE" ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/monitoring/monitor.py

if [ $? -eq 0 ]; then
    echo "✅ File uploaded successfully"
else
    echo "❌ Failed to upload file"
    exit 1
fi

echo "🔄 Restarting virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

echo "⏳ Waiting for service to start..."
sleep 5

echo "📊 Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service --no-pager | head -20"

echo ""
echo "📝 Recent logs (checking for AttributeError):"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' --no-pager | grep -E '(AttributeError|metrics_manager|start_operation|ERROR)' | tail -20"

echo ""
echo "✅ Deployment complete! Monitor the service with:"
echo "   ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"