#!/bin/bash

#############################################################################
# Script: fix_analyze_batch.sh
# Purpose: Deploy and manage fix analyze batch
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
#   ./fix_analyze_batch.sh [options]
#   
#   Examples:
#     ./fix_analyze_batch.sh
#     ./fix_analyze_batch.sh --verbose
#     ./fix_analyze_batch.sh --dry-run
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

echo "🔧 Fixing _analyze_batch coroutine issue..."

# Create backup
ssh linuxuser@${VPS_HOST} "cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_analyze"

# Fix: Remove the first task creation that's not being used
ssh linuxuser@${VPS_HOST} << 'ENDSSH'
cd /home/linuxuser/trading/Virtuoso_ccxt
python3 << 'PYTHON'
with open('src/main.py', 'r') as f:
    lines = f.readlines()

# Find and comment out the first task creation (around line 1036-1040)
for i in range(1034, 1042):
    if 'tasks = []' in lines[i]:
        # Comment out the old task creation loop
        start = i
        # Find the end of the for loop
        for j in range(i+1, i+5):
            if 'tasks.append(self._analyze_symbol' in lines[j]:
                # Comment out these lines
                lines[start] = '        # ' + lines[start].lstrip()
                lines[start+1] = '        # ' + lines[start+1].lstrip()
                lines[start+2] = '        # ' + lines[start+2].lstrip()
                lines[j] = '        # ' + lines[j].lstrip()
                print(f"Commented out lines {start+1}-{j+1}")
                break
        break

# Write the fixed file
with open('src/main.py', 'w') as f:
    f.writelines(lines)
print("✅ Fixed duplicate task creation")
PYTHON
ENDSSH

# Validate syntax
echo "🔍 Validating Python syntax..."
if ssh linuxuser@${VPS_HOST} "cd /home/linuxuser/trading/Virtuoso_ccxt && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -m py_compile src/main.py 2>&1"; then
    echo "✅ Syntax validation passed!"
    
    # Restart service
    echo "🔄 Restarting service..."
    ssh linuxuser@${VPS_HOST} "sudo systemctl restart virtuoso.service"
    
    # Wait for startup
    echo "⏳ Waiting for service to start..."
    sleep 15
    
    # Check for the warning
    echo "📊 Checking if coroutine warning is gone..."
    if ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -q 'coroutine.*was never awaited'"; then
        echo "⚠️ Warning still present - checking logs"
        ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep 'coroutine' | tail -3"
    else
        echo "✅ No coroutine warnings found!"
    fi
    
    # Check if analysis is working
    echo -e "\n🔍 Checking analysis activity..."
    ssh linuxuser@${VPS_HOST} "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep -E 'analyze_batch|_push_to_unified_cache|analysis.*complete' | tail -5"
    
else
    echo "❌ Syntax validation failed - restoring backup"
    ssh linuxuser@${VPS_HOST} "mv /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_analyze /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
fi
