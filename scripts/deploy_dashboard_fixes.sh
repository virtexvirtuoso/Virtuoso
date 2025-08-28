#!/bin/bash
"""
Deploy Dashboard Performance Fixes to VPS
Quickly deploys the emergency fixes for dashboard performance
"""

set -e  # Exit on any error

echo "🚀 Deploying Dashboard Performance Fixes to VPS"
echo "=================================================="

# Configuration
VPS_HOST="45.77.40.77"
VPS_USER="linuxuser"
VPS_PROJECT_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Step 1: Syncing files to VPS...${NC}"
rsync -avz --progress \
    src/api/routes/dashboard_cached.py \
    src/api/cache_adapter_direct.py \
    ${VPS_USER}@${VPS_HOST}:${VPS_PROJECT_PATH}/

echo -e "${BLUE}📦 Step 2: Backing up current files on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    cd ${VPS_PROJECT_PATH}
    cp src/api/routes/dashboard_cached.py src/api/routes/dashboard_cached.py.backup.\$(date +%s) || echo 'No existing file'
    cp src/api/cache_adapter_direct.py src/api/cache_adapter_direct.py.backup.\$(date +%s) || echo 'No existing file'
"

echo -e "${BLUE}🔄 Step 3: Restarting Virtuoso service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    sudo systemctl stop virtuoso.service
    sleep 3
    sudo systemctl start virtuoso.service
    sleep 5
"

echo -e "${BLUE}✅ Step 4: Verifying deployment...${NC}"
ssh ${VPS_USER}@${VPS_HOST} "
    echo 'Service status:'
    sudo systemctl is-active virtuoso.service || echo 'Service not active'
    
    echo 'Recent logs:'
    sudo journalctl -u virtuoso.service --no-pager -n 10
    
    echo 'Testing endpoints:'
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/overview || echo 'Endpoint test failed'
    echo
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/mobile-data || echo 'Endpoint test failed'  
    echo
    curl -s -o /dev/null -w 'HTTP %{http_code} - %{time_total}s' http://localhost:8003/api/dashboard-cached/opportunities || echo 'Endpoint test failed'
    echo
"

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo "Monitor with: ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"
echo "Test endpoints:"
echo "  curl http://45.77.40.77:8003/api/dashboard-cached/overview"
echo "  curl http://45.77.40.77:8003/api/dashboard-cached/mobile-data"
echo "  curl http://45.77.40.77:8003/api/dashboard-cached/opportunities"

exit 0