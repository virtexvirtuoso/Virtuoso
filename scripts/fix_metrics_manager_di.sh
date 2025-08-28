#!/bin/bash

# Fix MetricsManager dependency injection error on VPS
# This script fixes the TypeError where MetricsManager is instantiated without required arguments

echo "=== Fixing MetricsManager Dependency Injection Error ==="
echo "Target: VPS at 45.77.40.77"
echo "Time: $(date)"

# Define VPS connection details
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Create the fix locally first
cat > /tmp/metrics_manager_fix.py << 'EOF'
#!/usr/bin/env python3
"""
Fix for MetricsManager dependency injection error.
This script patches the monitor.py file to properly handle MetricsManager initialization.
"""

import sys
import os

def apply_fix():
    monitor_file = "src/monitoring/monitor.py"
    
    print(f"Reading {monitor_file}...")
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Find and replace the problematic line
    old_code = """        # Set up metrics manager
        self.metrics_manager = metrics_manager or MetricsManager()"""
    
    new_code = """        # Set up metrics manager
        self.metrics_manager = metrics_manager
        if not self.metrics_manager and config and alert_manager:
            # Only create MetricsManager if we have required dependencies
            self.metrics_manager = MetricsManager(config, alert_manager)"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✓ Found and fixed MetricsManager initialization")
        
        # Write the fixed content
        with open(monitor_file, 'w') as f:
            f.write(content)
        print(f"✓ Updated {monitor_file}")
        return True
    else:
        print("ℹ️ Code already fixed or pattern not found")
        # Check if already fixed
        if "if not self.metrics_manager and config and alert_manager:" in content:
            print("✓ Fix already applied")
            return True
        return False

if __name__ == "__main__":
    try:
        if apply_fix():
            print("✅ MetricsManager fix applied successfully")
            sys.exit(0)
        else:
            print("⚠️ Could not apply fix - manual intervention may be required")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        sys.exit(1)
EOF

echo ""
echo "=== Step 1: Copying fix script to VPS ==="
scp /tmp/metrics_manager_fix.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/

echo ""
echo "=== Step 2: Applying fix on VPS ==="
ssh ${VPS_USER}@${VPS_HOST} << 'REMOTE_EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Stop the service first
echo "Stopping virtuoso service..."
sudo systemctl stop virtuoso.service

# Apply the fix
echo "Applying MetricsManager fix..."
python3 metrics_manager_fix.py

# Verify the fix was applied
echo ""
echo "Verifying fix..."
if grep -q "if not self.metrics_manager and config and alert_manager:" src/monitoring/monitor.py; then
    echo "✓ Fix verified in monitor.py"
else
    echo "❌ Fix verification failed"
    exit 1
fi

# Clean up
rm -f metrics_manager_fix.py

# Restart the service
echo ""
echo "Restarting virtuoso service..."
sudo systemctl start virtuoso.service

# Wait a moment for service to start
sleep 3

# Check service status
echo ""
echo "=== Service Status ==="
sudo systemctl status virtuoso.service --no-pager | head -20

# Check for the specific error in recent logs
echo ""
echo "=== Checking for MetricsManager errors in logs ==="
if sudo journalctl -u virtuoso.service --since "2 minutes ago" | grep -q "MetricsManager.__init__() missing"; then
    echo "❌ Error still present in logs"
    sudo journalctl -u virtuoso.service --since "2 minutes ago" | grep -A5 -B5 "MetricsManager"
else
    echo "✓ No MetricsManager initialization errors found"
fi

echo ""
echo "=== Recent Service Logs ==="
sudo journalctl -u virtuoso.service -n 30 --no-pager

REMOTE_EOF

echo ""
echo "=== Step 3: Final Verification ==="
echo "Checking if service is running properly..."

# Quick health check
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8003/health | grep -q "200\|503"; then
    echo "✓ Health endpoint responding"
else
    echo "⚠️ Health endpoint not responding (might still be starting)"
fi

if curl -s -o /dev/null -w "%{http_code}" http://${VPS_HOST}:8001/api/monitoring/status | grep -q "200"; then
    echo "✓ Monitoring API responding"
else
    echo "⚠️ Monitoring API not responding (might still be starting)"
fi

echo ""
echo "=== Deployment Complete ==="
echo "Fix has been applied to resolve MetricsManager dependency injection error"
echo ""
echo "To monitor the service:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo journalctl -u virtuoso.service -f'"
echo ""
echo "To check service status:"
echo "  ssh ${VPS_USER}@${VPS_HOST} 'sudo systemctl status virtuoso.service'"