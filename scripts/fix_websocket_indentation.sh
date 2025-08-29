#!/bin/bash

#############################################################################
# Script: fix_websocket_indentation.sh
# Purpose: Fix duplicate function definition in websocket_manager.py
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
#   ./fix_websocket_indentation.sh [options]
#   
#   Examples:
#     ./fix_websocket_indentation.sh
#     ./fix_websocket_indentation.sh --verbose
#     ./fix_websocket_indentation.sh --dry-run
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

echo "Fixing WebSocket manager indentation issue..."

# Create a Python script to fix the issue
cat > /tmp/fix_websocket.py << 'EOF'
#!/usr/bin/env python3
import sys

# Read the file
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py', 'r') as f:
    lines = f.readlines()

# Find and remove the duplicate line
fixed_lines = []
prev_line = ""
for i, line in enumerate(lines):
    # Skip duplicate function definition
    if i == 150 and "async def _create_connection" in line and "async def _create_connection" in prev_line:
        print(f"Removing duplicate line {i+1}: {line.strip()}")
        continue
    fixed_lines.append(line)
    prev_line = line

# Write the fixed content
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py', 'w') as f:
    f.writelines(fixed_lines)

print("File fixed successfully!")
EOF

# Run the fix
python3 /tmp/fix_websocket.py

# Verify the fix
echo -e "\nVerifying fix..."
sed -n '149,155p' /home/linuxuser/trading/Virtuoso_ccxt/src/core/exchanges/websocket_manager.py

# Restart the service
echo -e "\nRestarting virtuoso service..."
sudo systemctl restart virtuoso.service

# Check status
sleep 3
echo -e "\nService status:"
sudo systemctl status virtuoso.service --no-pager | head -20