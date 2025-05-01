#!/bin/bash

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Simplified Bybit Futures Premium Test${NC}"
echo -e "${YELLOW}=====================================${NC}"

# Check if API keys are provided as arguments or if they're already set
if [ "$1" != "" ] && [ "$2" != "" ]; then
    export BYBIT_API_KEY="$1"
    export BYBIT_API_SECRET="$2"
    echo -e "${GREEN}Using provided API keys from arguments${NC}"
elif [ -n "$BYBIT_API_KEY" ] && [ -n "$BYBIT_API_SECRET" ]; then
    echo -e "${GREEN}Using API keys from environment${NC}"
else
    # Use demo keys (may have limited functionality)
    echo -e "${RED}No API keys provided. Using demo values.${NC}"
    echo -e "${RED}For full functionality, run: ./simple_test.sh YOUR_API_KEY YOUR_API_SECRET${NC}"
    export BYBIT_API_KEY="demo"
    export BYBIT_API_SECRET="demo"
fi

# Run the test
echo -e "\n${YELLOW}Starting simplified futures premium test...${NC}"
python simple_futures_premium_test.py

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Test completed successfully!${NC}"
else
    echo -e "\n${RED}Test failed!${NC}"
    echo -e "${YELLOW}Check the error output above for details${NC}"
fi 