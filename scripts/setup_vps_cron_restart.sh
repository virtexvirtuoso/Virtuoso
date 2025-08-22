#!/bin/bash

# Setup automatic daily restart for Virtuoso service on VPS
# This prevents memory leaks and connection pool exhaustion

VPS_HOST="linuxuser@45.77.40.77"

echo "Setting up automatic daily restart on VPS..."

# Create restart script on VPS
ssh $VPS_HOST 'cat > /home/linuxuser/restart_virtuoso.sh << "EOF"
#!/bin/bash
# Virtuoso service restart script
# Runs daily at 3 AM SGT to prevent memory leaks

echo "$(date): Starting Virtuoso restart" >> /home/linuxuser/virtuoso_restart.log

# Stop the service
sudo systemctl stop virtuoso
sleep 5

# Clear cache and temp files
rm -f /tmp/virtuoso.lock
sudo journalctl --vacuum-time=7d  # Keep only 7 days of logs

# Start the service
sudo systemctl start virtuoso
sleep 10

# Check if service started successfully
if sudo systemctl is-active virtuoso > /dev/null; then
    echo "$(date): Virtuoso restarted successfully" >> /home/linuxuser/virtuoso_restart.log
else
    echo "$(date): ERROR - Virtuoso failed to start" >> /home/linuxuser/virtuoso_restart.log
    # Try once more
    sudo systemctl start virtuoso
fi
EOF'

# Make script executable
ssh $VPS_HOST 'chmod +x /home/linuxuser/restart_virtuoso.sh'

# Add to crontab (3 AM SGT daily)
ssh $VPS_HOST '(crontab -l 2>/dev/null | grep -v restart_virtuoso; echo "0 3 * * * /home/linuxuser/restart_virtuoso.sh") | crontab -'

# Verify cron job was added
echo ""
echo "Cron job added:"
ssh $VPS_HOST 'crontab -l | grep restart_virtuoso'

echo ""
echo "✅ Daily restart configured for 3:00 AM SGT"
echo "✅ Logs will be saved to: /home/linuxuser/virtuoso_restart.log"
echo ""
echo "To check restart history:"
echo "ssh $VPS_HOST 'tail /home/linuxuser/virtuoso_restart.log'"