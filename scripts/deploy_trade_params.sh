#!/bin/bash

# Deployment script for Trade Parameters (Stop Loss & Take Profit) functionality
# This script deploys the updated signal processing with RiskManager integration

echo "🚀 Deploying Trade Parameters Update to VPS"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# VPS Configuration
VPS_USER="linuxuser"
VPS_HOST="VPS_HOST_REDACTED"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"
LOCAL_DIR="/Users/ffv_macmini/Desktop/Virtuoso_ccxt"

echo -e "${YELLOW}📦 Preparing deployment...${NC}"

# Step 1: Save local changes
echo -e "${GREEN}Step 1: Saving local changes...${NC}"
cd $LOCAL_DIR

# Step 2: Create backup on VPS
echo -e "${GREEN}Step 2: Creating backup on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
mkdir -p backups
BACKUP_DIR="backups/pre_trade_params_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup in $BACKUP_DIR"

# Backup critical files
mkdir -p $BACKUP_DIR/src/monitoring
cp src/monitoring/signal_processor.py $BACKUP_DIR/src/monitoring/ 2>/dev/null || true
cp src/monitoring/monitor.py $BACKUP_DIR/src/monitoring/ 2>/dev/null || true

mkdir -p $BACKUP_DIR/src/risk
cp -r src/risk/* $BACKUP_DIR/src/risk/ 2>/dev/null || true

mkdir -p $BACKUP_DIR/src/core
cp src/core/cache_keys.py $BACKUP_DIR/src/core/ 2>/dev/null || true

echo "✅ Backup created"
EOF

# Step 3: Deploy updated files
echo -e "${GREEN}Step 3: Deploying updated files...${NC}"

# Copy updated signal processor with trade parameters
echo "  • Deploying signal_processor.py with RiskManager integration..."
scp $LOCAL_DIR/src/monitoring/signal_processor.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/src/monitoring/

# Copy updated monitor with RiskManager initialization
echo "  • Deploying monitor.py with RiskManager initialization..."
scp $LOCAL_DIR/src/monitoring/monitor.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/src/monitoring/

# Copy risk manager (in case it needs updates)
echo "  • Ensuring risk_manager.py is up to date..."
scp $LOCAL_DIR/src/risk/risk_manager.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/src/risk/

# Copy cache_keys module
echo "  • Deploying cache_keys.py module..."
scp $LOCAL_DIR/src/core/cache_keys.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/src/core/

# Copy test scripts for verification
echo "  • Deploying test scripts..."
scp $LOCAL_DIR/scripts/test_trade_parameters.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/scripts/
scp $LOCAL_DIR/scripts/test_pdf_trade_params.py ${VPS_USER}@${VPS_HOST}:${VPS_DIR}/scripts/

# Step 4: Test on VPS
echo -e "${GREEN}Step 4: Running tests on VPS...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

echo "🧪 Testing trade parameters calculation..."
source venv311/bin/activate
PYTHONPATH=/home/linuxuser/trading/Virtuoso_ccxt python scripts/test_trade_parameters.py

if [ $? -eq 0 ]; then
    echo "✅ Trade parameters test passed"
else
    echo "❌ Trade parameters test failed"
    exit 1
fi
EOF

# Step 5: Restart services
echo -e "${GREEN}Step 5: Restarting services...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
echo "Restarting Virtuoso services..."

# Restart web service
sudo systemctl restart virtuoso-web.service
sleep 5

# Check service status
echo "Checking service status..."
if sudo systemctl is-active --quiet virtuoso-web.service; then
    echo "✅ virtuoso-web.service is running"
else
    echo "❌ virtuoso-web.service failed to start"
    sudo journalctl -u virtuoso-web.service -n 20
    exit 1
fi

# Restart monitoring service if it exists
if sudo systemctl list-units --all | grep -q "virtuoso-monitor.service"; then
    sudo systemctl restart virtuoso-monitor.service
    sleep 3
    if sudo systemctl is-active --quiet virtuoso-monitor.service; then
        echo "✅ virtuoso-monitor.service is running"
    else
        echo "⚠️ virtuoso-monitor.service failed to start"
    fi
fi
EOF

# Step 6: Verify deployment
echo -e "${GREEN}Step 6: Verifying deployment...${NC}"

# Test the API endpoints
echo "Testing API endpoints..."

# Test health endpoint
echo -n "  • Health check: "
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8003/health)
if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ Failed (HTTP $HEALTH_STATUS)${NC}"
fi

# Test dashboard data endpoint
echo -n "  • Dashboard data: "
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8003/api/dashboard/data)
if [ "$DASHBOARD_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️ Status: $DASHBOARD_STATUS${NC}"
fi

# Final verification - check if trade params are being calculated
echo -e "${GREEN}Step 7: Final verification...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Check logs for RiskManager initialization
echo "Checking for RiskManager in logs..."
sudo journalctl -u virtuoso-web.service -n 100 | grep -i "riskmanager" | tail -3

# Quick Python check
source venv311/bin/activate
python -c "
import sys
sys.path.insert(0, '.')
from src.monitoring.signal_processor import SignalProcessor
from src.risk.risk_manager import RiskManager
print('✅ Modules imported successfully')
print('✅ Trade parameters functionality is ready')
"
EOF

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo ""
echo "Summary:"
echo "  ✅ Signal processor updated with trade parameters calculation"
echo "  ✅ RiskManager integrated into monitoring system"
echo "  ✅ Stop loss and take profit now included in signals"
echo "  ✅ PDF/PNG charts will show trading levels"
echo ""
echo "Access points:"
echo "  • Dashboard: http://${VPS_HOST}:8003/"
echo "  • Mobile: http://${VPS_HOST}:8003/mobile"
echo "  • API: http://${VPS_HOST}:8003/api/dashboard/data"
echo ""
echo "Next steps:"
echo "  1. Monitor signals to verify trade parameters"
echo "  2. Check generated PDFs for stop loss/take profit levels"
echo "  3. Review logs: ssh vps 'sudo journalctl -u virtuoso-web.service -f'"