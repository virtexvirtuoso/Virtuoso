#!/bin/bash

echo "🚀 Deploying stable service configuration to VPS..."

# Stop the service and clean up
echo "1. Stopping service and cleaning up..."
ssh linuxuser@45.77.40.77 << 'ENDSSH'
    sudo systemctl stop virtuoso.service
    sudo pkill -9 -f "python.*main.py" || true
    sleep 2
    
    # Clear any stuck ports
    sudo lsof -ti:8001 | xargs -r sudo kill -9 || true
    sudo lsof -ti:8004 | xargs -r sudo kill -9 || true
    
    # Reset systemd failure state
    sudo systemctl reset-failed virtuoso.service
    
    echo "Service stopped and cleaned up"
ENDSSH

# Deploy the latest code
echo "2. Syncing code to VPS..."
rsync -avz --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='venv311' \
    --exclude='logs' \
    --exclude='exports' \
    --exclude='backups' \
    --exclude='reports' \
    --exclude='*.log' \
    src/ scripts/ config/ \
    linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/

# Start the service
echo "3. Starting virtuoso service..."
ssh linuxuser@45.77.40.77 << 'ENDSSH'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Ensure memcached is running
    sudo systemctl start memcached || true
    
    # Start the service
    sudo systemctl start virtuoso.service
    
    # Wait for initialization
    sleep 10
    
    # Check status
    sudo systemctl status virtuoso.service | head -15
ENDSSH

echo "4. Testing API endpoints..."
sleep 5

# Test the API
echo "Testing confluence scores endpoint..."
curl -s -m 5 "http://45.77.40.77:8004/api/dashboard/confluence/scores" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data:
        print('✅ API is responding with data')
        print(f'  Found {len(data)} symbols')
    else:
        print('⚠️ API responded but no data')
except:
    print('❌ API not responding or invalid JSON')
" || echo "❌ API request failed"

echo ""
echo "Deployment complete. Checking final status..."
ssh linuxuser@45.77.40.77 "sudo systemctl is-active virtuoso.service"