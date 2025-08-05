#!/bin/bash
# Simple patch to increase timeouts in bybit.py

ssh linuxuser@45.77.40.77 << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Backup current file
cp src/core/exchanges/bybit.py src/core/exchanges/bybit.py.broken

# Use the original file
cp src/core/exchanges/bybit_original.py src/core/exchanges/bybit.py

# Update main timeout from 30 to 60 seconds
sed -i 's/total=30,  # Total timeout/total=60,  # Total timeout (increased for high latency)/' src/core/exchanges/bybit.py

# Update connection timeout from 10 to 20 seconds  
sed -i 's/connect=10,  # Connection timeout/connect=20,  # Connection timeout (increased from 10s)/' src/core/exchanges/bybit.py

# Update socket read timeout from 20 to 30 seconds
sed -i 's/sock_read=20  # Socket read timeout/sock_read=30  # Socket read timeout (increased from 20s)/' src/core/exchanges/bybit.py

# Reduce connection limit from 40 to 30
sed -i 's/limit_per_host=40,/limit_per_host=30,  # Reduced to prevent exhaustion/' src/core/exchanges/bybit.py

echo "Applied simple timeout optimizations to bybit.py"
EOF