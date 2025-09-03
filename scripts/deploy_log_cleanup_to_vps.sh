#!/bin/bash
#
# Deploy log cleanup automation to VPS
# This script sets up systemd timer and service for automatic log rotation
#

set -e

# Configuration
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_PROJECT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=========================================="
echo "Deploying Log Cleanup to VPS"
echo "=========================================="

# Step 1: Copy cleanup script to VPS
echo "📤 Copying cleanup script to VPS..."
scp scripts/utilities/clean_logs.py ${VPS_USER}@${VPS_HOST}:${VPS_PROJECT}/scripts/utilities/

# Step 2: Copy systemd files to VPS
echo "📤 Copying systemd configuration files..."
scp scripts/systemd/virtuoso-log-cleanup.timer ${VPS_USER}@${VPS_HOST}:/tmp/
scp scripts/systemd/virtuoso-log-cleanup.service ${VPS_USER}@${VPS_HOST}:/tmp/

# Step 3: Install and enable systemd services on VPS
echo "🔧 Installing systemd services on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
    # Move systemd files to proper location
    sudo mv /tmp/virtuoso-log-cleanup.timer /etc/systemd/system/
    sudo mv /tmp/virtuoso-log-cleanup.service /etc/systemd/system/
    
    # Set proper permissions
    sudo chmod 644 /etc/systemd/system/virtuoso-log-cleanup.*
    
    # Reload systemd daemon
    sudo systemctl daemon-reload
    
    # Enable and start the timer
    sudo systemctl enable virtuoso-log-cleanup.timer
    sudo systemctl start virtuoso-log-cleanup.timer
    
    # Show status
    echo ""
    echo "📊 Timer status:"
    sudo systemctl status virtuoso-log-cleanup.timer --no-pager
    
    echo ""
    echo "📅 Next scheduled runs:"
    sudo systemctl list-timers virtuoso-log-cleanup.timer --no-pager
    
    echo ""
    echo "✅ Log cleanup automation installed successfully!"
ENDSSH

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "Useful commands on VPS:"
echo "  Check timer status:     sudo systemctl status virtuoso-log-cleanup.timer"
echo "  Check service logs:     sudo journalctl -u virtuoso-log-cleanup.service"
echo "  Run cleanup manually:   sudo systemctl start virtuoso-log-cleanup.service"
echo "  View cleanup logs:      tail -f ${VPS_PROJECT}/logs/cleanup.log"
echo "  Disable timer:          sudo systemctl disable virtuoso-log-cleanup.timer"
echo ""

# Step 4: Run initial cleanup
read -p "Run initial log cleanup on VPS now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Running initial cleanup..."
    ssh ${VPS_USER}@${VPS_HOST} "cd ${VPS_PROJECT} && python3 scripts/utilities/clean_logs.py --execute --aggressive"
    echo "✅ Initial cleanup complete!"
fi

# Step 5: Create monitoring script
echo ""
echo "📊 Creating log monitoring script..."
cat > scripts/monitor_vps_logs.sh << 'EOF'
#!/bin/bash
# Monitor VPS log sizes
VPS_USER="linuxuser"
VPS_HOST="45.77.40.77"
VPS_LOGS="/home/linuxuser/trading/Virtuoso_ccxt/logs"

watch -n 60 "ssh ${VPS_USER}@${VPS_HOST} 'du -sh ${VPS_LOGS}/ && echo && du -sh ${VPS_LOGS}/* 2>/dev/null | sort -rh | head -10'"
EOF

chmod +x scripts/monitor_vps_logs.sh
echo "✅ Monitor script created: scripts/monitor_vps_logs.sh"