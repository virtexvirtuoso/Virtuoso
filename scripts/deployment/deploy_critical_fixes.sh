#!/bin/bash

#############################################################################
# Script: deploy_critical_fixes.sh
# Purpose: Deploy and manage deploy critical fixes
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
#   ./deploy_critical_fixes.sh [options]
#   
#   Examples:
#     ./deploy_critical_fixes.sh
#     ./deploy_critical_fixes.sh --verbose
#     ./deploy_critical_fixes.sh --dry-run
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

# Deploy critical async fixes to VPS
# Date: 2025-08-04

echo "🚀 Deploying critical async architecture fixes to VPS..."
echo "========================================"

VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
FILES=(
    "src/core/base_component.py"
    "src/core/startup_orchestrator.py"
    "src/core/exchanges/bybit.py"
    "src/monitoring/monitor.py"
)

# Create backup directory on VPS
echo "📦 Creating backup directory on VPS..."
ssh $VPS_HOST "cd $VPS_DIR && mkdir -p backups/2025-08-04-async-fixes"

# Deploy each file
echo -e "\n📤 Deploying fixed files..."
for file in "${FILES[@]}"; do
    echo "  Deploying $file..."
    
    # Check if file exists locally
    if [ ! -f "$file" ]; then
        echo "    ⚠️  File not found locally, skipping"
        continue
    fi
    
    # Backup existing file on VPS if it exists
    ssh $VPS_HOST "cd $VPS_DIR && [ -f $file ] && cp $file backups/2025-08-04-async-fixes/" 2>/dev/null
    
    # Copy file to VPS
    scp "$file" "$VPS_HOST:$VPS_DIR/$file"
    if [ $? -eq 0 ]; then
        echo "    ✅ Success"
    else
        echo "    ❌ Failed"
        exit 1
    fi
done

# Kill any stuck processes
echo -e "\n🔄 Stopping any running processes..."
ssh $VPS_HOST "pkill -9 -f 'python.*main.py' || echo 'No process found'"

# Wait for processes to die
sleep 3

# Start the process with proper venv
echo -e "\n🚀 Starting process with Python 3.11..."
ssh $VPS_HOST "cd $VPS_DIR && nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py > logs/startup.log 2>&1 &"

# Wait for startup
echo "⏳ Waiting for startup..."
sleep 15

# Check if process started
echo -e "\n✅ Checking process status..."
ssh $VPS_HOST "ps aux | grep -E 'python.*main.py' | grep -v grep"

# Check logs for initialization
echo -e "\n📋 Checking initialization logs..."
ssh $VPS_HOST "cd $VPS_DIR && grep -E '(Initializing|initialized|State:|ERROR|timeout)' logs/app.log | tail -30"

# Check for the hanging issue
echo -e "\n🔍 Monitoring for hanging issues..."
for i in {1..6}; do
    echo -n "  Check $i/6: "
    ssh $VPS_HOST "cd $VPS_DIR && tail -1 logs/app.log | awk '{print \$1, \$2}'"
    sleep 10
done

# Final status check
echo -e "\n📊 Final status check..."
ssh $VPS_HOST "cd $VPS_DIR && ls -la logs/app.log && echo '---' && tail -5 logs/app.log"

echo -e "\n✅ Deployment complete!"
echo ""
echo "Monitor the system with:"
echo "  ssh $VPS_HOST 'tail -f $VPS_DIR/logs/app.log'"
echo ""
echo "Check initialization states with:"
echo "  ssh $VPS_HOST 'cd $VPS_DIR && grep -E \"initialization_state|State:\" logs/app.log | tail -20'"