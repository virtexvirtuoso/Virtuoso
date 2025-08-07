#!/bin/bash

# Simple deployment script for cache optimizations
# Phases 1-3 to VPS

echo "======================================"
echo "DEPLOYING CACHE OPTIMIZATIONS TO VPS"
echo "======================================"

VPS="linuxuser@45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# First, let's just copy the cache directory
echo "1. Creating cache directory structure..."
ssh $VPS "mkdir -p $VPS_PATH/src/core/cache"

echo "2. Copying cache implementation files..."
# Core cache files
scp -q src/core/cache/*.py $VPS:$VPS_PATH/src/core/cache/ 2>/dev/null || true
scp -q src/core/api_cache.py $VPS:$VPS_PATH/src/core/ 2>/dev/null || true

echo "3. Copying updated integration files..."
# Updated files that use caching
scp -q src/indicators/base_indicator.py $VPS:$VPS_PATH/src/indicators/
scp -q src/indicators/technical_indicators.py $VPS:$VPS_PATH/src/indicators/
scp -q src/main.py $VPS:$VPS_PATH/src/
scp -q src/web_server.py $VPS:$VPS_PATH/src/
scp -q src/api/routes/dashboard.py $VPS:$VPS_PATH/src/api/routes/
scp -q src/api/routes/market.py $VPS:$VPS_PATH/src/api/routes/
scp -q src/core/exchanges/manager.py $VPS:$VPS_PATH/src/core/exchanges/
scp -q config/config.yaml $VPS:$VPS_PATH/config/

echo "4. Installing dependencies on VPS..."
ssh $VPS << 'REMOTE'
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv/bin/activate

# Install Python packages
pip install -q pymemcache aiomemcache

# Check/install memcached
if ! command -v memcached &> /dev/null; then
    echo "   Installing memcached..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq memcached
    sudo systemctl start memcached
    sudo systemctl enable memcached
else
    echo "   Memcached already installed"
    sudo systemctl restart memcached
fi

echo "   Dependencies installed."
REMOTE

echo "5. Quick verification..."
ssh $VPS << 'VERIFY'
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv/bin/activate

python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from src.core.cache.unified_cache import UnifiedCache
    from src.core.cache.indicator_cache import IndicatorCache
    from src.core.cache.distributed_rate_limiter import DistributedRateLimiter
    from src.core.cache.session_manager import MemcachedSessionStore
    print('   ✓ All cache modules imported successfully')
except Exception as e:
    print(f'   ✗ Import error: {e}')
"
VERIFY

echo "6. Restarting services..."
ssh $VPS << 'RESTART'
# Try to restart services if they exist
sudo systemctl restart virtuoso 2>/dev/null || echo "   Virtuoso service not found"
sudo systemctl restart virtuoso-web 2>/dev/null || echo "   Web service not found"
RESTART

echo ""
echo "======================================"
echo "DEPLOYMENT COMPLETE!"
echo "======================================"
echo ""
echo "Cache optimizations deployed to VPS."
echo "Check status at: http://45.77.40.77:8003/api/cache/metrics"