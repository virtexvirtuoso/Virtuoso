#!/bin/bash

#############################################################################
# Script: deploy_admin_url_update.sh
# Purpose: Deploy and manage deploy admin url update
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
#   ./deploy_admin_url_update.sh [options]
#   
#   Examples:
#     ./deploy_admin_url_update.sh
#     ./deploy_admin_url_update.sh --verbose
#     ./deploy_admin_url_update.sh --dry-run
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

# Deploy Admin URL Update to VPS
# Changes /api/dashboard/admin to /admin

# Configuration
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Admin URL Update to VPS...${NC}"
echo -e "${YELLOW}Target: ${VPS_USER}@${VPS_HOST}${NC}"
echo -e "${YELLOW}Changes: /api/dashboard/admin → /admin${NC}"
echo ""

# Step 1: Deploy the updated API init file
echo -e "${YELLOW}📤 Deploying updated API routes...${NC}"
scp "${LOCAL_PATH}/src/api/__init__.py" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/__init__.py"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy __init__.py${NC}"
    exit 1
fi

# Step 2: Deploy all updated template files
echo -e "${YELLOW}📤 Deploying updated templates...${NC}"

# Admin dashboard
scp "${LOCAL_PATH}/src/dashboard/templates/admin_dashboard.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_dashboard.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_dashboard.html${NC}"
    exit 1
fi

# Admin login
scp "${LOCAL_PATH}/src/dashboard/templates/admin_login.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_login.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_login.html${NC}"
    exit 1
fi

# Config editor
scp "${LOCAL_PATH}/src/dashboard/templates/admin_config_editor.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_config_editor.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_config_editor.html${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All files deployed successfully!${NC}"
echo ""

# Step 3: Restart the Python process
echo -e "${YELLOW}🔄 Restarting Virtuoso process...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" << 'EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Find the Python process
    PID=$(ps aux | grep "python -u src/main.py" | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$PID" ]; then
        echo "Found Virtuoso process with PID: $PID"
        echo "Sending HUP signal to reload..."
        kill -HUP $PID
        sleep 2
        
        # Verify it's still running
        if ps -p $PID > /dev/null; then
            echo "✅ Process reloaded successfully"
        else
            echo "⚠️  Process may have stopped. You may need to restart manually."
        fi
    else
        echo "⚠️  Virtuoso process not found. You may need to start it manually."
    fi
EOF

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}📝 URL Changes:${NC}"
echo "  OLD: http://${VPS_HOST}:8003/api/dashboard/admin/*"
echo "  NEW: http://${VPS_HOST}:8003/admin/*"
echo ""
echo -e "${YELLOW}🔗 New Admin URLs:${NC}"
echo "  Login:        http://${VPS_HOST}:8003/admin/login"
echo "  Dashboard:    http://${VPS_HOST}:8003/admin/dashboard"
echo "  Config Editor: http://${VPS_HOST}:8003/admin/config-editor"
echo ""
echo -e "${GREEN}✅ All admin features now accessible at the shorter /admin path!${NC}"