#!/usr/bin/env python3
"""
Fix script for the ticker initialization issue in market_data_manager.py

This fixes the 'NoneType' object does not support item assignment error
when updating ticker data from WebSocket.
"""

import os
import re
import sys
import shutil
from datetime import datetime

def fix_ticker_initialization():
    """Fix the ticker initialization issue in _update_ticker_from_ws method."""
    # Define paths
    manager_path = 'src/core/market/market_data_manager.py'
    
    # Check if file exists
    if not os.path.isfile(manager_path):
        print(f"Error: {manager_path} not found")
        return False
    
    # Create backup
    backup_path = f"{manager_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(manager_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    # Read file content
    with open(manager_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the pattern for the ticker initialization
    init_pattern = r"(# Initialize ticker if it doesn't exist\s+if 'ticker' not in self\.data_cache\[symbol\]:)"
    
    # Replacement to also check for None
    init_replacement = r"\1 or self.data_cache[symbol]['ticker'] is None:"
    
    # Apply the fix for ticker initialization
    modified_content = re.sub(init_pattern, init_replacement, content)
    
    # Check if any changes were made
    if modified_content == content:
        print("No changes made to ticker initialization - trying alternative approach")
        
        # Try another approach - add the None check in each place where ticker is used
        ticker_access_pattern = r"(self\.data_cache\[symbol\]\['ticker'\])\[(['\w]+)\]"
        ticker_access_replacement = r"# Ensure ticker exists\n        if 'ticker' not in self.data_cache[symbol] or self.data_cache[symbol]['ticker'] is None:\n            self.data_cache[symbol]['ticker'] = {}\n        \1[\2]"
        
        # Apply the fix - but only to the first occurrence to avoid excessive replacements
        first_occurrence = re.search(ticker_access_pattern, content)
        if first_occurrence:
            print(f"Found ticker access pattern at position {first_occurrence.start()}")
            modified_content = content[:first_occurrence.start()] + ticker_access_replacement.replace(r"\1", first_occurrence.group(1)).replace(r"\2", first_occurrence.group(2)) + content[first_occurrence.end():]
        else:
            print("Ticker access pattern not found")
            return False
    
    # Write changes back to file
    with open(manager_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"Successfully updated {manager_path}")
    return True

def restore_backup():
    """Restore from the most recent backup."""
    manager_path = 'src/core/market/market_data_manager.py'
    backups = [f for f in os.listdir(os.path.dirname(manager_path)) 
              if f.startswith(os.path.basename(manager_path) + '.bak_')]
    
    if not backups:
        print("No backups found")
        return False
    
    # Sort backups by timestamp (newest first)
    latest_backup = sorted(backups, reverse=True)[0]
    backup_path = os.path.join(os.path.dirname(manager_path), latest_backup)
    
    # Restore from backup
    shutil.copy2(backup_path, manager_path)
    print(f"Restored from {backup_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        restore_backup()
    else:
        fix_ticker_initialization() 