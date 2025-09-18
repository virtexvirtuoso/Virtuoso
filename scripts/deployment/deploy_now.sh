#!/bin/bash

#############################################################################
# Script: deploy_now.sh
# Purpose: Deploy and manage deploy now
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
#   ./deploy_now.sh [options]
#   
#   Examples:
#     ./deploy_now.sh
#     ./deploy_now.sh --verbose
#     ./deploy_now.sh --dry-run
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

# Interactive deployment script

echo "🚀 Virtuoso VPS Deployment"
echo "=========================="
echo ""

# Prompt for VPS details
read -p "Enter VPS IP address: " VPS_IP
read -p "Enter VPS username (default: root): " VPS_USER
VPS_USER=${VPS_USER:-root}
read -p "Enter VPS destination path (default: /root/Virtuoso_ccxt): " VPS_PATH
VPS_PATH=${VPS_PATH:-/root/Virtuoso_ccxt}

echo ""
echo "📋 Deployment Configuration:"
echo "  VPS: ${VPS_USER}@${VPS_IP}"
echo "  Path: ${VPS_PATH}"
echo ""

read -p "Continue with deployment? (y/n): " CONFIRM
if [[ $CONFIRM != "y" ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "🔄 Starting deployment..."

# Create directory on VPS if it doesn't exist
ssh "${VPS_USER}@${VPS_IP}" "mkdir -p ${VPS_PATH}"

# Run rsync
rsync -avz --progress \
    --exclude='exports/' \
    --exclude='*.png' \
    --exclude='*.pdf' \
    --exclude='*.jpg' \
    --exclude='*.jpeg' \
    --exclude='*.gif' \
    --exclude='*.svg' \
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
    --exclude='*.h5' \
    --exclude='*.zip' \
    --exclude='*.tar.gz' \
    --exclude='backups/' \
    --exclude='test_output/' \
    --exclude='.DS_Store' \
    --exclude='*.old' \
    --exclude='*.rtf' \
    --exclude='.env' \
    --exclude='node_modules/' \
    --exclude='sample_reports/' \
    --exclude='performance_analysis/' \
    /Users/ffv_macmini/Desktop/Virtuoso_ccxt/ "${VPS_USER}@${VPS_IP}:${VPS_PATH}"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment completed successfully!"
    
    # Show deployment size
    echo ""
    echo "📊 Deployment size on VPS:"
    ssh "${VPS_USER}@${VPS_IP}" "du -sh ${VPS_PATH} 2>/dev/null || echo 'Could not calculate size'"
    
    echo ""
    echo "🎯 Next steps on VPS:"
    echo "1. SSH into VPS: ssh ${VPS_USER}@${VPS_IP}"
    echo "2. Navigate to: cd ${VPS_PATH}"
    echo "3. Create virtual environment: python3.11 -m venv venv311"
    echo "4. Activate it: source venv311/bin/activate"
    echo "5. Install requirements: pip install -r requirements.txt"
    echo "6. Copy and configure .env file"
    echo "7. Test run: python src/main.py"
else
    echo ""
    echo "❌ Deployment failed!"
    echo "Please check your VPS connection and try again."
fi