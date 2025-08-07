#!/bin/bash

echo "Deploying confluence fix..."

# Copy the fixed file
scp src/api/routes/dashboard.py vps:/home/linuxuser/trading/Virtuoso_ccxt/src/api/routes/

# Quick test on VPS
ssh vps << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt
echo "Restarting web server..."
sudo systemctl restart virtuoso-web
sleep 2
echo "Testing symbols endpoint..."
curl -s http://localhost:8001/api/dashboard/symbols | head -c 200
echo
EOF

echo "Done!"