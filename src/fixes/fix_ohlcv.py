#!/usr/bin/env python
"""
Fix the _ohlcv_cache attribute missing from MarketMonitor
This causes error when generating market reports.
"""

import re
import os
import datetime

def fix_ohlcv_cache():
    """Fix the _ohlcv_cache attribute by:
    1. Adding initialization in __init__ method
    2. Adding population in fetch_market_data method
    """
    file_path = 'src/monitoring/monitor.py'
    backup_path = f'{file_path}.bak_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    # Create backup
    os.system(f'cp {file_path} {backup_path}')
    print(f"Created backup: {backup_path}")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Add _ohlcv_cache initialization in __init__
    # Find the initialization block where caches are defined
    init_pattern = r'(        # Initialize market data cache for fetch_market_data method\s+self\._market_data_cache = {}\s+self\._cache_ttl = \d+  # \d+ minutes default cache TTL\s+self\._last_ohlcv_update = {})'
    
    init_replacement = r'\1\n        \n        # Initialize OHLCV cache for reports\n        self._ohlcv_cache = {}'
    
    # Replace the initialization code
    content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)
    
    # Fix 2: Add _ohlcv_cache population in fetch_market_data
    # Find the cache update block in fetch_market_data
    cache_pattern = r'(            # Update cache\s+self\._market_data_cache\[symbol_str\] = {.*?timestamp\": self\.timestamp_utility\.get_utc_timestamp\(\).*?}\s+)'
    
    cache_replacement = r'\1            \n            # Update OHLCV cache for reports\n            self._ohlcv_cache[symbol_str] = {\n                \'raw\': raw_ohlcv,\n                \'processed\': ohlcv_data,\n                \'timestamp\': self.timestamp_utility.get_utc_timestamp()\n            }\n            \n'
    
    # Replace the cache update code
    content = re.sub(cache_pattern, cache_replacement, content, flags=re.DOTALL)
    
    # Write the changes back to the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed missing _ohlcv_cache attribute in MarketMonitor")
    print("1. Added initialization in __init__")
    print("2. Added update code in fetch_market_data")

if __name__ == "__main__":
    fix_ohlcv_cache() 