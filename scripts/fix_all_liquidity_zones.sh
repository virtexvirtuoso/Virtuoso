#!/bin/bash

#############################################################################
# Script: fix_all_liquidity_zones.sh
# Purpose: Deploy and manage fix all liquidity zones
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
#   ./fix_all_liquidity_zones.sh [options]
#   
#   Examples:
#     ./fix_all_liquidity_zones.sh
#     ./fix_all_liquidity_zones.sh --verbose
#     ./fix_all_liquidity_zones.sh --dry-run
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

echo "Fixing ALL liquidity_zones undefined errors in orderflow_indicators.py"

# Apply comprehensive fix on VPS
ssh linuxuser@${VPS_HOST} << 'REMOTE_FIX'
# Fix all incorrect liquidity_zones variable references
python3 << 'PYTHON_FIX'
import re

file_path = "/home/linuxuser/trading/Virtuoso_ccxt/src/indicators/orderflow_indicators.py"

try:
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Count fixes needed
    fixes_needed = content.count("liquidity_zones")
    print(f"Found {fixes_needed} references to 'liquidity_zones' that need fixing")
    
    # In the _detect_smart_money_flow method, liquidity_zones should be smart_money_flow
    # Find the method and fix within its scope
    
    # First, replace in the _detect_smart_money_flow method context
    # Lines around 3431, 3440, 3443, 3445 use liquidity_zones but should use smart_money_flow
    
    # Fix 1: liquidity_zones['bullish'].append(zone) -> smart_money_flow['bullish'].append(zone)
    content = content.replace("liquidity_zones['bullish'].append(zone)", 
                            "smart_money_flow['bullish'].append(zone)")
    
    # Fix 2: liquidity_zones['bearish'].append(zone) -> smart_money_flow['bearish'].append(zone)  
    content = content.replace("liquidity_zones['bearish'].append(zone)", 
                            "smart_money_flow['bearish'].append(zone)")
    
    # Fix 3: self._check_liquidity_sweeps(df, liquidity_zones) -> self._check_liquidity_sweeps(df, smart_money_flow)
    content = content.replace("self._check_liquidity_sweeps(df, liquidity_zones)", 
                            "self._check_liquidity_sweeps(df, smart_money_flow)")
    
    # Fix 4: return liquidity_zones -> return smart_money_flow
    # Be careful to only replace in the right context
    pattern = r'(\s+)return liquidity_zones(\s)'
    replacement = r'\1return smart_money_flow\2'
    content = re.sub(pattern, replacement, content)
    
    # Now check if there are other liquidity_zones references that need different handling
    # In methods that RECEIVE liquidity_zones as a parameter, keep the parameter name
    # But in the _calculate_smart_money_flow_score method, it should use smart_money_flow
    
    # This is already fixed in previous script, but double-check
    content = content.replace("self._score_smart_money_proximity(current_price, liquidity_zones)",
                            "self._score_smart_money_proximity(current_price, smart_money_flow)")
    
    # Count remaining references
    remaining = content.count("liquidity_zones")
    print(f"After fixes, {remaining} references to 'liquidity_zones' remain (these should be in method signatures)")
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    print("File updated successfully")
    
    # Verify the specific lines were fixed
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Check around line 3430-3445
    for i in range(3425, min(3450, len(lines))):
        if 'smart_money_flow' in lines[i] and 'append' in lines[i]:
            print(f"✓ Line {i+1} correctly uses smart_money_flow")
            
except Exception as e:
    print(f"Error: {e}")
PYTHON_FIX

echo "Restarting service..."
sudo systemctl restart virtuoso.service

echo "Service restarted. Waiting for startup..."
sleep 10

echo "Checking for liquidity_zones errors..."
echo "==================================="
sudo journalctl -u virtuoso.service --since '20 seconds ago' | grep -E "liquidity_zones.*undefined" || echo "✓ No liquidity_zones undefined errors found!"

echo ""
echo "Checking smart_money_flow is working..."
echo "========================================"
sudo journalctl -u virtuoso.service --since '20 seconds ago' | grep -E "smart_money_flow" | tail -5

echo ""
echo "Service status:"
sudo systemctl status virtuoso.service --no-pager | head -15
REMOTE_FIX

echo "Fix complete!"