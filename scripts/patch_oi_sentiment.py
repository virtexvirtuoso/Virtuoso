#!/usr/bin/env python3
"""
Patch script to fix OI data showing as 0.0 in sentiment processing.

The issue: OI data is fetched correctly but shows as {'value': 0.0, 'change_24h': 0.0}
when passed to sentiment indicators.
"""

import os
import sys
import re

def patch_monitor_file():
    """Patch the monitor.py file to fix OI data handling."""
    
    monitor_path = 'src/monitoring/monitor.py'
    
    if not os.path.exists(monitor_path):
        print(f"Error: {monitor_path} not found")
        return False
    
    with open(monitor_path, 'r') as f:
        content = f.read()
    
    # Look for where sentiment data is assembled
    # We need to find where open_interest is added to sentiment with 0.0 values
    
    # Pattern 1: Look for default OI structure creation
    pattern1 = r"'open_interest':\s*{\s*'value':\s*0\.0,\s*'change_24h':\s*0\.0,\s*'timestamp':\s*[^}]+\}"
    
    # Pattern 2: Look for where sentiment data is built
    pattern2 = r"sentiment\s*=\s*{[^}]*'open_interest'[^}]*}"
    
    # Pattern 3: Look for get_sentiment_data or similar
    pattern3 = r"def\s+\w*get\w*sentiment\w*data"
    
    replacements = []
    
    # Check if we need to add proper OI data retrieval
    if "'open_interest': {" in content and "'value': 0.0" in content:
        print("Found potential default OI structure")
        
        # Replace default OI with proper data retrieval
        old_pattern = r"'open_interest':\s*{\s*'value':\s*0\.0,\s*'change_24h':\s*0\.0,\s*'timestamp':\s*[^}]+\}"
        new_code = """'open_interest': self._get_open_interest_for_sentiment(symbol, market_data)"""
        
        replacements.append((old_pattern, new_code))
    
    # Apply replacements
    modified = False
    for old, new in replacements:
        if re.search(old, content):
            content = re.sub(old, new, content)
            modified = True
            print(f"Applied replacement: {old[:50]}... -> {new[:50]}...")
    
    # Add helper method if needed
    if modified and "_get_open_interest_for_sentiment" not in content:
        # Find a good place to add the method (after __init__ or at end of class)
        class_end = content.rfind("\n\n# ")  # Find end of class methods
        if class_end == -1:
            class_end = len(content) - 1
        
        helper_method = '''
    def _get_open_interest_for_sentiment(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get open interest data formatted for sentiment analysis."""
        try:
            # Try to get OI from market data
            oi_data = market_data.get('open_interest', {})
            
            # If we have valid OI data from market data manager
            if isinstance(oi_data, dict) and 'current' in oi_data:
                return {
                    'value': float(oi_data.get('current', 0)),
                    'change_24h': float(oi_data.get('change_24h', 0)),
                    'timestamp': int(oi_data.get('timestamp', time.time() * 1000))
                }
            
            # Try to get from data cache directly
            if hasattr(self, 'data_processor') and hasattr(self.data_processor, 'market_data_manager'):
                cache_oi = self.data_processor.market_data_manager.get_open_interest_data(symbol)
                if cache_oi and isinstance(cache_oi, dict):
                    current = float(cache_oi.get('current', cache_oi.get('value', 0)))
                    previous = float(cache_oi.get('previous', 0))
                    change = current - previous if previous else 0
                    
                    return {
                        'value': current,
                        'change_24h': change,
                        'timestamp': int(cache_oi.get('timestamp', time.time() * 1000))
                    }
            
            # Default if no data found
            self.logger.warning(f"No valid OI data found for {symbol}, using defaults")
            return {
                'value': 0.0,
                'change_24h': 0.0,
                'timestamp': int(time.time() * 1000)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting OI data for sentiment: {str(e)}")
            return {
                'value': 0.0,
                'change_24h': 0.0,
                'timestamp': int(time.time() * 1000)
            }
'''
        
        content = content[:class_end] + helper_method + content[class_end:]
        print("Added _get_open_interest_for_sentiment helper method")
    
    if modified:
        # Create backup
        backup_path = monitor_path + '.backup'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"Created backup at {backup_path}")
        
        # Write modified content
        with open(monitor_path, 'w') as f:
            f.write(content)
        print(f"Modified {monitor_path}")
        return True
    else:
        print("No modifications needed in monitor.py")
        return False


def find_sentiment_assembly():
    """Find where sentiment data is assembled with OI."""
    
    print("\nSearching for sentiment data assembly...")
    
    files_to_check = [
        'src/monitoring/monitor.py',
        'src/data_processing/data_processor.py',
        'src/core/market/market_data_manager.py'
    ]
    
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if "'open_interest'" in line and ("0.0" in line or "None" in line or "{}" in line):
                print(f"\nFound in {file_path} at line {i+1}:")
                # Show context
                start = max(0, i-3)
                end = min(len(lines), i+4)
                for j in range(start, end):
                    prefix = ">>> " if j == i else "    "
                    print(f"{prefix}{j+1}: {lines[j].rstrip()}")


if __name__ == "__main__":
    print("OI Sentiment Data Patch")
    print("======================\n")
    
    find_sentiment_assembly()
    
    # For now, just analyze - don't auto-patch
    print("\n\nTo fix the issue, we need to:")
    print("1. Find where sentiment['open_interest'] is set to default values")
    print("2. Replace it with actual OI data from market_data_manager")
    print("3. Ensure the data structure matches what sentiment_indicators expects")