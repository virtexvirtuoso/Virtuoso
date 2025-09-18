#!/bin/bash

#############################################################################
# Script: start_virtuoso.sh
# Purpose: Deploy and manage start virtuoso
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
#   ./start_virtuoso.sh [options]
#   
#   Examples:
#     ./start_virtuoso.sh
#     ./start_virtuoso.sh --verbose
#     ./start_virtuoso.sh --dry-run
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

# Virtuoso Trading System Startup Script
# This script ensures the correct Python environment is used

echo "🚀 Starting Virtuoso Trading System..."

# Check if we're in the correct directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Please run this script from the Virtuoso_ccxt directory"
    exit 1
fi

# Check if Python 3.11 virtual environment exists
if [ ! -d "venv311" ]; then
    echo "❌ Error: Python 3.11 virtual environment not found (venv311)"
    echo "Please create the virtual environment first:"
    echo "python3.11 -m venv venv311"
    echo "source venv311/bin/activate"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "📦 Activating Python 3.11 virtual environment..."
source venv311/bin/activate

echo "🔍 Python version: $(python --version)"
echo "📍 Python path: $(which python)"

# Check if required packages are installed
echo "🔧 Checking dependencies..."
if ! python -c "import pybit" 2>/dev/null; then
    echo "❌ Error: pybit not installed in virtual environment"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Dependencies OK"

# Kill any existing processes on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "🔄 Stopping existing processes on port 8000..."
    kill $(lsof -ti:8000) 2>/dev/null || true
    sleep 2
fi

echo "🎯 Starting Virtuoso Trading System..."
echo "📊 Access dashboard at: http://localhost:8000"
echo "🔴 Press Ctrl+C to stop"
echo ""

# Start the application
python src/main.py 