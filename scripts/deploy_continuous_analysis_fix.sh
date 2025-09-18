#!/bin/bash

# Continuous Analysis Cache Fix Deployment Script
# Deploys fixes for Continuous Analysis Manager cache population

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
echo -e "${GREEN}🚀 CONTINUOUS ANALYSIS CACHE FIX DEPLOYMENT${NC}"
echo -e "${GREEN}============================================================${NC}"

# Step 1: Create backup on VPS
echo -e "\n${YELLOW}📦 Creating backup on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/pre_continuous_fix_${TIMESTAMP}"
mkdir -p ${BACKUP_DIR}

# Backup main.py
cp src/main.py ${BACKUP_DIR}/

echo "✅ Backup created: ${BACKUP_DIR}"
echo "${BACKUP_DIR}" > /tmp/last_continuous_backup_dir.txt
EOF

# Step 2: Copy fixed file to VPS
echo -e "\n${YELLOW}📤 Transferring fixed file to VPS...${NC}"
scp src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/

echo -e "${GREEN}✅ File transferred successfully${NC}"

# Step 3: Clear cache and restart service
echo -e "\n${YELLOW}🔄 Clearing cache and restarting service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
# Clear memcached to force fresh data
echo 'flush_all' | nc localhost 11211 || echo "  ⚠️  Could not flush memcached"

# Restart service gracefully
sudo systemctl restart virtuoso.service
sleep 5

# Check if service started successfully
if sudo systemctl is-active --quiet virtuoso.service; then
    echo "✅ Service restarted successfully"
    
    # Wait for initialization
    echo "⏳ Waiting for service to initialize..."
    sleep 15
    
    # Check logs for successful cache operations
    echo ""
    echo "📋 Recent cache operations:"
    sudo journalctl -u virtuoso.service --since "1 minute ago" | grep -E "cache|continuous|market overview" | tail -10 || echo "  ℹ️  No cache messages yet"
else
    echo "❌ Service failed to start - initiating rollback"
    
    # Rollback
    BACKUP_DIR=$(cat /tmp/last_continuous_backup_dir.txt)
    cd /home/linuxuser/trading/Virtuoso_ccxt
    cp ${BACKUP_DIR}/main.py src/
    sudo systemctl start virtuoso.service
    
    echo "🔄 Rollback completed"
    exit 1
fi
EOF

# Step 4: Test cache population
echo -e "\n${YELLOW}🧪 Testing cache population...${NC}"
sleep 10  # Give the continuous analysis time to populate cache

# Check if market overview is now populated
echo -e "\n${YELLOW}📊 Checking market overview data...${NC}"
curl -s http://${VPS_HOST}:8003/api/dashboard/market-overview | python3 -c "
import sys, json
data = json.load(sys.stdin)
symbols = data.get('active_symbols', 0)
volume = data.get('total_volume', 0)
print(f'Active Symbols: {symbols}')
print(f'Total Volume: {volume:,.2f}')
if symbols > 0 or volume > 0:
    print('✅ Market overview is now populating!')
else:
    print('⚠️  Market overview still empty - check logs')
"

# Check dashboard data
echo -e "\n${YELLOW}📊 Checking dashboard data...${NC}"
curl -s http://${VPS_HOST}:8003/api/dashboard/data | python3 -c "
import sys, json
data = json.load(sys.stdin)
summary = data.get('summary', {})
symbols = summary.get('total_symbols', 0)
volume = summary.get('total_volume_24h', 0)
print(f'Total Symbols: {symbols}')
print(f'Total Volume: {volume:,.2f}')
if symbols > 0 or volume > 0:
    print('✅ Dashboard data is now populating!')
else:
    print('⚠️  Dashboard data still empty')
"

# Monitor live logs
echo -e "\n${YELLOW}📋 Monitoring live logs (press Ctrl+C to stop)...${NC}"
echo -e "${YELLOW}Looking for cache population messages...${NC}\n"

# Show recent logs with cache operations
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso.service -f | grep -E 'Pushed|cache|continuous|market overview|confluence scores'"