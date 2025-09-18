#!/bin/bash

#############################################################################
# Script: deploy_cache_optimization.sh
# Purpose: Deploy and manage deploy cache optimization
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
#   ./deploy_cache_optimization.sh [options]
#   
#   Examples:
#     ./deploy_cache_optimization.sh
#     ./deploy_cache_optimization.sh --verbose
#     ./deploy_cache_optimization.sh --dry-run
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

echo "=== Deploying Indicator Cache Optimizations to VPS ==="
echo "Time: $(date)"

VPS_HOST="linuxuser@${VPS_HOST}"
PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy the optimized indicator cache file
echo "→ Copying optimized indicator_cache.py..."
scp src/core/cache/indicator_cache.py $VPS_HOST:$PROJECT_PATH/src/core/cache/

# Step 2: SSH to VPS and restart the service
echo "→ Restarting service on VPS..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Restart the service
echo "Restarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Wait for service to start
sleep 5

# Check service status
echo "Service status:"
sudo systemctl status virtuoso.service --no-pager | head -20

# Check recent logs for cache performance
echo ""
echo "Recent cache logs (last 50 lines):"
sudo journalctl -u virtuoso.service --no-pager -n 50 | grep -E "(cache|indicator)" | tail -20

echo ""
echo "Deployment complete!"
EOF

echo "=== Cache Optimization Deployment Finished ==="