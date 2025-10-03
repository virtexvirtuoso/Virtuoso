#!/bin/bash
set -e

echo "🚀 Deploying Mock Data Fixes to VPS"
echo "=================================="

VPS_HOST=${VPS_HOST:-"vps"}
PROJECT_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📋 Step 1: Backup current VPS state"
ssh $VPS_HOST "cd $PROJECT_DIR && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'No .env to backup'"

echo "📋 Step 2: Apply environment configuration fixes"
ssh $VPS_HOST "cd $PROJECT_DIR && 
    echo 'EXCHANGE_DEMO_MODE=false' > .env.deploy_fix &&
    echo 'ANALYSIS_MODE=false' >> .env.deploy_fix &&
    if [ -f .env ]; then
        grep -v 'EXCHANGE_DEMO_MODE\|ANALYSIS_MODE' .env >> .env.deploy_fix || true
    fi &&
    mv .env.deploy_fix .env &&
    echo '✅ Environment configuration updated'"

echo "📋 Step 3: Restart services with new configuration"
ssh $VPS_HOST "cd $PROJECT_DIR && 
    echo 'Stopping existing services...' &&
    pkill -f 'python.*main.py' 2>/dev/null || echo 'No main.py running' &&
    pkill -f 'python.*web_server.py' 2>/dev/null || echo 'No web_server.py running' &&
    sleep 3 &&
    echo 'Starting services with real market data...' &&
    source venv311/bin/activate &&
    nohup python src/main.py > logs/deploy_main_\$(date +%H%M%S).log 2>&1 & &&
    sleep 5 &&
    nohup python src/web_server.py > logs/deploy_web_\$(date +%H%M%S).log 2>&1 & &&
    echo '✅ Services restarted with production configuration'"

echo "📋 Step 4: Verify real market data is being used"
ssh $VPS_HOST "cd $PROJECT_DIR && 
    sleep 10 &&
    echo 'Checking for real market prices in logs...' &&
    tail -30 logs/app.log 2>/dev/null | grep -E '[0-9]{5,}.*BTC|BTC.*[0-9]{5,}' | head -2 || echo 'No BTC price data found yet'"

echo ""
echo "🎯 Deployment Complete!"
echo "✅ Demo mode disabled on VPS"
echo "✅ Services restarted with production config"
echo "🔍 Monitor logs for real $115K+ BTC prices"

