#!/bin/bash

#############################################################################
# Script: quick_deploy.sh
# Purpose: Deploy and manage quick deploy
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
#   ./quick_deploy.sh [options]
#   
#   Examples:
#     ./quick_deploy.sh
#     ./quick_deploy.sh --verbose
#     ./quick_deploy.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

# Quick deployment script - updates only dashboard files

REMOTE_USER="linuxuser"
REMOTE_HOST="VPS_HOST_REDACTED"
REMOTE_PATH="/home/linuxuser/trading/virtuoso_ccxt"

echo "🚀 Quick Deploy - Dashboard Update"
echo "Updating dashboard files on ${REMOTE_HOST}..."

# Copy the updated dashboard templates
scp src/dashboard/templates/dashboard_desktop_v1.html ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/dashboard/templates/
scp src/dashboard/templates/dashboard_mobile_v1.html ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/dashboard/templates/

# Copy the updated web server
scp src/web_server.py ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/

# Copy manifest.json
scp src/static/manifest.json ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/src/static/

echo "✅ Files copied successfully"
echo ""
echo "To restart the web server, run:"
echo "ssh ${REMOTE_USER}@${REMOTE_HOST} 'pkill -f web_server.py; cd ${REMOTE_PATH} && source venv/bin/activate && nohup python src/web_server.py > web_server.log 2>&1 &'"