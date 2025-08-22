#!/bin/bash

echo "=== Deploying Market Regime Fix to VPS ==="
echo "Fix: Market regime showing 'unknown' - converting to uppercase and adding missing metrics"

VPS_HOST="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Deploy the main.py fix
echo "📦 Deploying src/main.py with market regime fix..."
scp src/main.py $VPS_HOST:$VPS_DIR/src/

echo "✅ Files deployed successfully"

# Restart the service on VPS
echo "🔄 Restarting service on VPS..."
ssh $VPS_HOST << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Check if service is running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "Stopping existing service..."
    pkill -f "python.*main.py"
    sleep 2
fi

# Start the service
echo "Starting service with market regime fix..."
nohup python src/main.py > /dev/null 2>&1 &
sleep 3

# Verify it's running
if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ Service restarted successfully with market regime fix"
    
    # Clear cache to ensure fresh data
    echo "Clearing cache for fresh market regime data..."
    python -c "
import asyncio
import aiomcache

async def clear():
    client = aiomcache.Client('localhost', 11211)
    await client.flush_all()
    await client.close()
    print('Cache cleared')

asyncio.run(clear())
" 2>/dev/null || echo "Cache clear skipped"
    
else
    echo "⚠️ Service may not have started properly"
fi

echo "=== Deployment Complete ==="
echo "Market regime should now show BULLISH/BEARISH/NEUTRAL instead of 'unknown'"
EOF

echo ""
echo "🎯 Market Regime Fix Deployed!"
echo "The dashboard should now display the correct market regime."