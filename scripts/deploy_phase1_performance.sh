#!/bin/bash
# Deploy Phase 1 Performance Optimizations

echo "🚀 Deploying Phase 1 Performance Optimizations"
echo "=============================================="

# Deploy pooled cache adapter
echo "📦 Deploying connection pooling..."
scp src/core/cache_adapter_pooled.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/core/

# Deploy parallel dashboard routes
echo "📦 Deploying parallel processing routes..."
scp src/api/routes/dashboard_parallel.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Update dashboard.py to use pooled adapter
echo "🔧 Updating dashboard to use pooled adapter..."
ssh linuxuser@45.77.40.77 'cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i "s/from src.api.cache_adapter_direct/from src.core.cache_adapter_pooled/g" src/api/routes/dashboard.py'

# Restart service
echo "🔄 Restarting service..."
ssh linuxuser@45.77.40.77 'sudo systemctl restart virtuoso.service'

# Wait for startup
echo "⏳ Waiting for service to start..."
sleep 15

# Test performance
echo ""
echo "📊 Testing Performance Improvements:"
echo "===================================="

for i in {1..3}; do
    echo ""
    echo "Test Run $i:"
    echo -n "  Mobile: "
    time=$(curl -w "%{time_total}" -o /dev/null -s http://45.77.40.77:8003/api/dashboard/mobile 2>/dev/null)
    echo "${time}s"
    
    echo -n "  Alerts: "
    time=$(curl -w "%{time_total}" -o /dev/null -s http://45.77.40.77:8003/api/dashboard/alerts 2>/dev/null)
    echo "${time}s"
    
    sleep 1
done

echo ""
echo "✅ Phase 1 deployment complete!"
echo "Monitor: ssh linuxuser@45.77.40.77 'sudo journalctl -u virtuoso.service -f'"