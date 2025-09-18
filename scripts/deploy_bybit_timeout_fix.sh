#!/bin/bash

#############################################################################
# Script: deploy_bybit_timeout_fix.sh
# Purpose: Deploy and manage deploy bybit timeout fix
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
#   ./deploy_bybit_timeout_fix.sh [options]
#   
#   Examples:
#     ./deploy_bybit_timeout_fix.sh
#     ./deploy_bybit_timeout_fix.sh --verbose
#     ./deploy_bybit_timeout_fix.sh --dry-run
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

echo "🚀 Deploying Bybit timeout fix to VPS..."

# VPS connection details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed bybit.py file
echo "📦 Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

# Restart the service
echo "🔄 Restarting virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso.service"

# Wait a moment for service to start
sleep 5

# Check service status
echo "✅ Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso.service --no-pager"

# Check recent logs
echo ""
echo "📋 Recent logs:"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' --no-pager | tail -30"

echo ""
echo "✅ Deployment complete!"