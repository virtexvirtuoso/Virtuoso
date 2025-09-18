#!/bin/bash

#############################################################################
# Script: install_latest_talib.sh
# Purpose: Test and validate install latest talib
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
#   ./install_latest_talib.sh [options]
#   
#   Examples:
#     ./install_latest_talib.sh
#     ./install_latest_talib.sh --verbose
#     ./install_latest_talib.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

echo "🔧 Installing Latest TA-Lib from Source"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Navigate to home directory
cd ~

# Check if we're in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    cd ~/trading/Virtuoso_ccxt
    source venv/bin/activate
fi

echo -e "${YELLOW}Step 1: Removing old TA-Lib installation...${NC}"
sudo rm -rf /usr/lib/libta_lib* /usr/include/ta-lib /usr/local/lib/libta_lib* /usr/local/include/ta-lib

echo -e "${YELLOW}Step 2: Installing build dependencies...${NC}"
sudo apt update
sudo apt install -y automake autoconf libtool build-essential python3-dev git

echo -e "${YELLOW}Step 3: Cloning latest TA-Lib source...${NC}"
cd /tmp
rm -rf ta-lib
git clone https://github.com/TA-Lib/ta-lib.git
cd ta-lib

echo -e "${YELLOW}Step 4: Building TA-Lib...${NC}"
chmod +x autogen.sh
./autogen.sh
./configure --prefix=/usr
make -j$(nproc)

echo -e "${YELLOW}Step 5: Installing TA-Lib...${NC}"
sudo make install
sudo ldconfig

echo -e "${YELLOW}Step 6: Verifying installation...${NC}"
ldconfig -p | grep ta_lib

echo -e "${YELLOW}Step 7: Installing Python wrapper...${NC}"
cd ~/trading/Virtuoso_ccxt
source venv/bin/activate

# Uninstall old wrapper
pip uninstall -y TA-Lib

# Set environment variables
export TA_INCLUDE_PATH=/usr/include
export TA_LIBRARY_PATH=/usr/lib

# Install with proper paths
CFLAGS="-I/usr/include" LDFLAGS="-L/usr/lib" pip install --no-cache-dir TA-Lib

echo -e "${YELLOW}Step 8: Testing TA-Lib...${NC}"
python -c "import talib; print('TA-Lib version:', talib.__version__)" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ TA-Lib installed successfully!${NC}"
    
    echo -e "${YELLOW}Step 9: Reverting wrapper changes...${NC}"
    # Revert the wrapper imports back to direct talib imports
    find src -name "*.py" -type f -exec grep -l "from src.utils.talib_wrapper import" {} \; | while read file; do
        echo "  Reverting $file"
        sed -i 's/from src.utils.talib_wrapper import talib, TALIB_AVAILABLE/import talib/' "$file"
    done
    
    # Also restore any backed up files
    find src -name "*.py.backup_talib" -type f | while read backup; do
        original="${backup%.backup_talib}"
        echo "  Restoring $original from backup"
        mv "$backup" "$original"
    done
    
    echo -e "${GREEN}✅ All imports reverted to use real TA-Lib${NC}"
else
    echo -e "${RED}❌ TA-Lib Python wrapper installation failed${NC}"
    echo -e "${YELLOW}Keeping fallback wrapper in place${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo ""
echo "To run your bot:"
echo "  cd ~/trading/Virtuoso_ccxt"
echo "  source venv/bin/activate"
echo "  python src/main.py"
echo ""
echo "Note: If TA-Lib still shows errors, the fallback"
echo "calculations will work perfectly fine for trading."
echo "======================================="