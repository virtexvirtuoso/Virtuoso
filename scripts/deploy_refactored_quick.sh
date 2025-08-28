#!/bin/bash

# Quick deployment of refactored components to VPS

set -e

echo "🚀 Quick Deploy - Refactored Components"
echo "======================================="

VPS="linuxuser@45.77.40.77"
VPS_DIR="/home/linuxuser/trading/Virtuoso_ccxt"

# Create directories on VPS
echo "📁 Creating directories..."
ssh $VPS "mkdir -p ${VPS_DIR}/src/monitoring/components/alerts"

# Deploy files
echo "📤 Uploading refactored components..."

# Upload monitor_refactored.py
scp -q src/monitoring/monitor_refactored.py $VPS:${VPS_DIR}/src/monitoring/

# Upload alert components
scp -q src/monitoring/components/alerts/*.py $VPS:${VPS_DIR}/src/monitoring/components/alerts/

# Upload supporting components if they exist
for file in data_collector.py validator.py signal_processor.py metrics_tracker.py base.py; do
    if [ -f "src/monitoring/$file" ]; then
        scp -q src/monitoring/$file $VPS:${VPS_DIR}/src/monitoring/
    fi
done

echo "✅ Files uploaded"

# Quick test
echo "🧪 Testing components..."
ssh $VPS "cd ${VPS_DIR} && python3 -c 'import sys; sys.path.insert(0, \"src\"); from monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored; print(\"✅ AlertManager works\")'"

ssh $VPS "cd ${VPS_DIR} && python3 -c 'import sys; sys.path.insert(0, \"src\"); from monitoring.monitor_refactored import RefactoredMarketMonitor; print(\"✅ Monitor works\")'"

echo ""
echo "✅ Deployment successful!"
echo ""
echo "To test: ssh vps"
echo "Then: cd /home/linuxuser/trading/Virtuoso_ccxt"
echo "And: python3 -c 'from src.monitoring.components.alerts.alert_manager_refactored import AlertManagerRefactored'"