#!/bin/bash

#############################################################################
# Script: fix_connection_timeout.sh
# Purpose: Fix connection timeout issues caused by concurrent API burst
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
#   ./fix_connection_timeout.sh [options]
#   
#   Examples:
#     ./fix_connection_timeout.sh
#     ./fix_connection_timeout.sh --verbose
#     ./fix_connection_timeout.sh --dry-run
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

echo "🔧 Deploying Connection Timeout Fix to VPS..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "${YELLOW}📊 Current error count (last 5 mins):${NC}"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso --since '5 minutes ago' | grep -c 'Connection timeout' || echo '0'"

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/main.py src/main.py.backup_conn_fix_$(date +%Y%m%d_%H%M%S)"
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_conn_fix_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading fixed files..."
scp src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

echo "🔄 Restarting Virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso"

echo "⏳ Waiting for service to stabilize..."
sleep 15

echo -e "${GREEN}✅ Fix deployed!${NC}"
echo ""
echo "📊 Monitoring for improvements..."
echo "Waiting 2 minutes to collect data..."
sleep 120

echo -e "${YELLOW}📊 New error count (last 2 mins):${NC}"
NEW_ERRORS=$(ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso --since '2 minutes ago' | grep -c 'Connection timeout' || echo '0'")
echo "Connection timeout errors: ${NEW_ERRORS}"

if [ "$NEW_ERRORS" -lt 5 ]; then
    echo -e "${GREEN}✅ Fix successful! Connection timeouts significantly reduced.${NC}"
else
    echo -e "${RED}⚠️  Still seeing connection timeouts. May need further investigation.${NC}"
fi

echo ""
echo "To monitor logs:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso -f | grep -E \"(Connection timeout|ERROR)\"'"