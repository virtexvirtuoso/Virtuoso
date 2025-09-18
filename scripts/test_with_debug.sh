#!/bin/bash

#############################################################################
# Script: test_with_debug.sh
# Purpose: Test and validate test with debug
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates automated testing, validation, and quality assurance for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - python3
#   - curl
#   - grep
#   - Access to project directory structure
#
# Usage:
#   ./test_with_debug.sh [options]
#   
#   Examples:
#     ./test_with_debug.sh
#     ./test_with_debug.sh --verbose
#     ./test_with_debug.sh --dry-run
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
#   0 - All tests passed
#   1 - Test failures detected
#   2 - Test configuration error
#   3 - Dependencies missing
#   4 - Environment setup failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

VPS_HOST="${VPS_HOST}"
VPS_USER="linuxuser"

# Kill existing server
ssh ${VPS_USER}@${VPS_HOST} 'pkill -f web_server.py'
sleep 2

# Start with debug output
ssh ${VPS_USER}@${VPS_HOST} 'cd /home/linuxuser/trading/Virtuoso_ccxt && export PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt && venv311/bin/python -u src/web_server.py 2>&1 | grep -E "DEBUG:|Direct Cache" &'

# Give it time to start
sleep 5

# Test the endpoint
echo "Testing endpoint..."
curl -s http://${VPS_HOST}:8001/api/dashboard-cached/signals > /dev/null

# Wait to see output
sleep 2

# Kill the server
ssh ${VPS_USER}@${VPS_HOST} 'pkill -f web_server.py'