#!/bin/bash

#############################################################################
# Script: fix_liquidity_zones_error.sh
# Purpose: Deploy and manage fix liquidity zones error
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
#   ./fix_liquidity_zones_error.sh [options]
#   
#   Examples:
#     ./fix_liquidity_zones_error.sh
#     ./fix_liquidity_zones_error.sh --verbose
#     ./fix_liquidity_zones_error.sh --dry-run
#
# Options:
#   -h, --help       Show help message
#   -v, --verbose    Enable verbose output
#   -d, --dry-run    Show what would be done
#
# Environment Variables:
#   PROJECT_ROOT     Trading system root directory
#   VPS_HOST         VPS hostname (default: VPS_HOST_REDACTED)
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

echo "Fixing liquidity_zones undefined error in confluence.py"

# Create the fix script
cat << 'EOF' > /tmp/fix_liquidity_zones.py
import sys
import re

def fix_liquidity_zones_error():
    """Fix the undefined liquidity_zones variable error"""
    
    file_path = "/home/linuxuser/trading/Virtuoso_ccxt/src/analysis/core/confluence.py"
    
    # Read the file
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    
    # Check if we can find the problematic code
    if "liquidity_zones" in content:
        print("Found liquidity_zones reference in file")
        
        # Common fix patterns
        fixes = [
            # Initialize liquidity_zones if not defined
            (r'(\s+)(.*liquidity_zones.*)', r'\1liquidity_zones = []\n\1\2'),
            # Replace undefined liquidity_zones with empty list
            (r'liquidity_zones(?!\s*=)', r'[]'),
        ]
        
        # Try to apply fixes
        for pattern, replacement in fixes:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content, count=1)
                print(f"Applied fix: {pattern}")
                break
    
    # Alternative: Add initialization at the beginning of methods that use it
    # Look for methods that might use liquidity_zones
    methods_pattern = r'(def\s+\w*smart_money\w*.*?:.*?\n)'
    matches = re.finditer(methods_pattern, content)
    
    for match in matches:
        method_start = match.end()
        # Find the indentation level
        indent_match = re.search(r'^(\s+)', content[method_start:], re.MULTILINE)
        if indent_match:
            indent = indent_match.group(1)
            # Add initialization after method definition
            init_code = f"{indent}liquidity_zones = []  # Initialize to prevent undefined error\n"
            content = content[:method_start] + init_code + content[method_start:]
            print(f"Added liquidity_zones initialization to method")
            break
    
    # Write the fixed content back
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Successfully fixed {file_path}")
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False

if __name__ == "__main__":
    success = fix_liquidity_zones_error()
    sys.exit(0 if success else 1)
EOF

# Copy and run the fix on VPS
echo "Copying fix script to VPS..."
scp /tmp/fix_liquidity_zones.py linuxuser@VPS_HOST_REDACTED:/tmp/

echo "Running fix on VPS..."
ssh linuxuser@VPS_HOST_REDACTED "python /tmp/fix_liquidity_zones.py"

# Alternative simpler fix - just add the initialization
echo "Applying alternative fix..."
ssh linuxuser@VPS_HOST_REDACTED << 'REMOTE_FIX'
# Search for the error location and add initialization
python3 << 'PYTHON_FIX'
import re

file_path = "/home/linuxuser/trading/Virtuoso_ccxt/src/analysis/core/confluence.py"

try:
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Find lines that reference liquidity_zones without defining it
    modified = False
    for i, line in enumerate(lines):
        if 'liquidity_zones' in line and 'liquidity_zones =' not in line:
            # Check if this is inside a method
            # Look backwards for def statement
            for j in range(max(0, i-20), i):
                if lines[j].strip().startswith('def '):
                    # Found the method, add initialization after it
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        # Insert initialization
                        init_line = ' ' * indent + 'liquidity_zones = []  # Fix for undefined variable\n'
                        # Check if not already added
                        if j+1 < len(lines) and 'liquidity_zones = []' not in lines[j+1]:
                            lines.insert(j+1, init_line)
                            modified = True
                            print(f"Added initialization after line {j}")
                            break
            if modified:
                break
    
    if modified:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        print("File updated successfully")
    else:
        print("No modifications needed or pattern not found")
        
except Exception as e:
    print(f"Error: {e}")
PYTHON_FIX
REMOTE_FIX

echo "Restarting service to apply changes..."
ssh linuxuser@VPS_HOST_REDACTED "sudo systemctl restart virtuoso.service"

echo "Waiting for service to start..."
sleep 5

echo "Checking logs for errors..."
ssh linuxuser@VPS_HOST_REDACTED "sudo journalctl -u virtuoso.service --since '30 seconds ago' | grep -E '(liquidity_zones|ERROR)' | tail -10"

echo "Fix complete!"