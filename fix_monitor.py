#!/usr/bin/env python3
"""
Script to fix issues in the monitor.py file:
1. Fix the async validation function to handle dictionaries properly
2. Ensure orderbook data includes a timestamp field from initialization
3. Add a 'volume' field to ticker data if available from the exchange
"""

import re
import sys
import os

def fix_monitor_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Fix the async validation function to handle dictionaries properly
    # Find the validate_timeframes section in validate_market_data
    validate_timeframes_pattern = r'(\s+# Check timeframes if ohlcv data is present\n\s+if \'ohlcv\' in market_data and hasattr\(self, \'validate_timeframes\'\):\n\s+# Make sure we\'re not awaiting the result if it\'s not a coroutine\n\s+if callable\(self\.validate_timeframes\):\n\s+try:\n\s+)timeframe_results = self\.validate_timeframes\(market_data\.get\(\'ohlcv\', \{\}\)\)'
    
    validate_timeframes_replacement = r'\1# Check if validate_timeframes is a coroutine function\n                        if asyncio.iscoroutinefunction(self.validate_timeframes):\n                            timeframe_results = await self.validate_timeframes(market_data.get(\'ohlcv\', {}))\n                        else:\n                            # Call directly if it\'s a regular function\n                            timeframe_results = self.validate_timeframes(market_data.get(\'ohlcv\', {}))'
    
    content = re.sub(validate_timeframes_pattern, validate_timeframes_replacement, content)
    
    # Fix 2: Ensure orderbook data includes a timestamp field from initialization
    # Find the process_orderbook function
    process_orderbook_pattern = r'(async def process_orderbook\(self, symbol: str, orderbook_data: Dict\[str, Any\]\):\n\s+"""Process orderbook data for monitoring\."""\n\s+try:\n\s+# Only proceed if orderbook_data is valid\n\s+if not orderbook_data or not isinstance\(orderbook_data, dict\):\n\s+return orderbook_data\n\s+)'
    
    process_orderbook_replacement = r'\1            # Ensure orderbook has a timestamp\n            if \'timestamp\' not in orderbook_data:\n                orderbook_data[\'timestamp\'] = self.timestamp_utility.get_utc_timestamp()\n                self.logger.debug(f"Added missing timestamp to orderbook: {orderbook_data[\'timestamp\']}")\n            \n'
    
    content = re.sub(process_orderbook_pattern, process_orderbook_replacement, content)
    
    # Fix 3: Add a 'volume' field to ticker data if available from the exchange
    # Find the _validate_ticker function
    validate_ticker_pattern = r'(def _validate_ticker\(self, ticker_data\):\n\s+"""Validate ticker data\."""\n\s+if not isinstance\(ticker_data, dict\):\n\s+self\.logger\.error\(f"Ticker data must be a dictionary, got {type\(ticker_data\)}"\)\n\s+return False\n\s+)'
    
    validate_ticker_replacement = r'\1            # Add volume field if it\'s missing but available in raw data\n            if \'volume\' not in ticker_data and hasattr(self, \'exchange\') and self.exchange:\n                try:\n                    # Try to get volume from the exchange\'s last ticker response\n                    if hasattr(self.exchange, \'last_ticker_response\') and self.exchange.last_ticker_response:\n                        raw_ticker = self.exchange.last_ticker_response\n                        if isinstance(raw_ticker, dict) and \'volume\' in raw_ticker:\n                            ticker_data[\'volume\'] = raw_ticker[\'volume\']\n                            self.logger.debug(f"Added missing volume field to ticker: {ticker_data[\'volume\']}")\n                except Exception as e:\n                    self.logger.debug(f"Could not add volume field to ticker: {str(e)}")\n            \n'
    
    content = re.sub(validate_ticker_pattern, validate_ticker_replacement, content)
    
    # Write the modified content back to the file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Successfully fixed {file_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "src/monitoring/monitor.py"
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)
    
    # Create a backup
    backup_path = f"{file_path}.bak_before_fix"
    os.system(f"cp {file_path} {backup_path}")
    print(f"Created backup at {backup_path}")
    
    fix_monitor_file(file_path) 