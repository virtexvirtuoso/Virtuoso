#!/bin/bash

# Deploy alert persistence system to VPS

echo "🚀 Deploying Alert Persistence System to VPS..."

# VPS connection details
VPS_HOST="linuxuser@45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Step 1: Copy new files to VPS
echo "📦 Copying alert persistence files..."
scp src/monitoring/alert_persistence.py $VPS_HOST:$VPS_PATH/src/monitoring/
scp src/monitoring/alert_manager.py $VPS_HOST:$VPS_PATH/src/monitoring/
scp src/api/routes/alerts.py $VPS_HOST:$VPS_PATH/src/api/routes/

# Step 2: Create data directory on VPS if it doesn't exist
echo "📁 Creating data directory on VPS..."
ssh $VPS_HOST "mkdir -p $VPS_PATH/data"

# Step 3: Test the persistence system
echo "🧪 Testing alert persistence..."
ssh $VPS_HOST "cd $VPS_PATH && python3 -c '
from src.monitoring.alert_persistence import AlertPersistence, Alert, AlertType, AlertStatus
import asyncio
import time

async def test():
    try:
        # Initialize persistence
        persistence = AlertPersistence(\"data/alerts.db\")
        print(\"✅ Alert persistence initialized\")
        
        # Create test alert
        test_alert = Alert(
            alert_id=\"TEST-\" + str(int(time.time())),
            alert_type=AlertType.SYSTEM.value,
            symbol=None,
            timestamp=time.time(),
            title=\"Test Alert\",
            message=\"Testing alert persistence system\",
            data={\"test\": True},
            status=AlertStatus.SENT.value
        )
        
        # Save alert
        success = await persistence.save_alert(test_alert)
        if success:
            print(\"✅ Test alert saved successfully\")
        else:
            print(\"❌ Failed to save test alert\")
            return False
        
        # Retrieve alert
        retrieved = await persistence.get_alert(test_alert.alert_id)
        if retrieved:
            print(f\"✅ Test alert retrieved: {retrieved.alert_id}\")
        else:
            print(\"❌ Failed to retrieve test alert\")
            return False
        
        # Get statistics
        stats = await persistence.get_alert_statistics()
        print(f\"✅ Statistics retrieved: Total alerts = {stats.get(\"total_alerts\", 0)}\")
        
        return True
    except Exception as e:
        print(f\"❌ Test failed: {e}\")
        return False

result = asyncio.run(test())
exit(0 if result else 1)
'"

if [ $? -eq 0 ]; then
    echo "✅ Alert persistence test passed"
else
    echo "❌ Alert persistence test failed"
    exit 1
fi

# Step 4: Restart the service
echo "🔄 Restarting Virtuoso service..."
ssh $VPS_HOST "sudo systemctl restart virtuoso.service"

# Step 5: Check service status
echo "📊 Checking service status..."
ssh $VPS_HOST "sudo systemctl status virtuoso.service | head -20"

# Step 6: Test API endpoints
echo "🌐 Testing API endpoints..."
sleep 5  # Wait for service to fully start

# Test persisted alerts endpoint
echo "Testing /api/alerts/persisted/stats endpoint..."
curl -s "http://45.77.40.77:8000/api/alerts/persisted/stats?hours=1" | head -100

echo ""
echo "✅ Alert persistence deployment complete!"
echo ""
echo "📌 New API endpoints available:"
echo "  - GET  /api/alerts/persisted/list    - List persisted alerts"
echo "  - GET  /api/alerts/persisted/{id}    - Get specific alert"
echo "  - GET  /api/alerts/persisted/stats   - Get statistics"
echo ""
echo "💾 Alerts are now being persisted to: $VPS_PATH/data/alerts.db"
echo "🔍 To query specific alert: curl http://45.77.40.77:8000/api/alerts/persisted/WA-1755686017-API3USDT"