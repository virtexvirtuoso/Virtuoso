#!/bin/bash

# Market Overview Fix Deployment Script
# Deploys market overview calculation fixes to VPS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# VPS Configuration
VPS_HOST="5.223.63.4"
VPS_USER="linuxuser"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}🚀 MARKET OVERVIEW FIX DEPLOYMENT${NC}"
echo -e "${GREEN}============================================================${NC}"

# Step 1: Create backup on VPS
echo -e "\n${YELLOW}📦 Creating backup on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/pre_market_overview_fix_${TIMESTAMP}"
mkdir -p ${BACKUP_DIR}

# Backup critical files
cp src/api/cache_adapter_direct.py ${BACKUP_DIR}/ 2>/dev/null || true
cp src/dashboard/dashboard_integration.py ${BACKUP_DIR}/

echo "✅ Backup created: ${BACKUP_DIR}"
echo "${BACKUP_DIR}" > /tmp/last_market_backup_dir.txt
EOF

# Step 2: Copy fixed files to VPS
echo -e "\n${YELLOW}📤 Transferring fixed files to VPS...${NC}"

# Transfer the modified files
scp src/api/cache_adapter_direct.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/api/ 2>/dev/null || echo "  ⚠️  cache_adapter_direct.py may not exist"
scp src/dashboard/dashboard_integration.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/

echo -e "${GREEN}✅ Files transferred successfully${NC}"

# Step 3: Clear cache and restart service
echo -e "\n${YELLOW}🔄 Clearing cache and restarting service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
# Clear memcached to force recalculation
echo 'flush_all' | nc localhost 11211 || echo "  ⚠️  Could not flush memcached"

# Restart service gracefully
sudo systemctl restart virtuoso.service
sleep 5

# Check if service started successfully
if sudo systemctl is-active --quiet virtuoso.service; then
    echo "✅ Service restarted successfully"
else
    echo "❌ Service failed to start - initiating rollback"
    
    # Rollback
    BACKUP_DIR=$(cat /tmp/last_market_backup_dir.txt)
    cd /home/linuxuser/trading/Virtuoso_ccxt
    cp ${BACKUP_DIR}/* src/ -r
    sudo systemctl start virtuoso.service
    
    echo "🔄 Rollback completed"
    exit 1
fi
EOF

# Step 4: Wait for service to initialize
echo -e "\n${YELLOW}⏳ Waiting for service to initialize and populate cache...${NC}"
sleep 15

# Step 5: Test the deployment
echo -e "\n${YELLOW}🧪 Testing deployment...${NC}"

# Run the comprehensive test
./venv311/bin/python scripts/test_dashboard_fixes_comprehensive.py --vps

# Check test result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL!${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo -e "\n${YELLOW}📊 Dashboard URLs:${NC}"
    echo -e "  • Desktop: http://${VPS_HOST}:8003/"
    echo -e "  • Mobile: http://${VPS_HOST}:8003/mobile"
    echo -e "  • API Data: http://${VPS_HOST}:8003/api/dashboard/data"
    echo -e "  • Market Overview: http://${VPS_HOST}:8003/api/dashboard/market-overview"
    echo -e "\n${GREEN}✅ Market overview should now show proper values!${NC}"
else
    echo -e "\n${YELLOW}⚠️  Some issues remain - checking if improvements were made...${NC}"
    
    # Check if we at least got some data
    curl -s http://${VPS_HOST}:8003/api/dashboard/mobile-data | python3 -c "
import sys, json
data = json.load(sys.stdin)
overview = data.get('market_overview', {})
volume = overview.get('total_volume_24h', 0)
symbols = overview.get('active_symbols', 0)
print(f'Market Volume: {volume:,.2f}')
print(f'Active Symbols: {symbols}')
if volume > 0 or symbols > 0:
    print('✅ Partial improvement detected!')
else:
    print('❌ No improvement in market overview')
"
fi

echo -e "\n${YELLOW}📋 Manual verification:${NC}"
echo -e "1. Check dashboard: http://${VPS_HOST}:8003/"
echo -e "2. Check mobile: http://${VPS_HOST}:8003/mobile"
echo -e "3. Monitor logs: ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"