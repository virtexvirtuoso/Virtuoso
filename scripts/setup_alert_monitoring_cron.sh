#!/bin/bash

# Setup cron job for alert health monitoring
echo "Setting up automated alert health monitoring..."

# Create the cron script
cat > /tmp/alert_monitor_cron.sh << 'EOF'
#!/bin/bash
cd /home/linuxuser/trading/Virtuoso_ccxt
source venv311/bin/activate
python scripts/monitor_alert_health.py >> logs/alert_health.log 2>&1
EOF

# Copy to VPS
scp /tmp/alert_monitor_cron.sh vps:/home/linuxuser/trading/Virtuoso_ccxt/scripts/

# Make it executable and add to crontab
ssh vps << 'REMOTE_COMMANDS'
chmod +x /home/linuxuser/trading/Virtuoso_ccxt/scripts/alert_monitor_cron.sh

# Add cron job to run every hour
(crontab -l 2>/dev/null; echo "0 * * * * /home/linuxuser/trading/Virtuoso_ccxt/scripts/alert_monitor_cron.sh") | crontab -

# Create log file if it doesn't exist
touch /home/linuxuser/trading/Virtuoso_ccxt/logs/alert_health.log

echo "✅ Cron job added to run alert health monitoring every hour"
crontab -l | grep alert_monitor_cron
REMOTE_COMMANDS

echo "✅ Alert health monitoring automation setup complete!"