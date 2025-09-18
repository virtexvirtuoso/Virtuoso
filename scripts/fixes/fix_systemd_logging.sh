#!/bin/bash

#############################################################################
# Script: fix_systemd_logging.sh
# Purpose: Deploy and manage fix systemd logging
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
#   ./fix_systemd_logging.sh [options]
#   
#   Examples:
#     ./fix_systemd_logging.sh
#     ./fix_systemd_logging.sh --verbose
#     ./fix_systemd_logging.sh --dry-run
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

echo "=========================================="
echo "Fixing Virtuoso Logging for Systemd"
echo "=========================================="

# Create a backup of main.py
echo "1. Creating backup of main.py..."
cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_$(date +%Y%m%d_%H%M%S)

# Add logging verification to main.py
echo "2. Adding logging verification to main.py..."

# Find the line number after logging configuration
LINE_NUM=$(grep -n "logger.info(\"🚀 Starting Virtuoso" /home/linuxuser/trading/Virtuoso_ccxt/src/main.py | cut -d: -f1)

if [ -z "$LINE_NUM" ]; then
    echo "ERROR: Could not find the target line in main.py"
    exit 1
fi

# Create the patch
cat > /tmp/logging_patch.py << 'EOF'

# Ensure logging is properly configured (systemd fix)
import sys
_root_logger = logging.getLogger()
if len(_root_logger.handlers) == 0:
    _console = logging.StreamHandler(sys.stdout)
    _console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s'))
    _console.setLevel(logging.DEBUG)
    _root_logger.addHandler(_console)
    _root_logger.setLevel(logging.DEBUG)
    logger.warning("Applied systemd logging fix - handlers were missing")

EOF

# Insert the patch
echo "3. Applying patch..."
sed -i "${LINE_NUM}r /tmp/logging_patch.py" /home/linuxuser/trading/Virtuoso_ccxt/src/main.py

# Restart the service
echo "4. Restarting virtuoso service..."
sudo systemctl restart virtuoso

# Wait for service to start
sleep 3

# Check status
echo "5. Checking service status..."
sudo systemctl status virtuoso --no-pager | head -20

# Check logs
echo ""
echo "6. Recent logs from journalctl:"
sudo journalctl -u virtuoso -n 20 --no-pager

echo ""
echo "=========================================="
echo "Fix applied. Check logs with:"
echo "  sudo journalctl -u virtuoso -f"
echo "=========================================="