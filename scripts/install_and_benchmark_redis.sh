#!/bin/bash

echo "============================================"
echo "🔧 INSTALLING REDIS & RUNNING BENCHMARK"
echo "============================================"
echo

# Copy benchmark script to VPS
echo "📤 Copying benchmark script to VPS..."
scp scripts/benchmark_redis_vs_memcached.py linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# Run installation and benchmark on VPS
ssh linuxuser@45.77.40.77 << 'EOF'
echo "📦 Checking Redis installation..."

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Installing Redis..."
    sudo apt-get update
    sudo apt-get install -y redis-server
    
    # Configure Redis for optimal performance
    sudo bash -c 'cat >> /etc/redis/redis.conf << EOL

# Performance optimizations for Virtuoso
maxmemory 256mb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 0
tcp-backlog 511
EOL'
    
    # Start Redis
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
else
    echo "✅ Redis already installed"
fi

# Check Redis status
if systemctl is-active --quiet redis-server; then
    echo "✅ Redis is running"
else
    echo "Starting Redis..."
    sudo systemctl start redis-server
fi

# Check Memcached status
if systemctl is-active --quiet memcached; then
    echo "✅ Memcached is running"
else
    echo "Starting Memcached..."
    sudo systemctl start memcached
fi

echo
echo "📊 Testing both cache systems..."
echo

# Install redis-py if needed
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
pip install redis > /dev/null 2>&1

# Quick connectivity test
echo "Testing connections..."
python3 -c "
import sys
try:
    from pymemcache.client.base import Client
    mc = Client(('127.0.0.1', 11211))
    mc.set(b'test', b'1')
    mc.delete(b'test')
    print('✅ Memcached connection: OK')
except Exception as e:
    print(f'❌ Memcached connection: {e}')

try:
    import redis
    r = redis.Redis(host='127.0.0.1', port=6379)
    r.ping()
    print('✅ Redis connection: OK')
except Exception as e:
    print(f'❌ Redis connection: {e}')
"

echo
echo "🏁 Running performance benchmark..."
echo "=" * 60

# Run the benchmark with smaller test size for faster results
python3 scripts/benchmark_redis_vs_memcached.py

echo
echo "📊 Getting system info..."
echo "Memcached stats:"
echo "stats" | nc localhost 11211 | head -5

echo
echo "Redis info:"
redis-cli INFO server | head -5

EOF

echo
echo "============================================"
echo "✅ BENCHMARK COMPLETE!"
echo "============================================"
echo
echo "Summary:"
echo "  • Both Redis and Memcached are now installed"
echo "  • Performance comparison complete"
echo "  • Check results above for recommendations"