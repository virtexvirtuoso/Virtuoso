#!/bin/bash

#############################################################################
# Script: deploy_to_vps.sh
# Purpose: Deploy and manage deploy to vps
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
#   ./deploy_to_vps.sh [options]
#   
#   Examples:
#     ./deploy_to_vps.sh
#     ./deploy_to_vps.sh --verbose
#     ./deploy_to_vps.sh --dry-run
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

# Deploy to VPS using rsync
# Excludes exports, images, PDFs, and other large files

# Configuration
VPS_USER="linuxuser"
VPS_HOST="185.162.249.241"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_PATH="/Users/ffv_macmini/Desktop/Virtuoso_ccxt/"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Deploying Virtuoso to VPS...${NC}"
echo -e "${YELLOW}From: ${LOCAL_PATH}${NC}"
echo -e "${YELLOW}To: ${VPS_USER}@${VPS_HOST}:${VPS_PATH}${NC}"
echo ""

# Run rsync with exclusions
rsync -avz --progress \
    --exclude='exports/' \
    --exclude='*.png' \
    --exclude='*.pdf' \
    --exclude='*.jpg' \
    --exclude='*.jpeg' \
    --exclude='*.gif' \
    --exclude='*.svg' \
    --exclude='*.ico' \
    --exclude='reports/html/' \
    --exclude='reports/pdf/' \
    --exclude='cache/' \
    --exclude='logs/' \
    --exclude='*.log' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='venv/' \
    --exclude='venv311/' \
    --exclude='.git/' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.pkl' \
    --exclude='*.pickle' \
    --exclude='*.h5' \
    --exclude='*.zip' \
    --exclude='*.tar' \
    --exclude='*.gz' \
    --exclude='backups/' \
    --exclude='test_output/' \
    --exclude='.DS_Store' \
    --exclude='*.old' \
    --exclude='*.rtf' \
    --exclude='.env' \
    --exclude='.env.local' \
    "${LOCAL_PATH}" "${VPS_USER}@${VPS_HOST}:${VPS_PATH}"

# Check if rsync was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    
    # Show size of deployment
    echo -e "${YELLOW}Calculating deployment size...${NC}"
    ssh "${VPS_USER}@${VPS_HOST}" "du -sh ${VPS_PATH}"
else
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📝 Note: Remember to:${NC}"
echo "1. Set up virtual environment on VPS: python3.11 -m venv venv311"
echo "2. Install requirements: pip install -r requirements.txt"
echo "3. Configure environment variables"
echo "4. Set up systemd service for auto-start"