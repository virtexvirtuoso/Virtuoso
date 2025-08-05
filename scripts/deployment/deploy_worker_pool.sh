#!/bin/bash
# Deploy worker pool integration to VPS

echo "🚀 Deploying Worker Pool Integration to VPS..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# VPS details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Check if files exist locally
if [ ! -f "src/core/worker_pool_manager.py" ]; then
    echo -e "${RED}Error: src/core/worker_pool_manager.py not found locally${NC}"
    exit 1
fi

echo "📦 Creating backup on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && cp src/main.py src/main.py.backup_$(date +%Y%m%d_%H%M%S)"

echo "📤 Uploading worker pool manager..."
scp src/core/worker_pool_manager.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/core/

echo "📤 Uploading updated main.py..."
scp src/main.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/

echo "📝 Uploading documentation..."
scp WORKER_POOL_INTEGRATION.md ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/

echo "🔄 Restarting Virtuoso service..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl restart virtuoso"

echo "⏳ Waiting for service to start..."
sleep 10

echo "✅ Checking service status..."
ssh ${VPS_USER}@${VPS_HOST} "sudo systemctl status virtuoso | grep -E 'Active:|Main PID:'"

echo "🔍 Checking for worker pool initialization..."
ssh ${VPS_USER}@${VPS_HOST} "sudo journalctl -u virtuoso -n 50 | grep -i 'worker pool' | tail -5"

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "To monitor the service:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso -f'"
echo ""
echo "To check worker processes:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'ps aux | grep python | grep main.py'"