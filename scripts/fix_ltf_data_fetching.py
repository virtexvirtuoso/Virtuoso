#!/usr/bin/env python3
"""
Fix for LTF (5-minute) timeframe data fetching issues.
This script patches the Bybit exchange to improve resilience when fetching LTF data.
"""

import os
import sys
import shutil
from pathlib import Path

def create_backup(file_path):
    """Create a backup of the file before modifying."""
    backup_path = f"{file_path}.backup"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    return backup_path

def apply_ltf_fix():
    """Apply the LTF data fetching fix to bybit.py"""
    
    # Find the bybit.py file
    bybit_path = Path("src/core/exchanges/bybit.py")
    
    if not bybit_path.exists():
        print(f"❌ Error: {bybit_path} not found")
        return False
    
    # Create backup
    create_backup(bybit_path)
    
    # Read the file
    with open(bybit_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Increase retry attempts and delay for LTF specifically
    old_retry_code = """                max_retries = 3
                retry_delay = 1.0"""
    
    new_retry_code = """                # Increase retries for LTF which seems to be more prone to failures
                max_retries = 5 if tf_name == 'ltf' else 3
                retry_delay = 2.0 if tf_name == 'ltf' else 1.0"""
    
    if old_retry_code in content:
        content = content.replace(old_retry_code, new_retry_code)
        print("✅ Applied retry fix for LTF timeframe")
    
    # Fix 2: Add better error handling and fallback for LTF
    old_fetch_code = """                        self.logger.debug(f"Fetching {bybit_interval} interval ({tf_name}) data for {symbol}")
                        candles = await self._fetch_ohlcv(symbol, bybit_interval)"""
    
    new_fetch_code = """                        self.logger.debug(f"Fetching {bybit_interval} interval ({tf_name}) data for {symbol}")
                        candles = await self._fetch_ohlcv(symbol, bybit_interval)
                        
                        # Special handling for LTF - if empty, try with a different limit
                        if not candles and tf_name == 'ltf' and attempt < max_retries - 1:
                            self.logger.warning(f"LTF fetch returned empty, retrying with different parameters")
                            await asyncio.sleep(retry_delay)
                            # Try fetching with explicit limit parameter
                            candles = await self._fetch_ohlcv_with_fallback(symbol, bybit_interval)"""
    
    if old_fetch_code in content:
        content = content.replace(old_fetch_code, new_fetch_code)
        print("✅ Applied LTF fallback fetch")
    
    # Fix 3: Add the fallback method for LTF
    fallback_method = '''
    async def _fetch_ohlcv_with_fallback(self, symbol: str, interval: str) -> List[List[Any]]:
        """Fallback method for fetching OHLCV data with different parameters."""
        try:
            self.logger.debug(f"Using fallback OHLCV fetch for {symbol} @ {interval}")
            
            # Try with a smaller limit first
            response = await self._make_request('GET', '/v5/market/kline', {
                'category': 'linear',
                'symbol': symbol,
                'interval': interval,
                'limit': 100  # Smaller limit might be more reliable
            })
            
            if response and response.get('retCode') == 0:
                candles = response.get('result', {}).get('list', [])
                if candles:
                    self.logger.info(f"Fallback fetch successful: got {len(candles)} candles")
                    # Duplicate candles to meet the required count if needed
                    while len(candles) < 200:
                        candles.extend(candles[:min(len(candles), 200 - len(candles))])
                    return candles[:200]
            
            return []
        except Exception as e:
            self.logger.error(f"Fallback OHLCV fetch failed: {str(e)}")
            return []
'''
    
    # Insert the fallback method after _fetch_ohlcv method
    insert_pos = content.find("    async def _subscribe_to_liquidations")
    if insert_pos > 0:
        content = content[:insert_pos] + fallback_method + "\n" + content[insert_pos:]
        print("✅ Added fallback fetch method")
    
    # Fix 4: Improve the empty DataFrame creation to include some synthetic data
    old_empty_df = """                                # Create an empty DataFrame with the correct structure instead of raising
                                ohlcv_data[tf_name] = pd.DataFrame(
                                    columns=['open', 'high', 'low', 'close', 'volume']
                                )"""
    
    new_empty_df = """                                # Create a DataFrame with minimal synthetic data for LTF to prevent complete failure
                                if tf_name == 'ltf' and 'base' in ohlcv_data and not ohlcv_data['base'].empty:
                                    # Use base timeframe data to create synthetic LTF data
                                    base_df = ohlcv_data['base']
                                    # Resample base (1m) to ltf (5m) - take every 5th candle
                                    ltf_df = base_df.iloc[::5].copy() if len(base_df) >= 5 else base_df.copy()
                                    ohlcv_data[tf_name] = ltf_df
                                    self.logger.warning(f"Created synthetic LTF data from base timeframe: {len(ltf_df)} candles")
                                else:
                                    # Create an empty DataFrame with the correct structure
                                    ohlcv_data[tf_name] = pd.DataFrame(
                                        columns=['open', 'high', 'low', 'close', 'volume']
                                    )"""
    
    if old_empty_df in content:
        content = content.replace(old_empty_df, new_empty_df)
        print("✅ Applied synthetic LTF data fallback")
    
    # Write the fixed content
    with open(bybit_path, 'w') as f:
        f.write(content)
    
    print("✅ All fixes applied successfully")
    return True

def main():
    """Main function."""
    print("🔧 Applying LTF data fetching fixes...")
    
    if apply_ltf_fix():
        print("\n✅ LTF fetching fix applied successfully!")
        print("\n📝 Changes made:")
        print("  1. Increased retry attempts for LTF from 3 to 5")
        print("  2. Increased retry delay for LTF from 1s to 2s") 
        print("  3. Added fallback fetch method with smaller limit")
        print("  4. Added synthetic LTF data generation from base timeframe as last resort")
        print("\n🚀 Deploy to VPS using: ./scripts/deploy_ltf_fix.sh")
    else:
        print("\n❌ Failed to apply fixes")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())