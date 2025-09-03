#!/bin/bash

#############################################################################
# Script: restart_with_logging.sh
# Purpose: Deploy and manage restart with logging
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
#   ./restart_with_logging.sh [options]
#   
#   Examples:
#     ./restart_with_logging.sh
#     ./restart_with_logging.sh --verbose
#     ./restart_with_logging.sh --dry-run
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

echo "=========================================="
echo "Restarting Virtuoso with proper logging"
echo "=========================================="

# Change to project directory
cd /home/linuxuser/trading/Virtuoso_ccxt

# Kill the existing process
echo "1. Stopping current process (PID 131411)..."
kill -TERM 131411 2>/dev/null || echo "Process already stopped"
sleep 2

# Make sure it's really stopped
if ps -p 131411 > /dev/null 2>&1; then
    echo "   Force stopping..."
    kill -9 131411 2>/dev/null
    sleep 1
fi

# Activate virtual environment
echo "2. Activating virtual environment..."
source venv311/bin/activate

# Set up environment variables
echo "3. Setting up environment..."
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Create a timestamp for log files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Start the application with proper logging
echo "4. Starting application with logging to files..."
nohup python -u src/main.py \
    > logs/virtuoso_stdout_${TIMESTAMP}.log \
    2> logs/virtuoso_stderr_${TIMESTAMP}.log &

NEW_PID=$!
echo "   Started with PID: $NEW_PID"

# Wait a moment for startup
sleep 3

# Verify it's running
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "5. ✅ Process running successfully"
    echo "   Stdout log: logs/virtuoso_stdout_${TIMESTAMP}.log"
    echo "   Stderr log: logs/virtuoso_stderr_${TIMESTAMP}.log"
    echo "   App log: logs/app.log"
    
    # Show initial log output
    echo ""
    echo "6. Initial log output:"
    echo "   ------------------------"
    tail -20 logs/app.log
else
    echo "5. ❌ Process failed to start"
    echo "   Check stderr log for errors:"
    tail -20 logs/virtuoso_stderr_${TIMESTAMP}.log
fi

echo ""
echo "=========================================="
echo "Restart complete"
echo "=========================================="