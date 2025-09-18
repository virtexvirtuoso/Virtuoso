#!/bin/bash
# Deploy sentiment data flow fixes to VPS

VPS_HOST="linuxuser@5.223.63.4"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

echo "📊 Deploying Sentiment Data Flow Fixes to VPS..."
echo "==========================================="

# 1. Copy the fixed market_data_manager.py
echo "1. Copying fixed market_data_manager.py..."
scp src/core/market/market_data_manager.py $VPS_HOST:$VPS_DIR/src/core/market/

# 2. Copy the test script
echo "2. Copying test script..."
scp scripts/test_sentiment_data_flow.py $VPS_HOST:$VPS_DIR/scripts/

# 3. Restart the service
echo "3. Restarting Virtuoso trading service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso-trading.service"

# 4. Wait for service to start
echo "4. Waiting for service to stabilize..."
sleep 10

# 5. Check service status
echo "5. Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso-trading.service | head -20"

# 6. Test the sentiment data flow
echo ""
echo "6. Testing sentiment data flow on VPS..."
echo "==========================================="
ssh $VPS_HOST "cd $VPS_DIR && ./venv311/bin/python scripts/test_sentiment_data_flow.py 2>&1 | head -100"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To monitor logs in real-time:"
echo "  ssh vps 'sudo journalctl -u virtuoso-trading.service -f'"
echo ""
echo "To test sentiment data manually:"
echo "  curl http://5.223.63.4:8003/api/dashboard/data | jq '.sentiment'
"