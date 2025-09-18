#!/usr/bin/env python
"""
Script to restore missing methods in SignalGenerator from backup.
This will fix the BUY signal Discord alert issue.
"""

import os
import sys
import shutil
from datetime import datetime

def main():
    # Paths
    current_file = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/src/signal_generation/signal_generator.py"
    backup_file = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/archives/2024/backups/signal_generator.py.backup"
    
    # Create a backup of current file first
    backup_name = f"{current_file}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(current_file, backup_name)
    print(f"Created backup: {backup_name}")
    
    # Read both files
    with open(current_file, 'r') as f:
        current_content = f.read()
    
    with open(backup_file, 'r') as f:
        backup_content = f.read()
    
    # Extract missing methods from backup
    missing_methods = []
    
    # Method 1: process_signal (lines 1680-1989)
    start = backup_content.find("    async def process_signal(self, signal_data: Dict[str, Any]) -> None:")
    end = backup_content.find("\n    def _standardize_signal_data", start)
    if start != -1 and end != -1:
        process_signal_method = backup_content[start:end]
        missing_methods.append(("process_signal", process_signal_method))
        print("Extracted process_signal method")
    
    # Method 2: _standardize_signal_data (lines 1991-2058)
    start = backup_content.find("    def _standardize_signal_data(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:")
    end = backup_content.find("\n    def _resolve_price", start)
    if start != -1 and end != -1:
        standardize_method = backup_content[start:end]
        missing_methods.append(("_standardize_signal_data", standardize_method))
        print("Extracted _standardize_signal_data method")
    
    # Method 3: _resolve_price (lines 2060-2079)
    start = backup_content.find("    def _resolve_price(self, signal_data: Dict[str, Any], signal_id: str) -> float:")
    end = backup_content.find("\n    def _calculate_reliability", start)
    if start != -1 and end != -1:
        resolve_price_method = backup_content[start:end]
        missing_methods.append(("_resolve_price", resolve_price_method))
        print("Extracted _resolve_price method")
    
    # Method 4: _calculate_reliability (lines 2081-2154)
    start = backup_content.find("    def _calculate_reliability(self, signal_data: Dict[str, Any]) -> float:")
    end = backup_content.find("\n    async def _fetch_ohlcv_data", start)
    if start != -1 and end != -1:
        reliability_method = backup_content[start:end]
        missing_methods.append(("_calculate_reliability", reliability_method))
        print("Extracted _calculate_reliability method")
    
    # Method 5: _fetch_ohlcv_data (lines 2156+)
    start = backup_content.find("    async def _fetch_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 50)")
    if start != -1:
        # Find the end of this method (next method or end of class)
        next_method = backup_content.find("\n    def ", start + 1)
        next_async_method = backup_content.find("\n    async def ", start + 1)
        
        ends = [x for x in [next_method, next_async_method] if x > 0]
        if ends:
            end = min(ends)
        else:
            end = len(backup_content)
        
        fetch_ohlcv_method = backup_content[start:end]
        missing_methods.append(("_fetch_ohlcv_data", fetch_ohlcv_method))
        print("Extracted _fetch_ohlcv_data method")
    
    # Now add these methods to the current file
    # Find a good insertion point - after the last method
    insertion_point = current_content.rfind("\n    async def _send_alert")
    if insertion_point == -1:
        insertion_point = current_content.rfind("\n    def ")
    
    # Find the end of the last method
    if insertion_point != -1:
        # Find the end of this method
        next_class = current_content.find("\nclass ", insertion_point)
        if next_class == -1:
            next_class = len(current_content)
        
        # Insert before the end of class or file
        insert_at = next_class
        
        # Prepare the methods to insert
        methods_text = "\n\n    # ====== RESTORED METHODS FROM BACKUP ======\n"
        for method_name, method_code in missing_methods:
            methods_text += "\n" + method_code + "\n"
        
        # Insert the methods
        new_content = current_content[:insert_at] + methods_text + current_content[insert_at:]
        
        # Write the updated file
        with open(current_file, 'w') as f:
            f.write(new_content)
        
        print(f"\nSuccessfully added {len(missing_methods)} missing methods to {current_file}")
        print("\nRestored methods:")
        for method_name, _ in missing_methods:
            print(f"  - {method_name}")
    else:
        print("ERROR: Could not find insertion point in current file")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())