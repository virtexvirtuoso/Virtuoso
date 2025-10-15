#!/bin/bash
"""
Setup Monitoring API Reliability Infrastructure
===============================================

This script sets up all the reliability improvements for the monitoring API:
1. Deploys reliability scripts
2. Sets up systemd service
3. Configures automated health checks
4. Creates cron jobs for monitoring
"""

set -e

PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
LOGS_DIR="$PROJECT_ROOT/logs"

echo "Setting up Monitoring API Reliability Infrastructure..."

# Create necessary directories
mkdir -p "$LOGS_DIR"
mkdir -p "$SCRIPTS_DIR/systemd"

# Make scripts executable
chmod +x "$SCRIPTS_DIR/monitoring_reliability_fixes.py"
chmod +x "$SCRIPTS_DIR/monitoring_health_check.py"
chmod +x "$SCRIPTS_DIR/setup_monitoring_reliability.sh"

echo "✅ Made scripts executable"

# Copy systemd service file to system location
sudo cp "$SCRIPTS_DIR/systemd/virtuoso-monitoring-api.service" /etc/systemd/system/
sudo systemctl daemon-reload

echo "✅ Installed systemd service"

# Enable and start the service (optional - can be done manually)
read -p "Enable monitoring API systemd service? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable virtuoso-monitoring-api.service
    echo "✅ Enabled systemd service"
fi

# Set up cron jobs for health monitoring
CRON_FILE="/tmp/monitoring_cron_$$"

# Create cron job for health check (every 5 minutes)
cat > "$CRON_FILE" << EOF
# Monitoring API Health Check (every 5 minutes)
*/5 * * * * cd $PROJECT_ROOT && $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_health_check.py --once >> $LOGS_DIR/cron_health.log 2>&1

# Daily restart for maintenance (3:15 AM)
15 3 * * * cd $PROJECT_ROOT && $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_reliability_fixes.py restart >> $LOGS_DIR/cron_restart.log 2>&1

# Weekly cleanup of old processes (Sunday 2:00 AM)
0 2 * * 0 cd $PROJECT_ROOT && $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_reliability_fixes.py fix >> $LOGS_DIR/cron_cleanup.log 2>&1
EOF

# Install cron jobs
crontab -l 2>/dev/null | grep -v "monitoring_health_check\|monitoring_reliability_fixes" > "$CRON_FILE.tmp" || true
cat "$CRON_FILE" >> "$CRON_FILE.tmp"
crontab "$CRON_FILE.tmp"
rm -f "$CRON_FILE" "$CRON_FILE.tmp"

echo "✅ Installed cron jobs for automated monitoring"

# Create log rotation configuration
sudo tee /etc/logrotate.d/virtuoso-monitoring > /dev/null << EOF
$LOGS_DIR/monitoring_*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 linuxuser linuxuser
}
EOF

echo "✅ Configured log rotation"

# Create monitoring status script
cat > "$SCRIPTS_DIR/monitoring_status.sh" << 'EOF'
#!/bin/bash
# Quick monitoring status check

PROJECT_ROOT="/home/linuxuser/trading/Virtuoso_ccxt"

echo "=== Monitoring API Status ==="
echo

# Check process
if pgrep -f "monitoring_api.py" > /dev/null; then
    PID=$(pgrep -f "monitoring_api.py")
    echo "✅ Process running (PID: $PID)"
else
    echo "❌ Process not running"
fi

# Check health endpoint
for port in 8001 8003 8004 8005; do
    if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ Health check passed on port $port"
        break
    fi
done

# Check systemd service
if systemctl is-active --quiet virtuoso-monitoring-api.service; then
    echo "✅ Systemd service active"
else
    echo "⚠️  Systemd service not active"
fi

# Check cron jobs
if crontab -l | grep -q "monitoring_health_check"; then
    echo "✅ Cron health checks configured"
else
    echo "⚠️  Cron health checks not configured"
fi

# Show recent logs
echo
echo "=== Recent Logs ==="
tail -n 5 "$PROJECT_ROOT/logs/monitoring_api.log" 2>/dev/null || echo "No recent logs"
EOF

chmod +x "$SCRIPTS_DIR/monitoring_status.sh"

echo "✅ Created monitoring status script"

# Test the reliability script
echo
echo "Testing reliability script..."
if "$PROJECT_ROOT/venv311/bin/python" "$SCRIPTS_DIR/monitoring_reliability_fixes.py" health; then
    echo "✅ Reliability script test passed"
else
    echo "⚠️  Reliability script test failed"
fi

echo
echo "=== Setup Complete ==="
echo
echo "Available commands:"
echo "  - Check status: $SCRIPTS_DIR/monitoring_status.sh"
echo "  - Manual restart: $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_reliability_fixes.py restart"
echo "  - Health check: $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_health_check.py --once"
echo "  - Emergency fix: $PROJECT_ROOT/venv311/bin/python $SCRIPTS_DIR/monitoring_reliability_fixes.py fix"
echo
echo "Systemd commands:"
echo "  - Start service: sudo systemctl start virtuoso-monitoring-api.service"
echo "  - Check status: sudo systemctl status virtuoso-monitoring-api.service"
echo "  - View logs: sudo journalctl -u virtuoso-monitoring-api.service -f"
echo
echo "✅ Monitoring API reliability infrastructure is now set up!"