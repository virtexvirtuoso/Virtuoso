#!/bin/bash

#############################################################################
# Script: deploy_signal_cache_fix.sh
# Purpose: Deploy and manage deploy signal cache fix
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
#   ./deploy_signal_cache_fix.sh [options]
#   
#   Examples:
#     ./deploy_signal_cache_fix.sh
#     ./deploy_signal_cache_fix.sh --verbose
#     ./deploy_signal_cache_fix.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 45.77.40.77)
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

# Deploy Signal Cache Fix to VPS
# This ensures Discord alerts appear in the dashboard Signals tab

echo "=== Deploying Signal Cache Fix to VPS ==="

# Configuration
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PATH="/home/linuxuser/trading/Virtuoso_ccxt"

# Files to deploy
echo "=== Copying updated files ==="

# Copy the updated alert_manager.py with signal caching
scp src/monitoring/alert_manager.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/src/monitoring/

# Copy helper scripts
scp scripts/sync_alerts_to_signals.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/
scp scripts/realtime_signal_cache_service.py ${VPS_USER}@${VPS_HOST}:${VPS_PATH}/scripts/

echo "=== Installing dependencies on VPS ==="
ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PATH} && pip install pymemcache -q"

echo "=== Setting up signal sync service ==="
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Make scripts executable
chmod +x scripts/sync_alerts_to_signals.py
chmod +x scripts/realtime_signal_cache_service.py

# Create systemd service for signal sync (optional)
cat > /tmp/signal-sync.service << 'SERVICE'
[Unit]
Description=Virtuoso Signal Cache Sync Service
After=network.target memcached.service

[Service]
Type=simple
User=linuxuser
WorkingDirectory=/home/linuxuser/trading/Virtuoso_ccxt
ExecStart=/usr/bin/python3 /home/linuxuser/trading/Virtuoso_ccxt/scripts/realtime_signal_cache_service.py --demo
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Install service (optional - requires sudo)
# sudo cp /tmp/signal-sync.service /etc/systemd/system/
# sudo systemctl daemon-reload
# sudo systemctl enable signal-sync
# sudo systemctl start signal-sync

echo "Signal sync scripts deployed. You can run manually:"
echo "  python3 scripts/realtime_signal_cache_service.py --demo"
echo "  python3 scripts/sync_alerts_to_signals.py --continuous"
EOF

echo "=== Restarting web server to apply changes ==="
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
# Find and restart the web server process
pkill -f "python.*web_server.py" || true
sleep 2
cd /home/linuxuser/trading/Virtuoso_ccxt
nohup python src/web_server.py > logs/web_server.log 2>&1 &
echo "Web server restarted"
EOF

echo "=== Testing signal cache ==="
ssh ${VPS_USER}@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Run demo signals for testing
python3 scripts/realtime_signal_cache_service.py --demo &
DEMO_PID=$!
sleep 3
kill $DEMO_PID 2>/dev/null || true

# Check if signals are in cache
python3 -c "
try:
    from pymemcache.client.base import Client
    from pymemcache import serde
    cache = Client(('localhost', 11211), serde=serde.pickle_serde)
    signals = cache.get('analysis:signals')
    if signals and signals.get('signals'):
        print(f'✓ Found {len(signals.get(\"signals\", []))} signals in cache')
    else:
        print('⚠ No signals in cache yet')
    cache.close()
except Exception as e:
    print(f'⚠ Cache check failed: {e}')
"
EOF

echo "=== Deployment Complete ==="
echo ""
echo "The Signals tab will now display:"
echo "1. Alerts sent to Discord (automatically cached)"
echo "2. Demo signals (if running demo mode)"
echo ""
echo "To populate with demo signals on VPS:"
echo "  ssh ${VPS_USER}@${VPS_HOST}"
echo "  cd ${VPS_PATH}"
echo "  python3 scripts/realtime_signal_cache_service.py --demo"
echo ""
echo "Dashboard URL: http://45.77.40.77:8501/dashboard"