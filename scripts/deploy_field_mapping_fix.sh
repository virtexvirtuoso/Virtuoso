#!/bin/bash

# Dashboard Field Mapping Fix Deployment Script
# Safely deploys field mapping fixes to VPS with rollback capability

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
echo -e "${GREEN}🚀 DASHBOARD FIELD MAPPING FIX DEPLOYMENT${NC}"
echo -e "${GREEN}============================================================${NC}"

# Step 1: Create backup on VPS
echo -e "\n${YELLOW}📦 Creating backup on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/pre_field_fix_${TIMESTAMP}"
mkdir -p ${BACKUP_DIR}

# Backup critical files
cp src/core/exchanges/bybit.py ${BACKUP_DIR}/
cp src/dashboard/dashboard_integration.py ${BACKUP_DIR}/
cp src/api/cache_adapter_direct.py ${BACKUP_DIR}/ 2>/dev/null || true

echo "✅ Backup created: ${BACKUP_DIR}"
echo "${BACKUP_DIR}" > /tmp/last_backup_dir.txt
EOF

# Step 2: Copy fixed files to VPS
echo -e "\n${YELLOW}📤 Transferring fixed files to VPS...${NC}"

# Transfer the modified files
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/
scp src/dashboard/dashboard_integration.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/dashboard/

echo -e "${GREEN}✅ Files transferred successfully${NC}"

# Step 3: Restart service gracefully
echo -e "\n${YELLOW}🔄 Restarting Virtuoso service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
# Stop service gracefully
sudo systemctl stop virtuoso.service
sleep 2

# Start service
sudo systemctl start virtuoso.service
sleep 5

# Check if service started successfully
if sudo systemctl is-active --quiet virtuoso.service; then
    echo "✅ Service restarted successfully"
else
    echo "❌ Service failed to start - initiating rollback"
    
    # Rollback
    BACKUP_DIR=$(cat /tmp/last_backup_dir.txt)
    cd /home/linuxuser/trading/Virtuoso_ccxt
    cp ${BACKUP_DIR}/* src/ -r
    sudo systemctl start virtuoso.service
    
    echo "🔄 Rollback completed"
    exit 1
fi
EOF

# Step 4: Test the deployment
echo -e "\n${YELLOW}🧪 Testing deployment...${NC}"

# Wait for service to fully initialize
sleep 10

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
    echo -e "\n${YELLOW}📋 Next Steps:${NC}"
    echo -e "  1. Monitor the dashboard for proper data display"
    echo -e "  2. Check market overview values are non-zero"
    echo -e "  3. Verify confluence scores are calculating"
else
    echo -e "\n${RED}⚠️  Tests failed - consider rollback${NC}"
    echo -e "${YELLOW}To rollback manually:${NC}"
    echo -e "ssh ${VPS_USER}@${VPS_HOST}"
    echo -e "cd ${VPS_PATH}"
    echo -e "BACKUP_DIR=\$(cat /tmp/last_backup_dir.txt)"
    echo -e "cp \${BACKUP_DIR}/* src/ -r"
    echo -e "sudo systemctl restart virtuoso.service"
    exit 1
fi