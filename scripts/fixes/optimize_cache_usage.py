#!/usr/bin/env python3
"""
This script modifies the monitor.py file to optimize the cache usage for report generation.
It adds cache pre-warming functionality to the _generate_market_report method and 
enhances the get_ohlcv_for_report method for better cache utilization.

Usage:
    python scripts/fixes/optimize_cache_usage.py
"""

import os
import re
import shutil
import sys
from datetime import datetime

def main():
    """Main function that applies the fixes to monitor.py"""
    # Set file paths
    monitor_file = 'src/monitoring/monitor.py'
    backup_file = f'src/monitoring/monitor.py.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    # Make sure the file exists and is a file (not a directory)
    if not os.path.isfile(monitor_file):
        print(f"Error: {monitor_file} not found or is not a file. Make sure you're running this from the project root.")
        sys.exit(1)
    
    # Create backup
    print(f"Creating backup at {backup_file}")
    shutil.copy2(monitor_file, backup_file)
    
    # Read the file content
    with open(monitor_file, 'r') as f:
        content = f.read()
    
    # Apply fix 1: Add cache pre-warming to _generate_market_report
    print("Adding cache pre-warming to _generate_market_report method...")
    # Using more targeted regex to find the _generate_market_report method
    market_report_pattern = r"(async def _generate_market_report\(\) -> None:.*?# STEP 2: Data Collection\n\s+step_start = time\.time\(\))"
    market_report_replacement = """async def _generate_market_report(self) -> None:
        \"\"\"Generate and send a market report for all monitored symbols.\"\"\"
        # Create a unique transaction ID for tracking this report generation process
        transaction_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Starting market report generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Record steps and timings for process debugging
        steps_timing = {}
        
        try:
            # STEP 1: Validate prerequisites
            step_start = time.time()
            
            # Check if we have a market reporter
            if not hasattr(self, 'market_reporter') or self.market_reporter is None:
                self.logger.error(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] ERROR: No market reporter available")
                return
            
            # Make sure we have an alert manager for sending reports
            if not hasattr(self, 'alert_manager') or self.alert_manager is None:
                self.logger.error(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] ERROR: No alert manager available")
                return
            
            # Log reporter configuration
            reporter_enabled = getattr(self.market_reporter, 'enabled', True)
            reporter_pdf_enabled = getattr(self.market_reporter, 'pdf_enabled', True)
            self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Reporter enabled: {reporter_enabled}, PDF enabled: {reporter_pdf_enabled}")
                
            # Get list of symbols to report on
            symbols = self.get_monitored_symbols()
            self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Generating report for {len(symbols)} symbols")
            
            # Check if we have at least one symbol
            if not symbols:
                self.logger.warning(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] No symbols to report on, skipping report")
                return
            
            # Record step timing    
            steps_timing['prerequisites'] = time.time() - step_start
            
            # STEP 2: Pre-warm the cache for all symbols
            step_start = time.time()
            self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Starting cache pre-warming phase")
            
            cache_tasks = []
            stale_symbols = []
            
            # Identify which symbols need cache refreshing
            for symbol in symbols:
                if (symbol not in self._ohlcv_cache or 
                    time.time() - self._last_ohlcv_update.get(symbol, 0) > self._cache_ttl):
                    stale_symbols.append(symbol)
                    cache_tasks.append(self._get_cached_ohlcv(symbol))
            
            # Execute cache pre-warming tasks concurrently
            if cache_tasks:
                self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Pre-warming cache for {len(cache_tasks)} symbols")
                await asyncio.gather(*cache_tasks)
                self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Cache pre-warming completed")
            else:
                self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] All symbols already in cache, skipping pre-warming")
            
            # Record pre-warming statistics
            steps_timing['cache_prewarming'] = time.time() - step_start
            cache_stats = {
                "total_symbols": len(symbols),
                "fresh_cached_symbols": len(symbols) - len(stale_symbols),
                "refreshed_symbols": len(stale_symbols),
                "cache_hit_rate": f"{((len(symbols) - len(stale_symbols)) / len(symbols) * 100):.1f}%" if len(symbols) > 0 else "N/A",
            }
            self.logger.info(f"[DIAGNOSTICS] [MARKET_REPORT] [TXN:{transaction_id}] Cache stats: {json.dumps(cache_stats)}")
            
            # STEP 3: Data Collection
            step_start = time.time()"""
    
    # Use regex with DOTALL to match across multiple lines
    content = re.sub(market_report_pattern, market_report_replacement, content, flags=re.DOTALL)
    
    # Apply fix 2: Enhance get_ohlcv_for_report method for better caching
    print("Enhancing get_ohlcv_for_report method for better cache management...")
    get_ohlcv_pattern = r"(def get_ohlcv_for_report.*?return None[\s\n]+except Exception as e:.*?return \{\})"
    get_ohlcv_replacement = """def get_ohlcv_for_report(self, symbol: str, timeframe: str = 'base') -> Optional[pd.DataFrame]:
        \"\"\"
        Get cached OHLCV data formatted for ReportGenerator to avoid duplicate data fetching.
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to retrieve ('base', 'ltf', 'mtf', 'htf')
            
        Returns:
            Pandas DataFrame with OHLCV data ready for report generation or None if not available
        \"\"\"
        # Create a unique retrieval ID for tracking this data retrieval
        retrieval_id = str(uuid.uuid4())[:8]
        
        # Create a log prefix to reduce repetition
        prefix = f"[DIAGNOSTICS] [OHLCV_RETRIEVAL] [ID:{retrieval_id}]"
        
        self.logger.info(f"{prefix} Starting OHLCV retrieval for {symbol} ({timeframe})")
        
        try:
            # Check if we have cached data
            if symbol not in self._ohlcv_cache:
                self.logger.warning(f"{prefix} No cached OHLCV data for {symbol}")
                
                # List available symbols in cache for debugging
                available_symbols = list(self._ohlcv_cache.keys())
                cache_count = len(available_symbols)
                
                # More efficient cache summary logging
                if cache_count > 5:
                    symbol_preview = f"{available_symbols[:5]} and {cache_count-5} more..."
                else:
                    symbol_preview = f"{available_symbols}"
                self.logger.debug(f"{prefix} Cache contains {cache_count} symbols: {symbol_preview}")
                
                # Check when data was last fetched
                last_update = self._last_ohlcv_update.get(symbol, 0)
                if last_update > 0:
                    current_time = time.time()
                    time_diff = current_time - last_update
                    self.logger.debug(f"{prefix} Last update was {time_diff:.2f} seconds ago")
                    
                return None
                
            # Get the cached data for the specified timeframe
            cached_data = self._ohlcv_cache[symbol]
            
            # Check cache freshness
            current_time = time.time()
            cache_age = current_time - self._last_ohlcv_update.get(symbol, 0)
            self.logger.debug(f"{prefix} Cache age for {symbol}: {cache_age:.2f}s")
            
            # If cache is older than TTL/2, refresh in background but still use current cache
            if cache_age > (self._cache_ttl / 2):
                self.logger.debug(f"{prefix} Cache for {symbol} is aging ({cache_age:.2f}s), refreshing in background")
                try:
                    # Don't await - let it refresh in background
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._get_cached_ohlcv(symbol))
                except Exception as e:
                    self.logger.debug(f"{prefix} Background refresh error: {str(e)}")
            
            # Extract timeframes data using safer get() with type check
            timeframes_data = cached_data.get('processed', {})
            if not isinstance(timeframes_data, dict):
                self.logger.warning(f"{prefix} Invalid cache structure: 'processed' is not a dictionary")
                self.logger.debug(f"{prefix} Cache keys: {list(cached_data.keys())}")
                return None
            
            # Check if requested timeframe exists
            if timeframe in timeframes_data:
                ohlcv_data = timeframes_data[timeframe].get('data') 
                
                # Validate the data
                if isinstance(ohlcv_data, pd.DataFrame) and not ohlcv_data.empty:
                    self.logger.info(f"{prefix} Retrieved {len(ohlcv_data)} records for {symbol} ({timeframe})")
                    return ohlcv_data
                else:
                    self.logger.warning(f"{prefix} Invalid or empty DataFrame for {symbol} ({timeframe})")
            else:
                self.logger.warning(f"{prefix} Timeframe {timeframe} not found in cache for {symbol}")
                self.logger.debug(f"{prefix} Available timeframes: {list(timeframes_data.keys())}")
                
                # Check if we can derive the requested timeframe from base timeframe
                base_df = None
                if 'base' in timeframes_data:
                    base_df = timeframes_data['base'].get('data')
                    
                if isinstance(base_df, pd.DataFrame) and not base_df.empty:
                    self.logger.info(f"{prefix} Attempting to derive {timeframe} from base timeframe")
                    
                    # Map timeframes to pandas resample rules
                    resample_rules = {
                        'ltf': '5min',
                        'mtf': '30min',
                        'htf': '4h'
                    }
                    
                    if timeframe in resample_rules:
                        try:
                            # Make sure the dataframe is properly indexed by datetime
                            if not isinstance(base_df.index, pd.DatetimeIndex):
                                if 'timestamp' in base_df.columns:
                                    base_df = base_df.set_index('timestamp')
                                    base_df.index = pd.to_datetime(base_df.index, unit='ms')
                                else:
                                    self.logger.error(f"{prefix} Cannot resample: no datetime index or timestamp column")
                                    return None
                            
                            # Resample to target timeframe
                            resampled = base_df.resample(resample_rules[timeframe]).agg({
                                'open': 'first',
                                'high': 'max',
                                'low': 'min',
                                'close': 'last',
                                'volume': 'sum'
                            })
                            
                            # Drop any rows with NaN values
                            resampled = resampled.dropna()
                            
                            if not resampled.empty:
                                self.logger.info(f"{prefix} Successfully derived {len(resampled)} {timeframe} records from base timeframe")
                                
                                # Cache the derived data for future use
                                if timeframe not in timeframes_data:
                                    timeframes_data[timeframe] = {}
                                timeframes_data[timeframe]['data'] = resampled
                                
                                # Update the cache
                                self._ohlcv_cache[symbol]['processed'] = timeframes_data
                                
                                return resampled
                            else:
                                self.logger.warning(f"{prefix} Resampled dataframe is empty")
                        except Exception as e:
                            self.logger.error(f"{prefix} Error deriving timeframe: {str(e)}")
                            self.logger.error(traceback.format_exc())
                else:
                    self.logger.warning(f"{prefix} Base timeframe data missing or invalid, cannot derive {timeframe}")
            
            # If we get here, something went wrong with the cached data
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return None"""
    
    content = re.sub(get_ohlcv_pattern, get_ohlcv_replacement, content, flags=re.DOTALL)
    
    # Add note about required imports
    print("Adding note about required imports...")
    import_note = """
# Note: The modified monitor.py must have the following imports:
# - uuid
# - json
# - time
# - asyncio
# - traceback
# - pandas (as pd)
# - Optional from typing
"""
    
    # Add the note at the top of the file after existing imports
    import_section_end = content.find("def main")
    if import_section_end > 0:
        content = content[:import_section_end] + import_note + "\n" + content[import_section_end:]
    
    # Save the modified content back to the file
    with open(monitor_file, 'w') as f:
        f.write(content)
    
    print("Modifications applied successfully!")
    print(f"Original file backed up at {backup_file}")
    print("Changes made:")
    print("1. Added cache pre-warming to _generate_market_report method")
    print("2. Enhanced get_ohlcv_for_report method for better cache management")
    print("3. Added timeframe derivation capability for missing timeframes")
    print("4. Added note about required imports in monitor.py")
    
if __name__ == "__main__":
    main() 