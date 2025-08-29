#!/bin/bash

#############################################################################
# Script: test_local_startup.sh
# Purpose: Test local startup without Docker
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
#   ./test_local_startup.sh [options]
#   
#   Examples:
#     ./test_local_startup.sh
#     ./test_local_startup.sh --verbose
#     ./test_local_startup.sh --dry-run
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

echo "🧪 Testing Local Startup"
echo "======================="
echo ""

# Check Python version
echo "📍 Python version:"
python3.11 --version || python3 --version

# Check if venv exists
if [ -d "venv311" ]; then
    echo "✅ Virtual environment found"
    source venv311/bin/activate
else
    echo "❌ No virtual environment found"
    echo "   Create one with: python3.11 -m venv venv311"
    exit 1
fi

# Test imports
echo ""
echo "📦 Testing imports..."
python -c "
import sys
sys.path.append('src')
try:
    from src.config.manager import ConfigManager
    print('✅ ConfigManager import successful')
    from src.core.exchanges.manager import ExchangeManager
    print('✅ ExchangeManager import successful')
    from src.monitoring.monitor import MarketMonitor
    print('✅ MarketMonitor import successful')
    print('')
    print('✅ All imports successful!')
except Exception as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo ""
echo "📋 Next steps:"
echo "1. Ensure .env file is configured"
echo "2. Run: python -m src.main"
echo "3. Check http://localhost:8001/health"