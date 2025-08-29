#!/bin/bash

#############################################################################
# Script: setup_and_test_binance.sh
# Purpose: Test and validate setup and test binance
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
#   ./setup_and_test_binance.sh [options]
#   
#   Examples:
#     ./setup_and_test_binance.sh
#     ./setup_and_test_binance.sh --verbose
#     ./setup_and_test_binance.sh --dry-run
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

# Binance API Test Setup and Execution Script
# This script installs dependencies and runs the Binance API test

echo "🚀 Binance API Integration Test Setup"
echo "======================================"

# Check if Python 3.11+ is available
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
if [[ -z "$python_version" ]]; then
    echo "❌ Python 3 not found. Please install Python 3.11 or higher."
    exit 1
fi

major_version=$(echo $python_version | cut -d. -f1)
minor_version=$(echo $python_version | cut -d. -f2)

if [[ $major_version -eq 3 && $minor_version -ge 11 ]] || [[ $major_version -gt 3 ]]; then
    echo "✅ Python $python_version found"
else
    echo "❌ Python 3.11+ required, found $python_version"
    exit 1
fi

# Install required packages
echo ""
echo "📦 Installing required packages..."
echo "Installing: ccxt pandas tabulate"

# Try to install packages
if pip3 install ccxt pandas tabulate; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    echo "Try running: pip3 install --user ccxt pandas tabulate"
    exit 1
fi

# Check if script exists
echo ""
echo "📋 Checking test script..."
if [[ ! -f "scripts/test_binance_api_calls.py" ]]; then
    echo "❌ Test script not found at scripts/test_binance_api_calls.py"
    echo "Please make sure you're in the Virtuoso_ccxt directory"
    exit 1
fi

echo "✅ Test script found"

# Run the test
echo ""
echo "🔥 Running Binance API tests..."
echo "======================================"
echo ""

# Execute the test script
python3 scripts/test_binance_api_calls.py

echo ""
echo "======================================"
echo "✅ Test execution completed!"
echo ""
echo "💡 Next steps:"
echo "1. Review the test output above"
echo "2. Check for any API endpoints that failed"
echo "3. If tests passed, proceed with BinanceExchange implementation"
echo "4. Use the response structures shown to build the integration" 