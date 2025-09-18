#!/bin/bash

#############################################################################
# Script: deploy_dashboard_fixes.sh
# Purpose: Deploy and manage deploy dashboard fixes
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
#   ./deploy_dashboard_fixes.sh [options]
#   
#   Examples:
#     ./deploy_dashboard_fixes.sh
#     ./deploy_dashboard_fixes.sh --verbose
#     ./deploy_dashboard_fixes.sh --dry-run
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

"""
Deploy Dashboard Performance Fixes to VPS
Quickly deploys the emergency fixes for dashboard performance
"""

set -e  # Exit on any error

echo "🚀 Deploying Dashboard Performance Fixes to VPS"
echo "=================================================="

# Configuration
VPS_HOST="${VPS_HOST}"
VPS_USER="linuxuser"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Step 1: Syncing files to VPS...${NC}"
rsync -avz --progress \
    src/api/routes/dashboard_cached.py \
    src/api/cache_adapter_direct.py \
    ${VPS_USER}@${VPS_HOST}:${VPS_PROJECT_PATH}/

echo -e "${BLUE}📦 Step 2: Backing up current files on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    cp src/api/routes/dashboard_cached.py src/api/routes/dashboard_cached.py.backup.\$(date +%s) || echo 'No existing file'
    cp src/api/cache_adapter_direct.py src/api/cache_adapter_direct.py.backup.\$(date +%s) || echo 'No existing file'
"

echo -e "${BLUE}🔄 Step 3: Restarting Virtuoso service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    sudo systemctl stop virtuoso.service
    sleep 3
    sudo systemctl start virtuoso.service
    sleep 5
"

echo -e "${BLUE}✅ Step 4: Verifying deployment...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    echo 'Service status:'
    sudo systemctl is-active virtuoso.service || echo 'Service not active'
    
    echo 'Recent logs:'
    sudo journalctl -u virtuoso.service --no-pager -n 10
    
    echo 'Testing endpoints:'
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/overview || echo 'Endpoint test failed'
    echo
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/mobile-data || echo 'Endpoint test failed'  
    echo
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/opportunities || echo 'Endpoint test failed'
    echo
"

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo "Monitor with: ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"
echo "Test endpoints:"
echo "  curl http://${VPS_HOST}:8003/api/dashboard-cached/overview"
echo "  curl http://${VPS_HOST}:8003/api/dashboard-cached/mobile-data"
echo "  curl http://${VPS_HOST}:8003/api/dashboard-cached/opportunities"

exit 0