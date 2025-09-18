#!/bin/bash

# Deploy OHLCV cache connection fix to VPS
# This fixes the issue where charts weren't being included in Discord alerts
# by properly connecting cached OHLCV data between components

echo "🚀 Deploying OHLCV cache connection fix to VPS..."

# VPS connection details
VPS_HOST="linuxuser@VPS_HOST_REDACTED"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}📦 Syncing updated files to VPS...${NC}"

# Files to sync
FILES=(
    "src/main.py"
    "src/signal_generation/signal_generator.py"
    "src/data_processing/data_processor.py"
)

# Sync each file
for FILE in "${FILES[@]}"; do
    echo -e "${GREEN}  → Syncing $FILE${NC}"
    rsync -avz --progress "$FILE" "$VPS_HOST:$VPS_DIR/$FILE"
done

echo -e "${YELLOW}🔄 Restarting services on VPS...${NC}"

# Restart the trading service
ssh $VPS_HOST << 'EOF'
    echo "Stopping virtuoso-trading service..."
    sudo systemctl stop virtuoso-trading.service
    
    echo "Waiting for service to stop..."
    sleep 3
    
    echo "Starting virtuoso-trading service..."
    sudo systemctl start virtuoso-trading.service
    
    echo "Checking service status..."
    sudo systemctl status virtuoso-trading.service --no-pager | head -20
EOF

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Monitor the logs with:"
echo "  ssh vps \"sudo journalctl -u virtuoso-trading.service -f | grep -E 'DEBUG.*OHLCV|chart|PDF'\""
echo ""
echo "Key changes deployed:"
echo "  1. Signal generator now checks monitor's cache first, then market_data_manager"
echo "  2. DataProcessor also checks both caches before fetching from exchange"
echo "  3. Monitor reference is passed to signal_generator in main.py"
echo "  4. All cache formats (monitor-style and manager-style) are handled"
echo ""
echo -e "${YELLOW}Expected behavior:${NC}"
echo "  - OHLCV data should be found in cache (no exchange fetches)"
echo "  - Charts should be included in Discord alerts"
echo "  - Debug logs will show: '🎯 DEBUG: Found cached OHLCV data'"