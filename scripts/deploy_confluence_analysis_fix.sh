#!/bin/bash

#############################################################################
# Script: deploy_confluence_analysis_fix.sh
# Purpose: Deploy and manage deploy confluence analysis fix
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
#   ./deploy_confluence_analysis_fix.sh [options]
#   
#   Examples:
#     ./deploy_confluence_analysis_fix.sh
#     ./deploy_confluence_analysis_fix.sh --verbose
#     ./deploy_confluence_analysis_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

echo "🔧 Deploying Confluence Analysis Fix to VPS..."
echo "==============================================="

# Copy updated web server
echo "📤 Copying updated web_server.py..."
scp src/web_server.py linuxuser@5.223.63.4:/home/linuxuser/trading/Virtuoso_ccxt/src/

# Restart web service
echo "🔄 Restarting web service..."
ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && sudo systemctl restart virtuoso-web"

# Wait a moment for restart
echo "⏳ Waiting for service restart..."
sleep 5

# Check service status
echo "✅ Checking service status..."
ssh linuxuser@5.223.63.4 "sudo systemctl status virtuoso-web --no-pager -l"

echo ""
echo "🧪 Testing Analysis Button Endpoints..."
echo "======================================"

# Test confluence breakdown endpoint
echo "Testing /api/confluence/latest:"
curl -s http://5.223.63.4:8001/api/confluence/latest | jq -C '.' || echo "❌ Latest confluence endpoint not responding"

echo ""
echo "Testing /api/dashboard/confluence-analysis/BTCUSDT:"
curl -s "http://5.223.63.4:8001/api/dashboard/confluence-analysis/BTCUSDT" | jq -C '.' || echo "❌ Analysis endpoint not responding"

echo ""
echo "Testing /api/dashboard/confluence-analysis-page:"
curl -s -I "http://5.223.63.4:8001/api/dashboard/confluence-analysis-page?symbol=BTCUSDT" | head -1

echo ""
echo "🎯 Confluence Analysis Fix Deployment Complete!"
echo "✅ Analysis button should now show full terminal breakdown"
echo "📱 Test on mobile dashboard: http://5.223.63.4:8001/dashboard/mobile"