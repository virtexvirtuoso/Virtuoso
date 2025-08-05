#!/bin/bash
# Fix connection timeout issues caused by concurrent API burst

echo "🔧 Deploying Connection Timeout Fix to VPS..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

echo -e "${YELLOW}📊 Current error count (last 5 mins):${NC}"
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso --since '5 minutes ago' | grep -c 'Connection timeout' || echo '0'"

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/main.py src/main.py.backup_conn_fix_$(date +%Y%m%d_%H%M%S)"
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.backup_conn_fix_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading fixed files..."
scp src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/
scp src/core/exchanges/bybit.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/exchanges/

echo "🔄 Restarting Virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso"

echo "⏳ Waiting for service to stabilize..."
sleep 15

echo -e "${GREEN}✅ Fix deployed!${NC}"
echo ""
echo "📊 Monitoring for improvements..."
echo "Waiting 2 minutes to collect data..."
sleep 120

echo -e "${YELLOW}📊 New error count (last 2 mins):${NC}"
NEW_ERRORS=$(ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso --since '2 minutes ago' | grep -c 'Connection timeout' || echo '0'")
echo "Connection timeout errors: ${NEW_ERRORS}"

if [ "$NEW_ERRORS" -lt 5 ]; then
    echo -e "${GREEN}✅ Fix successful! Connection timeouts significantly reduced.${NC}"
else
    echo -e "${RED}⚠️  Still seeing connection timeouts. May need further investigation.${NC}"
fi

echo ""
echo "To monitor logs:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso -f | grep -E \"(Connection timeout|ERROR)\"'"