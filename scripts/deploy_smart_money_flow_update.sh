#!/bin/bash

echo "==================================="
echo "🚀 Deploying Smart Money Flow Weight Update"
echo "==================================="
echo ""
echo "Changes:"
echo "- smart_money_flow weight: 20% → 15%"
echo "- Redistributed 5% across other components:"
echo "  - cvd: 20% → 22% (+2%)"
echo "  - trade_flow: 15% → 17% (+2%)"  
echo "  - imbalance: 12% → 13% (+1%)"
echo ""

# Save current directory
CURRENT_DIR=$(pwd)

# Deploy to VPS
echo "📦 Deploying to VPS..."
rsync -avz --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='venv311' \
    --exclude='logs' \
    --exclude='exports' \
    --exclude='backups' \
    --exclude='reports' \
    --exclude='*.log' \
    src/indicators/orderflow_indicators.py \
    config/config.yaml \
    linuxuser@45.77.40.77:/home/linuxuser/trading/Virtuoso_ccxt/

if [ $? -eq 0 ]; then
    echo "✅ Files deployed successfully"
    
    # Restart service on VPS
    echo ""
    echo "🔄 Restarting service on VPS..."
    ssh linuxuser@45.77.40.77 << 'REMOTE_EOF'
    cd /home/linuxuser/trading/Virtuoso_ccxt
    
    # Kill existing processes
    echo "Stopping existing processes..."
    pkill -f "python.*main.py" || true
    pkill -f "python.*web_server.py" || true
    sleep 2
    
    # Start services
    echo "Starting services..."
    screen -dmS virtuoso bash -c 'cd /home/linuxuser/trading/Virtuoso_ccxt && python src/main.py 2>&1 | tee -a logs/main.log'
    screen -dmS webserver bash -c 'cd /home/linuxuser/trading/Virtuoso_ccxt && python src/web_server.py 2>&1 | tee -a logs/webserver.log'
    
    sleep 5
    
    # Verify services are running
    echo ""
    echo "Service status:"
    pgrep -f "python.*main.py" > /dev/null && echo "✅ Main service running" || echo "❌ Main service not running"
    pgrep -f "python.*web_server.py" > /dev/null && echo "✅ Web server running" || echo "❌ Web server not running"
    
    # Check logs for weight update
    echo ""
    echo "Checking for weight configuration..."
    tail -n 100 logs/main.log | grep -i "smart_money_flow" | tail -3
REMOTE_EOF
    
    echo ""
    echo "✅ Smart Money Flow weight update deployed successfully!"
    echo ""
    echo "New weight distribution:"
    echo "  cvd: 22%"
    echo "  trade_flow: 17%"
    echo "  imbalance: 13%"
    echo "  open_interest: 15%"
    echo "  pressure: 8%"
    echo "  liquidity: 10%"
    echo "  smart_money_flow: 15%"
    echo ""
    echo "Total: 100%"
else
    echo "❌ Deployment failed"
    exit 1
fi
