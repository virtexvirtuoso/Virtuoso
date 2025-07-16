#!/bin/bash

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