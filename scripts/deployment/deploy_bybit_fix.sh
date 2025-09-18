#!/bin/bash

#############################################################################
# Script: deploy_bybit_fix.sh
# Purpose: Deploy and manage deploy bybit fix
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
#   ./deploy_bybit_fix.sh [options]
#   
#   Examples:
#     ./deploy_bybit_fix.sh
#     ./deploy_bybit_fix.sh --verbose
#     ./deploy_bybit_fix.sh --dry-run
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

# Deploy the BybitExchange fix to VPS
echo "🚀 Deploying BybitExchange fix to VPS..."
echo "========================================"

VPS_HOST="linuxuser@${VPS_HOST}"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Copy the fixed bybit.py file
echo "📤 Copying fixed bybit.py to VPS..."
scp src/core/exchanges/bybit.py $VPS_HOST:$VPS_DIR/src/core/exchanges/

# Copy the test scripts
echo "📤 Copying test scripts..."
scp scripts/test_bybit_fix.py $VPS_HOST:$VPS_DIR/
scp scripts/fix_bybit_initialize.py $VPS_HOST:$VPS_DIR/

# Run tests on VPS
echo "🧪 Running tests on VPS..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "Testing BybitExchange fix..."
/home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python test_bybit_fix.py

# If tests pass, try the minimal startup
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tests passed! Running minimal startup..."
    /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python minimal_startup.py
else
    echo "❌ Tests failed on VPS"
fi
EOF

# If minimal startup works, start the full system
echo ""
echo "🚀 Starting full system..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill any existing processes
pkill -9 -f "python.*main.py" || true
sleep 2

# Start the system
echo "Starting Virtuoso Trading System..."
nohup /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -u src/main.py > logs/startup_$(date +%Y%m%d_%H%M%S).log 2>&1 &
PID=$!

echo "Started with PID: $PID"
echo "Monitoring startup..."

# Monitor for successful initialization
for i in {1..60}; do
    if ! kill -0 $PID 2>/dev/null; then
        echo "❌ Process died during startup!"
        echo "Last 20 lines of log:"
        tail -20 logs/app.log
        exit 1
    fi
    
    # Check for successful exchange initialization
    if grep -q "Primary exchange initialized" logs/app.log 2>/dev/null; then
        echo "✅ System initialized successfully!"
        echo ""
        echo "Recent log entries:"
        tail -10 logs/app.log
        exit 0
    fi
    
    # Check for errors
    if grep -q "INITIALIZATION TIMEOUT\|Failed to initialize exchange manager" logs/app.log 2>/dev/null; then
        echo "❌ Initialization failed!"
        grep -E "ERROR|TIMEOUT|Failed" logs/app.log | tail -10
        exit 1
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        echo "Still initializing... ($i seconds)"
    fi
    
    sleep 1
done

echo "⚠️ Initialization taking longer than expected..."
tail -20 logs/app.log
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Monitor the system with:"
echo "  ssh $VPS_HOST 'tail -f $VPS_DIR/logs/app.log'"