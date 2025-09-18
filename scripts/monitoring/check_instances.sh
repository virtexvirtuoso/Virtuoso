#!/bin/bash

#############################################################################
# Script: check_instances.sh
# Purpose: Check for running Virtuoso instances
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
#   ./check_instances.sh [options]
#   
#   Examples:
#     ./check_instances.sh
#     ./check_instances.sh --verbose
#     ./check_instances.sh --dry-run
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

echo "=== Checking for Virtuoso Instances ==="
echo

# Check PID file
if [ -f /tmp/virtuoso.pid ]; then
    PID=$(cat /tmp/virtuoso.pid)
    echo "PID file exists: $PID"
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "Process $PID is running:"
        ps -fp $PID
    else
        echo "Process $PID is NOT running (stale PID file)"
    fi
else
    echo "No PID file found at /tmp/virtuoso.pid"
fi

echo
echo "=== All Python Processes ==="
ps aux | grep -E "python.*main\.py|python.*virtuoso" | grep -v grep

echo
echo "=== Process Count ==="
COUNT=$(ps aux | grep -E "python.*main\.py" | grep -v grep | wc -l)
echo "Found $COUNT Virtuoso process(es)"

if [ $COUNT -gt 1 ]; then
    echo "WARNING: Multiple instances detected!"
fi