#!/bin/bash

# Test script for Virtuoso dashboard on remote server

REMOTE_HOST="45.77.40.77"
PORT="8003"

echo "🧪 Testing Virtuoso Dashboard on ${REMOTE_HOST}:${PORT}"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test function
test_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -n "Testing ${description}... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "http://${REMOTE_HOST}:${PORT}${endpoint}")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ OK${NC} (${response})"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (${response})"
        return 1
    fi
}

# Test HTML endpoints
echo -e "\n${YELLOW}HTML Endpoints:${NC}"
test_endpoint "/dashboard" "Desktop Dashboard"
test_endpoint "/dashboard/mobile" "Mobile Dashboard"
test_endpoint "/dashboard/desktop" "Desktop Dashboard (explicit)"
test_endpoint "/dashboard/v10" "Legacy v10 Dashboard"
test_endpoint "/dashboard/v1" "Original Dashboard"

# Test API endpoints
echo -e "\n${YELLOW}API Endpoints:${NC}"
test_endpoint "/api/dashboard/overview" "Dashboard Overview API"
test_endpoint "/api/market/overview" "Market Overview API"
test_endpoint "/health" "Health Check"
test_endpoint "/version" "Version Info"

# Test static resources
echo -e "\n${YELLOW}Static Resources:${NC}"
test_endpoint "/static/manifest.json" "PWA Manifest"

# Test WebSocket endpoint
echo -e "\n${YELLOW}WebSocket Test:${NC}"
echo -n "Testing WebSocket connection... "
timeout 2 bash -c "echo '' | nc ${REMOTE_HOST} ${PORT}" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Port accessible${NC}"
else
    echo -e "${RED}✗ Port not accessible${NC}"
fi

# Test API response content
echo -e "\n${YELLOW}API Response Test:${NC}"
echo "Dashboard Overview Response:"
curl -s "http://${REMOTE_HOST}:${PORT}/api/dashboard/overview" | python3 -m json.tool 2>/dev/null | head -15 || echo "Failed to parse JSON"

echo -e "\n${YELLOW}Dashboard URLs:${NC}"
echo "Desktop: http://${REMOTE_HOST}:${PORT}/dashboard"
echo "Mobile:  http://${REMOTE_HOST}:${PORT}/dashboard/mobile"
echo "Legacy:  http://${REMOTE_HOST}:${PORT}/dashboard/v10"

echo -e "\n✅ Test completed!"