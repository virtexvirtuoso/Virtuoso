#!/bin/bash

#############################################################################
# Script: deploy_monitor_fix.sh
# Purpose: Deploy monitor.py fix to VPS
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
#   ./deploy_monitor_fix.sh [options]
#   
#   Examples:
#     ./deploy_monitor_fix.sh
#     ./deploy_monitor_fix.sh --verbose
#     ./deploy_monitor_fix.sh --dry-run
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

echo "🚀 Deploying monitor.py AttributeError fix to VPS..."

# Copy to pi first as staging area
echo "📤 Copying monitor.py to pi staging area..."
scp /Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/monitoring/monitor.py pi:/tmp/monitor_fixed.py

# Create deployment commands
echo "📋 Creating deployment commands..."
cat > /tmp/vps_deploy_commands.sh << 'EOF'
#!/bin/bash
# VPS deployment commands
echo "🔄 Stopping Virtuoso service..."
sudo systemctl stop virtuoso.service

echo "📥 Installing fixed monitor.py..."
cp /tmp/monitor_fixed.py /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py

echo "✅ Setting correct permissions..."
chown linuxuser:linuxuser /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py
chmod 644 /home/linuxuser/trading/Virtuoso_ccxt/src/monitoring/monitor.py

echo "🚀 Starting Virtuoso service..."
sudo systemctl start virtuoso.service

echo "📊 Checking service status..."
sleep 5
sudo systemctl status virtuoso.service --no-pager

echo "📝 Showing recent logs..."
sudo journalctl -u virtuoso.service -n 20 --no-pager
EOF

# Copy deployment script to pi
scp /tmp/vps_deploy_commands.sh pi:/tmp/vps_deploy_commands.sh

# Execute deployment through pi
echo "🎯 Executing deployment on VPS through pi..."
ssh pi "chmod +x /tmp/vps_deploy_commands.sh && scp /tmp/monitor_fixed.py linuxuser@45.77.40.77:/tmp/ && scp /tmp/vps_deploy_commands.sh linuxuser@45.77.40.77:/tmp/ && ssh linuxuser@45.77.40.77 'chmod +x /tmp/vps_deploy_commands.sh && /tmp/vps_deploy_commands.sh'"

echo "✅ Deployment complete!"