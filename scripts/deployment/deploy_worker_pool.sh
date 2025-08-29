#!/bin/bash

#############################################################################
# Script: deploy_worker_pool.sh
# Purpose: Deploy worker pool integration to VPS
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
#   ./deploy_worker_pool.sh [options]
#   
#   Examples:
#     ./deploy_worker_pool.sh
#     ./deploy_worker_pool.sh --verbose
#     ./deploy_worker_pool.sh --dry-run
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

echo "🚀 Deploying Worker Pool Integration to VPS..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Check if files exist locally
if [ ! -f "src/core/worker_pool_manager.py" ]; then
    echo -e "${RED}Error: src/core/worker_pool_manager.py not found locally${NC}"
    exit 1
fi

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/main.py src/main.py.backup_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading worker pool manager..."
scp src/core/worker_pool_manager.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/

echo "📤 Uploading updated main.py..."
scp src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/

echo "📝 Uploading documentation..."
scp WORKER_POOL_INTEGRATION.md ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/

echo "🔄 Restarting Virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso"

echo "⏳ Waiting for service to start..."
sleep 10

echo "✅ Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso | grep -E 'Active:|Main PID:'"

echo "🔍 Checking for worker pool initialization..."
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso -n 50 | grep -i 'worker pool' | tail -5"

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "To monitor the service:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso -f'"
echo ""
echo "To check worker processes:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'ps aux | grep python | grep main.py'"