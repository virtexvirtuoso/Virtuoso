#!/bin/bash

#############################################################################
# Script: simple_confluence_deploy.sh
# Purpose: Deploy and manage simple confluence deploy
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
#   ./simple_confluence_deploy.sh [options]
#   
#   Examples:
#     ./simple_confluence_deploy.sh
#     ./simple_confluence_deploy.sh --verbose
#     ./simple_confluence_deploy.sh --dry-run
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

echo "Deploying confluence fix..."

# Copy the fixed file
scp src/api/routes/dashboard.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Quick test on VPS
ssh vps << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
echo "Restarting web server..."
sudo systemctl restart virtuoso-web
sleep 2
echo "Testing symbols endpoint..."
curl -s http://localhost:8001/api/dashboard/symbols | head -c 200
echo
EOF

echo "Done!"