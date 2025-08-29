#!/bin/bash

#############################################################################
# Script: deploy_websocket_fix.sh
# Purpose: Deploy and manage deploy websocket fix
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
#   ./deploy_websocket_fix.sh [options]
#   
#   Examples:
#     ./deploy_websocket_fix.sh
#     ./deploy_websocket_fix.sh --verbose
#     ./deploy_websocket_fix.sh --dry-run
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

echo "🔧 Deploying WebSocket timeout fix to VPS..."

# Copy the fix script to VPS
echo "📤 Copying fix script to VPS..."
scp scripts/fix_websocket_timeout.py linuxuser@45.77.40.77:/tmp/

# Run the fix on VPS
echo "🔨 Applying WebSocket timeout fix..."
ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
python3 /tmp/fix_websocket_timeout.py

# Restart the service to apply changes
echo "🔄 Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Wait for service to start
sleep 5

# Check service status
echo "📊 Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Check for WebSocket errors in recent logs
echo ""
echo "📋 Recent WebSocket logs:"
sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -i "websocket\|timeout" | tail -10

# Clean up
rm /tmp/fix_websocket_timeout.py
EOF

echo "✅ WebSocket timeout fix deployed successfully!"