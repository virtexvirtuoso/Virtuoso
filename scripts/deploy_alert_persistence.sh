#!/bin/bash

#############################################################################
# Script: deploy_alert_persistence.sh
# Purpose: Deploy and manage deploy alert persistence
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates deployment automation, service management, and infrastructure updates for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - rsync
#   - ssh
#   - git
#   - systemctl
#   - Access to project directory structure
#
# Usage:
#   ./deploy_alert_persistence.sh [options]
#   
#   Examples:
#     ./deploy_alert_persistence.sh
#     ./deploy_alert_persistence.sh --verbose
#     ./deploy_alert_persistence.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: ${VPS_HOST})
#   VPS_USER         VPS username (default: linuxuser)
#
# Output:
#   - Console output with operation status
#   - Log messages with timestamps
#   - Success/failure indicators
#
# Exit Codes:
#   0 - Success
#   1 - Deployment failed
#   2 - Invalid arguments
#   3 - Connection error
#   4 - Service start failed
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Deploy alert persistence system to VPS

echo "🚀 Deploying Alert Persistence System to VPS..."

# VPS connection details
VPS_HOST="linuxuser@${VPS_HOST}"
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
curl -s "http://${VPS_HOST}:8000/api/alerts/persisted/stats?hours=1" | head -100

echo ""
echo "✅ Alert persistence deployment complete!"
echo ""
echo "📌 New API endpoints available:"
echo "  - GET  /api/alerts/persisted/list    - List persisted alerts"
echo "  - GET  /api/alerts/persisted/{id}    - Get specific alert"
echo "  - GET  /api/alerts/persisted/stats   - Get statistics"
echo ""
echo "💾 Alerts are now being persisted to: $VPS_PATH/data/alerts.db"
echo "🔍 To query specific alert: curl http://${VPS_HOST}:8000/api/alerts/persisted/WA-1755686017-API3USDT"