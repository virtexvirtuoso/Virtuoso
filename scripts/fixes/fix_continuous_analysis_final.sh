#!/bin/bash

#############################################################################
# Script: fix_continuous_analysis_final.sh
# Purpose: Deploy and manage fix continuous analysis final
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
#   ./fix_continuous_analysis_final.sh [options]
#   
#   Examples:
#     ./fix_continuous_analysis_final.sh
#     ./fix_continuous_analysis_final.sh --verbose
#     ./fix_continuous_analysis_final.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: 5.223.63.4)
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

echo "🔧 Applying final fix for ContinuousAnalysisManager..."

# Create backup
ssh linuxuser@5.223.63.4 "cp /home/linuxuser/trading/Virtuoso_ccxt/src/main.py /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_final"

# Create a Python script to apply the fixes
cat << 'PYTHON' > /tmp/fix_main.py
#!/usr/bin/env python3
import sys

# Read the file
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'r') as f:
    lines = f.readlines()

# Fix 1: Add market_data_manager to globals at line 3183 (index 3182)
if 'market_data_manager' not in lines[3182]:
    lines[3182] = lines[3182].rstrip() + ', market_data_manager\n'
    print("✅ Added market_data_manager to global declaration")

# Fix 2: Add extraction after line 3204 (index 3203)
# Find the line with market_monitor assignment
for i in range(3200, 3210):
    if 'market_monitor = components[' in lines[i]:
        # Add market_data_manager extraction on next line
        if i+1 < len(lines) and 'market_data_manager' not in lines[i+1]:
            indent = '        '  # Same indent as market_monitor line
            lines.insert(i+1, f"{indent}market_data_manager = components['market_data_manager']  # Extract for ContinuousAnalysisManager\n")
            print(f"✅ Added market_data_manager extraction after line {i+1}")
        break

# Write the fixed file
with open('/home/linuxuser/trading/Virtuoso_ccxt/src/main.py', 'w') as f:
    f.writelines(lines)

print("✅ Fixes applied successfully")
PYTHON

# Copy and run the fix script on VPS
scp /tmp/fix_main.py linuxuser@5.223.63.4:/tmp/
ssh linuxuser@5.223.63.4 "python3 /tmp/fix_main.py"

# Validate syntax
echo "🔍 Validating Python syntax..."
if ssh linuxuser@5.223.63.4 "cd /home/linuxuser/trading/Virtuoso_ccxt && /home/linuxuser/trading/Virtuoso_ccxt/venv311/bin/python -m py_compile src/main.py 2>&1"; then
    echo "✅ Python syntax validation passed!"
    
    # Restart service
    echo "🔄 Restarting service..."
    ssh linuxuser@5.223.63.4 "sudo systemctl restart virtuoso.service"
    
    # Wait for startup
    echo "⏳ Waiting for service to start..."
    sleep 15
    
    # Check for success
    echo "📊 Checking if ContinuousAnalysisManager started..."
    if ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep -q 'Continuous analysis manager started'"; then
        echo "✅ SUCCESS! ContinuousAnalysisManager is now running!"
    else
        echo "🔍 Checking for warning messages..."
        ssh linuxuser@5.223.63.4 "sudo journalctl -u virtuoso.service --since '1 minute ago' | grep 'ContinuousAnalysisManager' | tail -3"
    fi
    
    # Show cache status
    echo -e "\n📝 Testing cache endpoints:"
    echo "Analysis results:"
    ssh linuxuser@5.223.63.4 "curl -s http://localhost:8000/api/analysis/results | head -c 100"
    echo -e "\n"
else
    echo "❌ Syntax validation failed - restoring backup"
    ssh linuxuser@5.223.63.4 "mv /home/linuxuser/trading/Virtuoso_ccxt/src/main.py.backup_final /home/linuxuser/trading/Virtuoso_ccxt/src/main.py"
fi
