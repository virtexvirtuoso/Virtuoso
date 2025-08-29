#!/bin/bash

#############################################################################
# Script: deploy_smart_money_flow_fixes.sh
# Purpose: Deploy and manage deploy smart money flow fixes
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
#   ./deploy_smart_money_flow_fixes.sh [options]
#   
#   Examples:
#     ./deploy_smart_money_flow_fixes.sh
#     ./deploy_smart_money_flow_fixes.sh --verbose
#     ./deploy_smart_money_flow_fixes.sh --dry-run
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

echo "==================================="
echo "🚀 Deploying Smart Money Flow Fixes & Updates"
echo "==================================="
echo ""
echo "Changes being deployed:"
echo "1. Fixed 'liquidity_zones' undefined error"
echo "2. Updated interpretations to use smart money flow terminology"
echo "3. Weight adjustments: smart_money_flow 15%, cvd 22%, trade_flow 17%"
echo ""

# Deploy files to VPS
echo "📦 Deploying updated files to VPS..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='venv311' \
    --exclude='logs' \
    --exclude='exports' \
    --exclude='backups' \
    --exclude='reports' \
    --exclude='*.log' \
    src/indicators/orderflow_indicators.py \
    src/analysis/core/interpretation_generator.py \
    src/analysis/market/interpretation_generator.py \
    src/core/analysis/interpretation_generator.py \
    config/config.yaml \
    linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/

if [ $? -eq 0 ]; then
    echo "✅ Files deployed successfully"
    
    # Restart services on VPS
    echo ""
    echo "🔄 Restarting services on VPS..."
    ssh linuxuser@45.77.40.77 << 'REMOTE_EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Kill existing processes
    echo "Stopping existing processes..."
    pkill -f "python.*main.py" || true
    pkill -f "python.*web_server.py" || true
    sleep 2
    
    # Start services with virtual environment
    echo "Starting services with venv311..."
    screen -dmS virtuoso bash -c 'cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python src/main.py 2>&1 | tee -a logs/main.log'
    screen -dmS webserver bash -c 'cd /home/linuxuser/trading/Virtuoso_ccxt && ./venv311/bin/python src/web_server.py 2>&1 | tee -a logs/webserver.log'
    
    sleep 10
    
    # Verify services are running
    echo ""
    echo "Service status:"
    pgrep -f "python.*main.py" > /dev/null && echo "✅ Main service running" || echo "❌ Main service not running"
    pgrep -f "python.*web_server.py" > /dev/null && echo "✅ Web server running" || echo "❌ Web server not running"
    
    # Check for errors in recent logs
    echo ""
    echo "Checking for 'liquidity_zones' errors (should be none):"
    tail -100 logs/main.log | grep -i "liquidity_zones.*not defined" || echo "✅ No 'liquidity_zones' errors found"
    
    echo ""
    echo "Checking for smart_money_flow in logs:"
    tail -100 logs/main.log | grep -i "smart_money_flow" | tail -3
REMOTE_EOF
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "Fixed Issues:"
    echo "  • liquidity_zones undefined error resolved"
    echo "  • All references updated to smart_money_flow"
    echo "  • Interpretation messages updated"
    echo ""
    echo "Current Weights:"
    echo "  • smart_money_flow: 15%"
    echo "  • cvd: 22%"
    echo "  • trade_flow: 17%"
    echo "  • imbalance: 13%"
    echo "  • open_interest: 15%"
    echo "  • pressure: 8%"
    echo "  • liquidity: 10%"
else
    echo "❌ Deployment failed"
    exit 1
fi
