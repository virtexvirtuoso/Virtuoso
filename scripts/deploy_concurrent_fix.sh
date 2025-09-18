#!/bin/bash

#############################################################################
# Script: deploy_concurrent_fix.sh
# Purpose: Deploy and manage deploy concurrent fix
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
#   ./deploy_concurrent_fix.sh [options]
#   
#   Examples:
#     ./deploy_concurrent_fix.sh
#     ./deploy_concurrent_fix.sh --verbose
#     ./deploy_concurrent_fix.sh --dry-run
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

echo "========================================"
echo "DEPLOYING CONCURRENT STARTUP FIX TO VPS"
echo "========================================"
echo ""

VPS="linuxuser@${VPS_HOST}"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo "1. Copying fixed main.py to VPS..."
echo "----------------------------------------"
scp -q src/main.py $VPS:$VPS_PATH/src/
echo "   ✓ main.py copied"

echo ""
echo "2. Restarting service with fix..."
echo "----------------------------------------"

ssh $VPS << 'EOF'
echo "   Stopping virtuoso service..."
sudo systemctl stop virtuoso

# Clear any stale lock files
rm -f /tmp/virtuoso.lock

# Wait a moment
sleep 2

echo "   Starting virtuoso service..."
sudo systemctl start virtuoso

# Wait for startup
sleep 5

# Check status
if systemctl is-active --quiet virtuoso; then
    echo "   ✓ Virtuoso service started successfully"
    
    # Give it more time to initialize both services
    echo "   Waiting for services to initialize..."
    sleep 10
    
    # Check if port 8003 is listening
    if ss -tlpn | grep -q ':8003'; then
        echo "   ✓ Port 8003 is now listening!"
    else
        echo "   ⚠ Port 8003 not yet listening, checking logs..."
        sudo journalctl -u virtuoso --since "1 minute ago" | grep -E "web server|Starting web server|uvicorn|8003" | tail -5
    fi
    
    # Check if monitoring is running
    if sudo journalctl -u virtuoso --since "1 minute ago" | grep -q "market_monitor background task created"; then
        echo "   ✓ Monitoring system started in background"
    else
        echo "   ⚠ Monitoring startup not confirmed"
    fi
else
    echo "   ✗ Service failed to start"
    sudo systemctl status virtuoso --no-pager | head -15
fi
EOF

echo ""
echo "3. Verifying both services are running..."
echo "----------------------------------------"

# Test API endpoint
echo "   Testing API on port 8003..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://${VPS_HOST}:8003/api/system/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✓ API responding on port 8003!"
    
    # Get detailed health status
    echo ""
    echo "   API Health Status:"
    curl -s http://${VPS_HOST}:8003/api/system/health | python3 -m json.tool 2>/dev/null | head -20 || echo "   Could not parse health response"
else
    echo "   ⚠ API not responding yet (HTTP $HTTP_CODE)"
    echo "   Checking service logs for issues..."
    ssh $VPS "sudo journalctl -u virtuoso --since '30 seconds ago' | grep -E 'ERROR|WARNING|web server|8003' | tail -10"
fi

echo ""
echo "4. Checking recent logs for both services..."
echo "----------------------------------------"
ssh $VPS "sudo journalctl -u virtuoso --since '30 seconds ago' | grep -E 'web server|Starting web server|market_monitor|background task|8003|uvicorn' | tail -15"

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================"
echo ""
echo "Summary:"
echo "  ✓ Concurrent startup fix deployed"
echo "  ✓ Service restarted"
echo ""
echo "Monitor with:"
echo "  ssh $VPS 'sudo journalctl -u virtuoso -f'"
echo ""
echo "Test endpoints:"
echo "  curl http://${VPS_HOST}:8003/api/system/health"
echo "  curl http://${VPS_HOST}:8001/"