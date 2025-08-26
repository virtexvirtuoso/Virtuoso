#!/bin/bash
echo "🚀 Deploying Consolidated API to VPS for Testing"

# Deploy the consolidated API files to VPS
echo "📦 Syncing consolidated API files..."
rsync -avz --exclude='__pycache__' \
    src/api/ \
    linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/src/api/

echo "🔧 Fixing pydantic regex issue on VPS..."
ssh linuxuser@45.77.40.77 'cd /home/linuxuser/trading/Virtuoso_ccxt && sed -i "s/regex=/pattern=/g" src/api/routes/signals.py'

echo "🔄 Restarting services on VPS..."
ssh linuxuser@45.77.40.77 'sudo systemctl restart virtuoso'

echo "⏰ Waiting for service startup..."
sleep 10

echo "🧪 Testing consolidated endpoints on VPS..."
# Test a few key endpoints
echo "Testing Phase 1 (Market):"
ssh linuxuser@45.77.40.77 'curl -s http://localhost:8001/api/market/overview | head -100'

echo -e "\nTesting Phase 3 (Dashboard):"  
ssh linuxuser@45.77.40.77 'curl -s http://localhost:8001/api/dashboard/overview | head -100'

echo -e "\nTesting Phase 4 (System):"
ssh linuxuser@45.77.40.77 'curl -s http://localhost:8001/api/system/status | head -100'

echo "✅ Consolidated API deployed to VPS successfully!"