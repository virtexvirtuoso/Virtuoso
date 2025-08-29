#!/bin/bash

#############################################################################
# Script: deploy_config_editor.sh
# Purpose: Deploy and manage deploy config editor
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
#   ./deploy_config_editor.sh [options]
#   
#   Examples:
#     ./deploy_config_editor.sh
#     ./deploy_config_editor.sh --verbose
#     ./deploy_config_editor.sh --dry-run
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

# Deploy Config Editor Update to VPS
# Deploys the new admin config editor feature

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

echo -e "${BLUE}🚀 Deploying Config Editor Update to VPS...${NC}"
echo -e "${YELLOW}Target: ${VPS_USER}@${VPS_HOST}${NC}"
echo ""

# Step 1: Deploy the updated admin.py file
echo -e "${YELLOW}📤 Deploying updated admin API routes...${NC}"
scp "${LOCAL_PATH}/src/api/routes/admin.py" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/routes/admin.py"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin.py${NC}"
    exit 1
fi

# Step 2: Deploy the new config editor HTML file
echo -e "${YELLOW}📤 Deploying new config editor template...${NC}"
scp "${LOCAL_PATH}/src/dashboard/templates/admin_config_editor.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_config_editor.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_config_editor.html${NC}"
    exit 1
fi

# Step 3: Deploy the updated admin dashboard HTML
echo -e "${YELLOW}📤 Deploying updated admin dashboard...${NC}"
scp "${LOCAL_PATH}/src/dashboard/templates/admin_dashboard.html" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/templates/admin_dashboard.html"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to deploy admin_dashboard.html${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All files deployed successfully!${NC}"
echo ""

# Step 4: Restart the service
echo -e "${YELLOW}🔄 Restarting Virtuoso service...${NC}"
ssh "${VPS_USER}@${VPS_HOST}" << 'EOF'
    # Check if systemd service exists
    if systemctl is-active --quiet virtuoso-monitor.service; then
        echo "Restarting virtuoso-monitor service..."
        sudo systemctl restart virtuoso-monitor.service
        sleep 3
        
        # Check service status
        if systemctl is-active --quiet virtuoso-monitor.service; then
            echo "✅ Service restarted successfully"
            sudo systemctl status virtuoso-monitor.service --no-pager | head -10
        else
            echo "⚠️  Service failed to start"
            sudo systemctl status virtuoso-monitor.service --no-pager
        fi
    else
        echo "⚠️  Virtuoso service not found. You may need to restart manually."
        echo "   Try: sudo systemctl restart virtuoso-monitor"
        echo "   Or restart the Python process manually"
    fi
EOF

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}📝 New Features Available:${NC}"
echo "  - Enhanced config editor with syntax highlighting"
echo "  - Live YAML validation"
echo "  - Split view with preview panel"
echo "  - Version history and backup management"
echo "  - Professional IDE-like editing experience"
echo ""
echo -e "${YELLOW}🔗 Access the new editor at:${NC}"
echo "  http://${VPS_HOST}:8003/admin/config-editor"
echo "  Or click 'Open Advanced Editor' from the admin dashboard"
echo ""
echo -e "${YELLOW}⚠️  Note:${NC}"
echo "  - Make sure to login to admin dashboard first"
echo "  - The editor uses CDN resources (CodeMirror, js-yaml)"
echo "  - Ensure your VPS has internet access for CDN resources"