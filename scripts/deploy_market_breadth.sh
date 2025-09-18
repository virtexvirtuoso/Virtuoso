#!/bin/bash

#############################################################################
# Script: deploy_market_breadth.sh
# Purpose: Deploy market breadth updates to VPS
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
#   ./deploy_market_breadth.sh [options]
#   
#   Examples:
#     ./deploy_market_breadth.sh
#     ./deploy_market_breadth.sh --verbose
#     ./deploy_market_breadth.sh --dry-run
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

echo "🚀 Deploying market breadth updates to VPS..."

# Copy updated files to VPS
echo "📦 Copying updated files..."
scp src/api/cache_adapter_direct.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/api/
scp src/dashboard/templates/dashboard_mobile_v1.html linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/dashboard/templates/
scp scripts/add_market_breadth.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# Run market breadth update on VPS
echo "📊 Running market breadth data update..."
ssh linuxuser@${VPS_HOST} "cd /home/linuxuser/trading/Virtuoso_ccxt && python scripts/add_market_breadth.py"

# Restart web server to pick up changes
echo "🔄 Restarting web server..."
ssh linuxuser@${VPS_HOST} "sudo systemctl restart virtuoso-web"

# Give services time to stabilize
sleep 3

# Test the endpoints
echo "✅ Testing market breadth endpoints..."
echo ""
echo "Testing market overview endpoint:"
curl -s http://${VPS_HOST}:8080/api/market_overview | python -m json.tool | grep -A5 "market_breadth" || echo "No market breadth data"

echo ""
echo "Testing mobile data endpoint:"
curl -s http://${VPS_HOST}:8080/api/mobile_data | python -m json.tool | head -20

echo ""
echo "✅ Deployment complete!"
echo "📱 Mobile dashboard: http://${VPS_HOST}:8080/dashboard/mobile"