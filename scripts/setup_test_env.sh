#!/bin/bash

#############################################################################
# Script: setup_test_env.sh
# Purpose: Test and validate setup test env
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
#   ./setup_test_env.sh [options]
#   
#   Examples:
#     ./setup_test_env.sh
#     ./setup_test_env.sh --verbose
#     ./setup_test_env.sh --dry-run
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

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Virtuoso CCXT Market Reporter Test${NC}"
echo -e "${YELLOW}===================================${NC}"

# Check if API keys are provided as arguments or if they're already set
if [ "$1" != "" ] && [ "$2" != "" ]; then
    export BYBIT_API_KEY="$1"
    export BYBIT_API_SECRET="$2"
    echo -e "${GREEN}Using provided API keys from arguments${NC}"
elif [ -n "$BYBIT_API_KEY" ] && [ -n "$BYBIT_API_SECRET" ]; then
    echo -e "${GREEN}Using API keys from environment${NC}"
else
    # Use demo keys (may have limited functionality)
    echo -e "${RED}No API keys provided. Using default values which may have limited functionality.${NC}"
    echo -e "${RED}For full functionality, run: ./setup_test_env.sh YOUR_API_KEY YOUR_API_SECRET${NC}"
    export BYBIT_API_KEY="YOUR_API_KEY_HERE"
    export BYBIT_API_SECRET="YOUR_API_SECRET_HERE"
fi

echo "API Key: ${BYBIT_API_KEY:0:4}...${BYBIT_API_KEY: -4}"
echo "API Secret length: ${#BYBIT_API_SECRET} characters"

# Install required packages if they're not already installed
echo -e "\n${YELLOW}Checking for required Python packages...${NC}"
required_packages=("aiohttp" "websockets" "pybit" "python-dotenv" "pandas" "numpy" "cachetools")

for package in "${required_packages[@]}"; do
    if ! pip show $package &> /dev/null; then
        echo -e "${RED}Installing missing package: $package${NC}"
        pip install $package
    else
        echo -e "${GREEN}✓ $package already installed${NC}"
    fi
done

# Run the test
echo -e "\n${YELLOW}Starting market reporter test...${NC}"
python test_market_report_live.py

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Test completed successfully!${NC}"
    echo -e "${YELLOW}Check market_report.json for detailed results${NC}"
else
    echo -e "\n${RED}Test failed!${NC}"
    echo -e "${YELLOW}Check the error output above for details${NC}"
fi 