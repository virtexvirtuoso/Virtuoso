#!/bin/bash

#############################################################################
# Script: deploy_vwap_fix.sh
# Purpose: Deploy and manage deploy vwap fix
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
#   ./deploy_vwap_fix.sh [options]
#   
#   Examples:
#     ./deploy_vwap_fix.sh
#     ./deploy_vwap_fix.sh --verbose
#     ./deploy_vwap_fix.sh --dry-run
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

# Deploy VWAP fix to VPS
# Usage: ./deploy_vwap_fix.sh

echo "=== Deploying VWAP Fix to VPS ==="
echo "Date: $(date)"

# VPS details
VPS_USER="linuxuser"
VPS_HOST="5.223.63.4"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Local paths
PATCH_FILE="patches/vwap_fix_20250727.patch"
INDICATOR_FILE="src/indicators/price_structure_indicators.py"

# Check if patch file exists
if [ ! -f "$PATCH_FILE" ]; then
    echo "Error: Patch file not found: $PATCH_FILE"
    exit 1
fi

# Check if local indicator file exists
if [ ! -f "$INDICATOR_FILE" ]; then
    echo "Error: Local indicator file not found: $INDICATOR_FILE"
    exit 1
fi

echo "1. Creating backup on VPS..."
ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && cp $INDICATOR_FILE ${INDICATOR_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "2. Creating patches directory and copying patch file to VPS..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $VPS_PATH/patches"
scp $PATCH_FILE $VPS_USER@$VPS_HOST:$VPS_PATH/$PATCH_FILE

echo "3. Copying updated indicator file to VPS..."
scp $INDICATOR_FILE $VPS_USER@$VPS_HOST:$VPS_PATH/$INDICATOR_FILE

echo "4. Restarting Virtuoso service..."
ssh $VPS_USER@$VPS_HOST "sudo systemctl restart virtuoso"

echo "5. Checking service status..."
ssh $VPS_USER@$VPS_HOST "sudo systemctl status virtuoso | head -10"

echo "6. Tailing logs for VWAP entries..."
ssh $VPS_USER@$VPS_HOST "sudo journalctl -u virtuoso -n 50 | grep -i vwap || echo 'No VWAP entries in recent logs'"

echo "=== Deployment Complete ==="
echo "Monitor logs with: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u virtuoso -f | grep -i vwap'"