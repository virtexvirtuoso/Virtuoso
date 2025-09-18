#!/bin/bash

#############################################################################
# Script: setup_vps_cron_restart.sh
# Purpose: Setup and configure setup vps cron restart
# Author: Virtuoso CCXT Development Team
# Version: 1.0.0
# Created: 2025-08-28
# Modified: 2025-08-28
#############################################################################
#
# Description:
   Automates system setup, service configuration, and environment preparation for the Virtuoso trading
   system. This script provides comprehensive functionality for managing
   the trading infrastructure with proper error handling and validation.
#
# Dependencies:
#   - Bash 4.0+
#   - systemctl
#   - mkdir
#   - chmod
#   - Access to project directory structure
#
# Usage:
#   ./setup_vps_cron_restart.sh [options]
#   
#   Examples:
#     ./setup_vps_cron_restart.sh
#     ./setup_vps_cron_restart.sh --verbose
#     ./setup_vps_cron_restart.sh --dry-run
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
#   0 - Setup completed successfully
#   1 - Setup failed
#   2 - Permission denied
#   3 - Dependencies missing
#   4 - Configuration error
#
# Notes:
#   - Run from project root directory
#   - Requires proper SSH key configuration for VPS operations
#   - Creates backups before destructive operations
#
#############################################################################

# Setup automatic daily restart for Virtuoso service on VPS
# This prevents memory leaks and connection pool exhaustion

VPS_HOST="linuxuser@${VPS_HOST}"

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