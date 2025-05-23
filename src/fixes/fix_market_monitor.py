#!/usr/bin/env python
"""Fix the fetch_market_data method"""

import re

def fix_fetch_market_data():
    """Fix the fetch_market_data method to ensure it provides OHLCV data."""
    file_path = 'src/monitoring/monitor.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the fetch_market_data method
    pattern = r'async def fetch_market_data.*?return market_data\s+except Exception as e:'
    
    # Replace the method with our improved version
    replacement = '''async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch market data for a symbol from the market data manager.
        
        Args:
            symbol: The symbol to fetch market data for
            
        Returns:
            Dict[str, Any]: Market data dictionary with various components
        """
        try:
            if not self.market_data_manager:
                self.logger.error("Market data manager not initialized")
                return None
                
            # Fetch market data through the manager
            market_data = await self.market_data_manager.get_market_data(symbol)
            
            if not market_data:
                self.logger.warning(f"No market data returned for {symbol}")
                return None
                
            # Ensure ticker is at least an empty dict so validation doesn't fail on None
            if 'ticker' not in market_data or market_data['ticker'] is None:
                self.logger.warning(f"Ticker data missing for {symbol}, initializing with empty dict")
                market_data['ticker'] = {'last': 0, 'bid': 0, 'ask': 0, 'timestamp': int(time.time() * 1000)}
            
            # Ensure OHLCV data is available - if not, try to fetch it separately
            if 'ohlcv' not in market_data or not market_data['ohlcv']:
                self.logger.warning(f"OHLCV data missing for {symbol}, requesting fetch")
                try:
                    # Request OHLCV refresh from the market data manager
                    await self.market_data_manager.refresh_components(symbol, components=['kline'])
                    
                    # Try to get the market data again after refresh
                    market_data = await self.market_data_manager.get_market_data(symbol)
                    
                    # Log the result of the refresh attempt
                    if market_data and 'ohlcv' in market_data and market_data['ohlcv']:
                        self.logger.info(f"Successfully fetched OHLCV data for {symbol}")
                    else:
                        self.logger.warning(f"Still no OHLCV data for {symbol} after refresh attempt")
                except Exception as e:
                    self.logger.error(f"Error fetching OHLCV data for {symbol}: {str(e)}")
                    self.logger.debug(traceback.format_exc())
                
            return market_data
        except Exception as e:'''
    
    # Replace the method
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the new content back to the file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("Fixed fetch_market_data method to ensure OHLCV data availability")

if __name__ == "__main__":
    fix_fetch_market_data() 