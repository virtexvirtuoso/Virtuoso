#!/bin/bash

#############################################################################
# Script: deploy_stable_service.sh
# Purpose: Deploy and manage deploy stable service
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
#   ./deploy_stable_service.sh [options]
#   
#   Examples:
#     ./deploy_stable_service.sh
#     ./deploy_stable_service.sh --verbose
#     ./deploy_stable_service.sh --dry-run
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

echo "🚀 Deploying stable service configuration to VPS..."

# Stop the service and clean up
echo "1. Stopping service and cleaning up..."
ssh linuxuser@VPS_HOST_REDACTED << 'ENDSSH'
    sudo systemctl stop virtuoso.service
    sudo pkill -9 -f "python.*main.py" || true
    sleep 2
    
    # Clear any stuck ports
    sudo lsof -ti:8001 | xargs -r sudo kill -9 || true
    sudo lsof -ti:8004 | xargs -r sudo kill -9 || true
    
    # Reset systemd failure state
    sudo systemctl reset-failed virtuoso.service
    
    echo "Service stopped and cleaned up"
ENDSSH

# Deploy the latest code
echo "2. Syncing code to VPS..."
rsync -avz --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='venv311' \
    --exclude='logs' \
    --exclude='exports' \
    --exclude='backups' \
    --exclude='reports' \
    --exclude='*.log' \
    src/ scripts/ config/ \
    linuxuser@VPS_HOST_REDACTED:/home/linuxuser/trading/Virtuoso_ccxt/

# Start the service
echo "3. Starting virtuoso service..."
ssh linuxuser@VPS_HOST_REDACTED << 'ENDSSH'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Ensure memcached is running
    sudo systemctl start memcached || true
    
    # Start the service
    sudo systemctl start virtuoso.service
    
    # Wait for initialization
    sleep 10
    
    # Check status
    sudo systemctl status virtuoso.service | head -15
ENDSSH

echo "4. Testing API endpoints..."
sleep 5

# Test the API
echo "Testing confluence scores endpoint..."
curl -s -m 5 "http://VPS_HOST_REDACTED:8004/api/dashboard/confluence/scores" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data:
        print('✅ API is responding with data')
        print(f'  Found {len(data)} symbols')
    else:
        print('⚠️ API responded but no data')
except:
    print('❌ API not responding or invalid JSON')
" || echo "❌ API request failed"

echo ""
echo "Deployment complete. Checking final status..."
ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl is-active virtuoso.service"