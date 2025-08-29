#!/bin/bash

#############################################################################
# Script: launch_virtuoso.sh
# Purpose: Deploy and manage launch virtuoso
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
#   ./launch_virtuoso.sh [options]
#   
#   Examples:
#     ./launch_virtuoso.sh
#     ./launch_virtuoso.sh --verbose
#     ./launch_virtuoso.sh --dry-run
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

# Virtuoso Trading System Launcher
echo "🚀 Starting Virtuoso Trading System..."

# Navigate to project directory
cd /Users/ffv_macmini/Desktop/Virtuoso_ccxt

# Activate virtual environment
source venv311/bin/activate

# Check if port 8001 is in use and kill if necessary
if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8001 is in use. Killing existing process..."
    lsof -ti:8001 | xargs kill -9
    sleep 2
fi

# Start the application
echo "✅ Environment activated. Starting main.py..."
python src/main.py 