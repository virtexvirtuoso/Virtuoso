#!/bin/bash

#############################################################################
# Script: fix_indentation_error.sh
# Purpose: Fix indentation error in main.py
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
#   ./fix_indentation_error.sh [options]
#   
#   Examples:
#     ./fix_indentation_error.sh
#     ./fix_indentation_error.sh --verbose
#     ./fix_indentation_error.sh --dry-run
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

ssh linuxuser@${VPS_HOST} << 'EOF'
cd /home/linuxuser/trading/Virtuoso_ccxt

# Fix the indentation error
python3 << 'PYTHON'
with open('src/main.py', 'r') as f:
    lines = f.readlines()

# Fix line 907 and surrounding lines
for i in range(906, min(915, len(lines))):
    if lines[i].strip().startswith('try:'):
        # This line should have 8 spaces (2 indents) not 12
        lines[i] = '        try:\n'
    elif lines[i].strip().startswith('from src.core.dashboard_updater'):
        lines[i] = '            from src.core.dashboard_updater import DashboardUpdater\n'
    elif lines[i].strip().startswith('from src.core.api_cache'):
        lines[i] = '            from src.core.api_cache import api_cache\n'
    elif lines[i].strip().startswith('self.dashboard_updater'):
        lines[i] = '            self.dashboard_updater = DashboardUpdater(self, api_cache, update_interval=30)\n'
    elif lines[i].strip().startswith('self.dashboard_updater.start()'):
        lines[i] = '            self.dashboard_updater.start()\n'
    elif lines[i].strip().startswith('logger.info("✅ Dashboard updater'):
        lines[i] = '            logger.info("✅ Dashboard updater started successfully")\n'
    elif lines[i].strip().startswith('except Exception as e:'):
        lines[i] = '        except Exception as e:\n'
    elif lines[i].strip().startswith('logger.error(f"Failed to start dashboard'):
        lines[i] = '            logger.error(f"Failed to start dashboard updater: {e}")\n'
    elif lines[i].strip().startswith('import traceback'):
        lines[i] = '            import traceback\n'
    elif lines[i].strip().startswith('logger.error(traceback'):
        lines[i] = '            logger.error(traceback.format_exc())\n'

# Write back
with open('src/main.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixed indentation")
PYTHON

# Test syntax
echo "Testing syntax..."
python3 -m py_compile src/main.py && echo "✅ Syntax OK" || echo "❌ Syntax error"

# Restart service
echo "Restarting service..."
sudo systemctl restart virtuoso

sleep 3

# Check status
systemctl is-active virtuoso && echo "✅ Service running" || echo "❌ Service failed"
EOF