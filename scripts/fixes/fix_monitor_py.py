#!/usr/bin/env python3
"""
Fix issues in the monitor.py file:
1. Remove the incomplete duplicate _generate_market_report method
2. Enhance get_ohlcv_for_report method with better debugging

Usage:
    python scripts/fixes/fix_monitor_py.py
"""

import re
import os
import sys
import shutil
from datetime import datetime

def main():
    # Set file paths
    monitor_file = 'src/monitoring/monitor.py'
    backup_file = f'src/monitoring/monitor.py.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    # Make sure the file exists
    if not os.path.exists(monitor_file):
        print(f"Error: {monitor_file} not found. Make sure you're running this from the project root.")
        sys.exit(1)
    
    # Create a backup
    print(f"Creating backup at {backup_file}")
    shutil.copy2(monitor_file, backup_file)
    
    # Read the file content
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Find and remove the incomplete _generate_market_report method
    pattern = r'(\s+def _process_market_data_sync.*?)\s+async def _generate_market_report\(\s*self\s*\)\s*->\s*None:.*?["""]Market data monitoring system'
    
    # Add a comment to explain
    replacement = r"\1\n    # Note: The _generate_market_report method is defined later in this file\n\n'''Market data monitoring system"
    
    # Apply the fix with a regex pattern that uses DOTALL mode to match across lines
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Fix 2: Enhance the get_ohlcv_for_report method
    pattern2 = r'def get_ohlcv_for_report\(self, symbol: str, timeframe: str = \'base\'\) -> Optional\[pd\.DataFrame\]:.*?return market_data\s+except Exception as e:'
    
    replacement2 = '''def get_ohlcv_for_report(self, symbol: str, timeframe: str = 'base') -> Optional[pd.DataFrame]:
        """
        Get cached OHLCV data formatted for ReportGenerator to avoid duplicate data fetching.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to retrieve ('base', 'ltf', 'mtf', 'htf')
            
        Returns:
            Pandas DataFrame with OHLCV data ready for report generation or None if not available
        """
        # Create a unique retrieval ID for tracking this data retrieval
        retrieval_id = str(uuid.uuid4())[:8]
        self.logger.info(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Starting OHLCV retrieval for {symbol} ({timeframe})")
        
        try:
            # Check if we have cached data
            if symbol not in self._ohlcv_cache:
                self.logger.warning(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] No cached OHLCV data for {symbol}")
                
                # List available symbols in cache for debugging
                available_symbols = list(self._ohlcv_cache.keys())
                cache_count = len(available_symbols)
                self.logger.debug(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Cache contains {cache_count} symbols: {available_symbols[:5]}" + 
                                  (f" and {cache_count-5} more..." if cache_count > 5 else ""))
                
                # Check when data was last fetched
                last_update = self._last_ohlcv_update.get(symbol, 0)
                if last_update > 0:
                    current_time = time.time()
                    time_diff = current_time - last_update
                    self.logger.debug(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Last update was {time_diff:.2f} seconds ago")
                    
                return None
                
            # Get the cached data for the specified timeframe
            cached_data = self._ohlcv_cache[symbol]
            
            # Check if the cached data has the right structure and timeframe
            if 'processed' in cached_data and isinstance(cached_data['processed'], dict):
                timeframes_data = cached_data['processed']
                
                # Check if requested timeframe exists
                if timeframe in timeframes_data:
                    ohlcv_data = timeframes_data[timeframe].get('data') 
                    
                    # Validate the data
                    if isinstance(ohlcv_data, pd.DataFrame) and not ohlcv_data.empty:
                        self.logger.info(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Retrieved {len(ohlcv_data)} records for {symbol} ({timeframe})")
                        return ohlcv_data
                    else:
                        self.logger.warning(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Invalid or empty DataFrame for {symbol} ({timeframe})")
                else:
                    self.logger.warning(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Timeframe {timeframe} not found in cache for {symbol}")
                    self.logger.debug(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Available timeframes: {list(timeframes_data.keys())}")
            else:
                self.logger.warning(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Invalid cache structure for {symbol}")
                self.logger.debug(f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}] Cache keys: {list(cached_data.keys())}")
            
            # If we get here, something went wrong with the cached data
            return None
            
        except Exception as e:'''
    
    # Apply the second fix with a regex pattern that uses DOTALL mode to match across lines
    new_content = re.sub(pattern2, replacement2, new_content, flags=re.DOTALL)
    
    # Write the fixed content back to the file
    with open(monitor_file, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed monitor.py file. A backup was saved at {backup_file}")
    print("Modifications made:")
    print("1. Removed incomplete duplicate _generate_market_report method")
    print("2. Enhanced get_ohlcv_for_report method with better debugging")

if __name__ == "__main__":
    main() 