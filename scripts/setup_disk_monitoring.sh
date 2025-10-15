#!/bin/bash
# Setup Disk Space Monitoring for Virtuoso Trading System

set -e

echo "Setting up disk space monitoring..."

# Create log file
sudo mkdir -p /var/log
sudo touch /var/log/disk_monitor.log
sudo chown linuxuser:linuxuser /var/log/disk_monitor.log

# Copy monitoring script to VPS
echo "Deploying disk monitoring script..."
scp scripts/disk_space_monitor.py vps:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# Make script executable on VPS
ssh vps "chmod +x /home/linuxuser/trading/Virtuoso_ccxt/scripts/disk_space_monitor.py"

# Test the monitoring script
echo "Testing monitoring script..."
ssh vps "cd /home/linuxuser/trading/Virtuoso_ccxt && python3 scripts/disk_space_monitor.py"

# Setup cron job (run every 15 minutes)
echo "Setting up cron job..."
ssh vps "
# Remove any existing disk monitor cron jobs
crontab -l 2>/dev/null | grep -v 'disk_space_monitor' | crontab -

# Add new cron job
(crontab -l 2>/dev/null; echo '*/15 * * * * cd /home/linuxuser/trading/Virtuoso_ccxt && python3 scripts/disk_space_monitor.py') | crontab -

echo 'Current crontab:'
crontab -l
"

# Create emergency cleanup script
cat > scripts/emergency_cleanup.sh << 'EOF'
#!/bin/bash
# Emergency disk cleanup script

echo "=== EMERGENCY DISK CLEANUP ==="
echo "Current disk usage:"
df -h /

echo "Removing large backup directories..."
find /home/linuxuser/trading -name "*backup*" -type d -size +1G -mtime +7 -exec rm -rf {} + 2>/dev/null || true

echo "Removing old backup files..."
find /home/linuxuser/trading -name "*backup*.tar.gz" -size +500M -mtime +7 -delete 2>/dev/null || true

echo "Cleaning Docker..."
docker system prune -f 2>/dev/null || true

echo "Cleaning package cache..."
sudo apt-get clean 2>/dev/null || true

echo "After cleanup:"
df -h /

echo "=== CLEANUP COMPLETE ==="
EOF

chmod +x scripts/emergency_cleanup.sh

# Deploy emergency cleanup script
scp scripts/emergency_cleanup.sh vps:/home/linuxuser/trading/Virtuoso_ccxt/scripts/
ssh vps "chmod +x /home/linuxuser/trading/Virtuoso_ccxt/scripts/emergency_cleanup.sh"

echo "✅ Disk monitoring setup complete!"
echo ""
echo "Monitoring features deployed:"
echo "  ✓ Automated disk space monitoring (every 15 minutes)"
echo "  ✓ Automatic cleanup of old backups (>14 days)"
echo "  ✓ Alert system for disk usage thresholds:"
echo "    - Warning: 80%"
echo "    - Critical: 85%"
echo "    - Cleanup: 90%"
echo "  ✓ Emergency cleanup script available"
echo ""
echo "Monitor logs: ssh vps 'tail -f /var/log/disk_monitor.log'"
echo "Manual cleanup: ssh vps '/home/linuxuser/trading/Virtuoso_ccxt/scripts/emergency_cleanup.sh'"