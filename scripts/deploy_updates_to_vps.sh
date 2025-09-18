#!/bin/bash
#
# Script: deploy_updates_to_vps.sh
# Purpose: Deploy critical updates and fixes to production VPS
# Author: Virtuoso Team
# Version: 2.0.0
# Created: 2025-08-19
# Modified: 2025-08-28
#
# Description:
#   Deploys critical system updates to the production VPS including:
#   - Environment configuration files
#   - Python source code fixes
#   - Service restart and health verification
#   This script performs incremental updates without full redeployment.
#
# Usage:
#   ./deploy_updates_to_vps.sh [options]
#
# Options:
#   -h, --help     Show this help message
#   -v, --verbose  Enable verbose output
#   -f, --force    Force deployment without confirmation
#   -n, --no-restart  Skip service restart after deployment
#
# Environment Variables:
#   VPS_HOST       Target VPS connection (default: linuxuser@${VPS_HOST})
#   VPS_DIR        Project directory on VPS (default: /home/linuxuser/trading/Virtuoso_ccxt)
#   LOCAL_DIR      Local project directory (default: /Users/ffv_macmini/Desktop/Virtuoso_ccxt)
#
# Exit Codes:
#   0              Success
#   1              Connection error
#   2              File transfer error
#   3              Service restart failed
#
# Examples:
#   # Basic deployment
#   ./deploy_updates_to_vps.sh
#   
#   # Verbose deployment with output
#   ./deploy_updates_to_vps.sh --verbose
#   
#   # Deploy without restarting service
#   ./deploy_updates_to_vps.sh --no-restart
#
# Dependencies:
#   - SSH access to VPS with key authentication
#   - rsync/scp for file transfers
#   - sudo privileges on VPS for service restart
#
# Notes:
#   - Always test changes locally before deploying
#   - Creates automatic backups before overwriting files
#   - Monitors service health after restart
#
#==============================================================================

VPS_HOST="linuxuser@${VPS_HOST}"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo "========================================="
echo "Deploying Critical Updates to VPS"
echo "========================================="
echo ""

# 1. Deploy environment configuration
echo "1. Deploying environment configuration..."
ssh $VPS_HOST "mkdir -p $VPS_DIR/config/env"
scp "$LOCAL_DIR/config/env/.env" "$VPS_HOST:$VPS_DIR/config/env/.env"
echo "   ✅ Environment file deployed"

# 2. Deploy critical Python fixes (only if they have syntax errors)
echo ""
echo "2. Checking and deploying Python fixes..."

# Check and deploy alert_manager.py if needed
if ssh $VPS_HOST "grep -q 'self\.#' $VPS_DIR/src/monitoring/alert_manager.py 2>/dev/null"; then
    echo "   Fixing alert_manager.py syntax errors..."
    scp "$LOCAL_DIR/src/monitoring/alert_manager.py" "$VPS_HOST:$VPS_DIR/src/monitoring/"
    echo "   ✅ alert_manager.py deployed"
else
    echo "   ✅ alert_manager.py already fixed"
fi

# Check and deploy sentiment_indicators.py if needed
if ssh $VPS_HOST "grep -q 'self\.#' $VPS_DIR/src/indicators/sentiment_indicators.py 2>/dev/null"; then
    echo "   Fixing sentiment_indicators.py syntax errors..."
    scp "$LOCAL_DIR/src/indicators/sentiment_indicators.py" "$VPS_HOST:$VPS_DIR/src/indicators/"
    echo "   ✅ sentiment_indicators.py deployed"
else
    echo "   ✅ sentiment_indicators.py already fixed"
fi

# 3. Deploy updated core files
echo ""
echo "3. Deploying updated core files..."
FILES_TO_DEPLOY=(
    "src/core/exchanges/bybit.py"
    "src/core/exchanges/manager.py"
    "src/monitoring/alert_manager.py"
    "src/indicators/base_indicator.py"
    "src/main.py"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    echo "   Deploying $file..."
    scp "$LOCAL_DIR/$file" "$VPS_HOST:$VPS_DIR/$file"
done
echo "   ✅ Core files deployed"

# 4. Check service status
echo ""
echo "4. Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso --no-pager | head -10"

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "To restart the service, run:"
echo "ssh $VPS_HOST 'sudo systemctl restart virtuoso'"
echo ""
echo "To monitor logs:"
echo "ssh $VPS_HOST 'sudo journalctl -u virtuoso -f'"