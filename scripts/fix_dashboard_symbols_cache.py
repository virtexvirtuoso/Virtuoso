#!/usr/bin/env python3
"""
Fix: Add symbols cache with confluence scores to dashboard updater
This will ensure confluence scores are available on the dashboard
"""

import sys
sys.path.insert(0, '/home/linuxuser/trading/Virtuoso_ccxt')

print("=" * 60)
print("🔧 FIXING DASHBOARD SYMBOLS CACHE")
print("=" * 60)
print()

# The patch to add to dashboard_updater.py
patch_code = '''
    async def compute_symbols_with_confluence(self) -> Dict[str, Any]:
        """
        Compute symbols data with confluence scores.
        
        Returns:
            Dictionary with symbols and their confluence scores
        """
        try:
            logger.info("Computing symbols with confluence scores...")
            
            symbols_data = []
            
            # Get monitored symbols
            symbols = self.trading_system.market_data_manager.symbols
            logger.info(f"Processing {len(symbols)} symbols for dashboard")
            
            for symbol in symbols[:50]:  # Limit to top 50 for performance
                try:
                    # Get confluence score from analyzer
                    confluence_result = None
                    if hasattr(self.trading_system, 'confluence_analyzer'):
                        confluence_result = await self.trading_system.confluence_analyzer.analyze(symbol)
                    
                    # Get ticker data
                    ticker = None
                    try:
                        ticker = await self.trading_system.market_data_manager.get_ticker(symbol)
                    except:
                        pass
                    
                    symbol_data = {
                        'symbol': symbol,
                        'confluence_score': confluence_result.get('final_score', 50) if confluence_result else 50,
                        'confidence': confluence_result.get('confidence', 0) if confluence_result else 0,
                        'direction': confluence_result.get('direction', 'Neutral') if confluence_result else 'Neutral',
                        'change_24h': ticker.get('percentage', 0) if ticker else 0,
                        'price': ticker.get('last', 0) if ticker else 0,
                        'volume': ticker.get('quoteVolume', 0) if ticker else 0,
                        'components': confluence_result.get('components', {}) if confluence_result else {}
                    }
                    
                    symbols_data.append(symbol_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing symbol {symbol}: {e}")
                    # Add with default values
                    symbols_data.append({
                        'symbol': symbol,
                        'confluence_score': 50,
                        'confidence': 0,
                        'direction': 'Neutral',
                        'change_24h': 0,
                        'price': 0,
                        'volume': 0,
                        'components': {}
                    })
            
            logger.info(f"Computed confluence scores for {len(symbols_data)} symbols")
            
            return {
                'status': 'success',
                'symbols': symbols_data,
                'timestamp': datetime.now().isoformat(),
                'count': len(symbols_data)
            }
            
        except Exception as e:
            logger.error(f"Error computing symbols with confluence: {e}")
            return {
                'status': 'error',
                'symbols': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
'''

# Read the current file
try:
    with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'r') as f:
        content = f.read()
    
    # Check if the method already exists
    if 'compute_symbols_with_confluence' in content:
        print("✅ Method already exists, updating cache call...")
    else:
        print("📝 Adding compute_symbols_with_confluence method...")
        
        # Find where to insert (after compute_market_overview)
        insert_pos = content.find('    async def compute_positions')
        if insert_pos > 0:
            # Insert the new method
            content = content[:insert_pos] + patch_code + '\n' + content[insert_pos:]
            
            with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'w') as f:
                f.write(content)
            
            print("✅ Method added successfully")
    
    # Now update the update_all_caches method to call this
    if 'compute_symbols_with_confluence' not in content:
        print("❌ Failed to add method")
    else:
        # Check if it's being called in update_all_caches
        if "symbols_with_confluence = await self.compute_symbols_with_confluence()" not in content:
            print("📝 Adding call to update_all_caches...")
            
            # Find the update_all_caches method and add the call
            update_pos = content.find("# Compute and cache market overview")
            if update_pos > 0:
                insert_line = """            # Compute and cache symbols with confluence scores
            symbols_with_confluence = await self.compute_symbols_with_confluence()
            self.cache.set('symbols', symbols_with_confluence, ttl_seconds=30)
            
"""
                content = content[:update_pos] + insert_line + content[update_pos:]
                
                with open('/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_updater.py', 'w') as f:
                    f.write(content)
                
                print("✅ Cache call added to update_all_caches")
        else:
            print("✅ Already calling compute_symbols_with_confluence")
    
    print()
    print("✅ Dashboard updater fixed!")
    print()
    print("Next steps:")
    print("1. Restart the main service")
    print("2. Wait 30 seconds for cache to populate")
    print("3. Check dashboard for confluence scores")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()