#!/usr/bin/env python3
"""
Cache Bridge Dashboard Data Fix
Fixes the cache bridge initialization and data flow issues causing zero dashboard data.

Root Cause: Cache bridge not properly initialized with required components,
resulting in no data being aggregated into expected cache keys.

This fix ensures:
1. Bridge dependencies are properly injected
2. Bridge loop runs reliably every 30 seconds  
3. Fallback mechanisms work when primary data sources fail
4. Cache keys match between readers and writers
"""

import asyncio
import logging
import sys
import os

# Add project root to Python path
sys.path.insert(0, '/Users/ffv_macmini/Desktop/Virtuoso_ccxt')

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class CacheBridgeFix:
    """Fix cache bridge data flow issues"""
    
    def __init__(self):
        self.fixes_applied = []
    
    async def diagnose_current_state(self):
        """Diagnose current cache bridge state on VPS"""
        logger.info("🔍 Diagnosing cache bridge state...")
        
        issues = []
        
        # Test cache connectivity
        try:
            import aiomcache
            client = aiomcache.Client('5.223.63.4', 11211)
            
            # Check expected cache keys
            cache_keys = ['analysis:signals', 'market:overview', 'market:movers', 'market:tickers']
            key_status = {}
            
            for key in cache_keys:
                try:
                    data = await client.get(key.encode())
                    if data:
                        key_status[key] = f"Found ({len(data)} bytes)"
                    else:
                        key_status[key] = "Missing"
                        issues.append(f"Cache key '{key}' is empty")
                except Exception as e:
                    key_status[key] = f"Error: {e}"
                    issues.append(f"Cache key '{key}' access error: {e}")
            
            await client.close()
            
            logger.info("Cache Key Status:")
            for key, status in key_status.items():
                logger.info(f"  {key}: {status}")
                
        except Exception as e:
            issues.append(f"Cache connectivity error: {e}")
            logger.error(f"❌ Cache connectivity failed: {e}")
        
        return issues
    
    def create_bridge_initialization_fix(self):
        """Create fixed bridge initialization code"""
        
        fix_code = '''
# FIXED: Cache Bridge Initialization (add to main.py around line 892)
async def start_cache_bridge_with_dependencies():
    """Initialize cache bridge with proper dependency injection"""
    await asyncio.sleep(5)  # Wait for components to be ready
    try:
        from src.core.cache_data_bridge import cache_data_bridge
        
        # Get component references from app state
        components_needed = []
        
        # Market Data Manager
        if hasattr(app.state, 'market_data_manager') and app.state.market_data_manager:
            cache_data_bridge.set_market_data_manager(app.state.market_data_manager)
            components_needed.append("MarketDataManager")
            logger.info("✅ Cache bridge configured with MarketDataManager")
        else:
            logger.warning("⚠️ MarketDataManager not available for cache bridge")
        
        # Dashboard Integration Service  
        dashboard_integration = globals().get('dashboard_integration')
        if dashboard_integration:
            cache_data_bridge.set_dashboard_integration(dashboard_integration)
            components_needed.append("DashboardIntegration")
            logger.info("✅ Cache bridge configured with DashboardIntegration")
        else:
            logger.warning("⚠️ DashboardIntegration not available for cache bridge")
        
        # Confluence Analyzer
        if hasattr(app.state, 'confluence_analyzer') and app.state.confluence_analyzer:
            cache_data_bridge.set_confluence_analyzer(app.state.confluence_analyzer)
            components_needed.append("ConfluenceAnalyzer")
            logger.info("✅ Cache bridge configured with ConfluenceAnalyzer")
        else:
            logger.warning("⚠️ ConfluenceAnalyzer not available for cache bridge")
        
        # Start bridge even if some components are missing (fallbacks will handle it)
        if len(components_needed) > 0:
            logger.info(f"🚀 Starting cache bridge with components: {', '.join(components_needed)}")
            
            # Start the bridge loop in background task
            bridge_task = asyncio.create_task(cache_data_bridge.start_bridge_loop(interval=30))
            logger.info("✅ Cache data bridge started with proper dependency injection!")
            
            # Store task reference for cleanup
            app.state.cache_bridge_task = bridge_task
            app.state.cache_data_bridge = cache_data_bridge
            
        else:
            logger.error("❌ Cannot start cache bridge - no components available")
            
            # Start minimal bridge with direct exchange fallback only
            logger.info("🔄 Starting cache bridge in fallback mode...")
            bridge_task = asyncio.create_task(cache_data_bridge.start_bridge_loop(interval=30))
            app.state.cache_bridge_task = bridge_task
            
    except Exception as e:
        logger.error(f"❌ Failed to start cache bridge: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Replace the existing bridge startup with this call:
asyncio.create_task(start_cache_bridge_with_dependencies())
'''
        
        return fix_code
    
    def create_bridge_robustness_fixes(self):
        """Create fixes for bridge robustness"""
        
        fixes = []
        
        # Fix 1: Enhanced error handling in bridge loop
        fix1 = '''
# FIXED: Enhanced Bridge Loop Error Handling (cache_data_bridge.py)
async def start_bridge_loop(self, interval: int = 30):
    """Start the background bridging loop with enhanced error handling"""
    self.running = True
    logger.info(f"Starting cache data bridge (interval: {interval}s)")
    
    # Run immediate first update
    try:
        await self.bridge_monitoring_data()
        logger.info("✅ Initial cache bridge update completed")
    except Exception as e:
        logger.error(f"❌ Initial bridge update failed: {e}")
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while self.running:
        try:
            await asyncio.sleep(interval)
            
            # Bridge monitoring data with timeout
            bridge_task = asyncio.create_task(self.bridge_monitoring_data())
            try:
                await asyncio.wait_for(bridge_task, timeout=20.0)  # 20 second timeout
                consecutive_errors = 0  # Reset error counter on success
                logger.debug(f"✅ Cache bridge cycle completed successfully")
            except asyncio.TimeoutError:
                logger.error("❌ Cache bridge cycle timed out (20s)")
                consecutive_errors += 1
            except Exception as e:
                logger.error(f"❌ Cache bridge cycle failed: {e}")
                consecutive_errors += 1
                
            # If too many consecutive errors, try to restart with fresh connections
            if consecutive_errors >= max_consecutive_errors:
                logger.warning(f"⚠️ {consecutive_errors} consecutive bridge errors, resetting connections...")
                await self._reset_connections()
                consecutive_errors = 0
                
        except asyncio.CancelledError:
            logger.info("Cache data bridge cancelled")
            break
        except Exception as e:
            logger.error(f"❌ Critical error in bridge loop: {e}")
            consecutive_errors += 1
            await asyncio.sleep(5)
            
    logger.info("Cache data bridge stopped")

async def _reset_connections(self):
    """Reset cache connections"""
    try:
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("✅ Cache bridge connections reset")
    except Exception as e:
        logger.error(f"Error resetting connections: {e}")
'''
        fixes.append(("Enhanced Bridge Loop", fix1))
        
        # Fix 2: Improved data fetching with better fallbacks
        fix2 = '''
# FIXED: Improved Signal Data Fetching (cache_data_bridge.py)
async def _bridge_signals_data(self):
    """Bridge signals data with improved fallbacks"""
    try:
        logger.info("🔄 Starting signals data bridge...")
        
        signals_data = None
        data_source = "none"
        
        # Strategy 1: Try dashboard integration service first
        if self.dashboard_integration and hasattr(self.dashboard_integration, 'get_dashboard_data'):
            try:
                real_dashboard_data = await asyncio.wait_for(
                    self.dashboard_integration.get_dashboard_data(), 
                    timeout=10.0
                )
                if real_dashboard_data and 'signals' in real_dashboard_data:
                    signals_data = {
                        'signals': real_dashboard_data['signals'],
                        'timestamp': int(time.time())
                    }
                    data_source = "dashboard_integration"
                    logger.info(f"✅ Got {len(signals_data['signals'])} signals from dashboard integration")
            except Exception as e:
                logger.warning(f"Dashboard integration failed: {e}")
        
        # Strategy 2: Try to get from existing cache with different keys
        if not signals_data:
            cache_keys_to_try = [
                'dashboard:signals', 'signals:latest', 'confluence:scores', 
                'analysis:signals', 'virtuoso:signals'
            ]
            for key in cache_keys_to_try:
                try:
                    data = await self._get_cache(key)
                    if data and isinstance(data, dict) and 'signals' in data and len(data['signals']) > 0:
                        signals_data = data
                        data_source = f"cached_{key}"
                        logger.info(f"✅ Got {len(signals_data['signals'])} signals from cache key {key}")
                        break
                except Exception as e:
                    logger.debug(f"Cache key {key} failed: {e}")
        
        # Strategy 3: Build from real market data
        if not signals_data:
            logger.info("🔄 No cached signals found, building from real market data...")
            signals_data = await self._build_signals_from_market_data()
            if signals_data and len(signals_data.get('signals', [])) > 0:
                data_source = "built_from_market_data"
                logger.info(f"✅ Built {len(signals_data['signals'])} signals from market data")
        
        # Strategy 4: Direct exchange fallback
        if not signals_data:
            logger.info("🔄 Trying direct exchange fallback...")
            signals_data = await self._build_signals_from_direct_exchange()
            if signals_data:
                data_source = "direct_exchange_fallback"
                logger.info(f"✅ Built {len(signals_data.get('signals', []))} signals from direct exchange")
        
        # Store in cache if we have data
        if signals_data and len(signals_data.get('signals', [])) > 0:
            await self._set_cache('analysis:signals', signals_data, ttl=60)
            logger.info(f"✅ Cached {len(signals_data['signals'])} signals from {data_source}")
            
            # Also store individual scores for quick access
            for signal in signals_data.get('signals', []):
                symbol = signal.get('symbol')
                score = signal.get('score')
                if symbol and score is not None:
                    await self._set_cache(f'confluence:score:{symbol}', score, ttl=120)
        else:
            # Store empty but valid structure
            empty_signals = {
                'signals': [],
                'count': 0,
                'timestamp': int(time.time()),
                'status': 'no_data_available',
                'attempted_sources': data_source
            }
            await self._set_cache('analysis:signals', empty_signals, ttl=30)
            logger.warning(f"⚠️ Stored empty signals data - attempted: {data_source}")
            
    except Exception as e:
        logger.error(f"❌ Error bridging signals data: {e}")
        import traceback
        logger.error(traceback.format_exc())
'''
        fixes.append(("Improved Signal Data Fetching", fix2))
        
        return fixes
    
    def create_direct_exchange_fallback_fix(self):
        """Create direct exchange fallback method"""
        
        fix_code = '''
# FIXED: Direct Exchange Fallback Implementation (cache_data_bridge.py)
async def _build_signals_from_direct_exchange(self) -> Dict[str, Any]:
    """Build signals directly from exchange API as ultimate fallback"""
    try:
        import aiohttp
        import json
        
        logger.info("🔄 Fetching data directly from Bybit API...")
        
        async with aiohttp.ClientSession() as session:
            # Get top 15 symbols by volume from Bybit
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Bybit API error: {response.status}")
                    return None
                
                data = await response.json()
                
                if data.get('retCode') != 0:
                    logger.error(f"Bybit API returned error: {data}")
                    return None
                
                tickers = data['result']['list']
                
                # Process and sort by volume
                symbols_data = []
                for ticker in tickers:
                    try:
                        symbol = ticker['symbol']
                        if not symbol.endswith('USDT') or 'PERP' in symbol:
                            continue
                            
                        price = float(ticker['lastPrice'])
                        change_24h = float(ticker['price24hPcnt']) * 100
                        volume_24h = float(ticker['volume24h'])
                        turnover_24h = float(ticker['turnover24h'])
                        high = float(ticker['highPrice24h'])
                        low = float(ticker['lowPrice24h'])
                        
                        # Skip symbols with very low turnover
                        if turnover_24h < 1000000:  # $1M minimum
                            continue
                        
                        # Calculate basic confluence score from market data
                        base_score = 50.0
                        
                        # Price position in daily range
                        if high > low:
                            range_position = (price - low) / (high - low)
                            base_score += (range_position - 0.5) * 20
                        
                        # Volume boost
                        if turnover_24h > 50000000:  # $50M+
                            base_score += 10
                        elif turnover_24h > 10000000:  # $10M+
                            base_score += 5
                        
                        # Momentum from change
                        if abs(change_24h) > 5:
                            base_score += 5 if change_24h > 0 else -5
                        
                        score = max(0.0, min(100.0, base_score))
                        
                        symbols_data.append({
                            'symbol': symbol,
                            'price': price,
                            'change_24h': change_24h,
                            'volume': volume_24h,
                            'turnover': turnover_24h,
                            'score': score
                        })
                        
                    except (ValueError, KeyError) as e:
                        continue
                
                # Sort by turnover and take top 15
                symbols_data.sort(key=lambda x: x['turnover'], reverse=True)
                top_symbols = symbols_data[:15]
                
                # Format as signals
                signals = []
                for item in top_symbols:
                    signal = {
                        'symbol': item['symbol'],
                        'score': round(item['score'], 2),
                        'price': round(item['price'], 6),
                        'change_24h': round(item['change_24h'], 2),
                        'volume': int(item['volume']),
                        'sentiment': 'BULLISH' if item['change_24h'] > 2 else 'BEARISH' if item['change_24h'] < -2 else 'NEUTRAL',
                        'components': {
                            'technical': round(45 + (item['change_24h'] / 10) * 10, 2),
                            'volume': min(100, max(20, 30 + (item['turnover'] / 1000000) * 2)),
                            'orderflow': round(50 + (item['change_24h'] / 20) * 15, 2),
                            'sentiment': round(50 + (item['change_24h'] / 15) * 20, 2),
                            'orderbook': 50.0,
                            'price_structure': round(40 + ((item['price'] - (item.get('low', item['price']))) / max(item.get('high', item['price']) - item.get('low', item['price']), 1)) * 20, 2) if 'high' in item else 50.0
                        },
                        'timestamp': int(time.time())
                    }
                    signals.append(signal)
                
                logger.info(f"✅ Built {len(signals)} signals from direct Bybit API")
                
                return {
                    'signals': signals,
                    'count': len(signals),
                    'timestamp': int(time.time()),
                    'source': 'direct_bybit_api'
                }
                
    except Exception as e:
        logger.error(f"❌ Direct exchange fallback failed: {e}")
        return None
'''
        
        return fix_code
    
    async def apply_fixes_to_vps(self):
        """Apply fixes to VPS"""
        logger.info("🔧 Preparing to apply cache bridge fixes...")
        
        fixes_to_apply = [
            "Enhanced bridge initialization with proper dependency injection",
            "Improved error handling in bridge loop",
            "Better data fetching with multiple fallback strategies", 
            "Direct exchange API fallback implementation"
        ]
        
        logger.info("Fixes to be applied:")
        for i, fix in enumerate(fixes_to_apply, 1):
            logger.info(f"  {i}. {fix}")
        
        return fixes_to_apply

async def main():
    """Main fix execution"""
    fix = CacheBridgeFix()
    
    # Diagnose current state
    issues = await fix.diagnose_current_state()
    
    if issues:
        logger.error(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            logger.error(f"  - {issue}")
    else:
        logger.info("✅ No critical issues found in cache bridge")
        return
    
    # Generate fixes
    bridge_init_fix = fix.create_bridge_initialization_fix()
    robustness_fixes = fix.create_bridge_robustness_fixes()
    direct_fallback_fix = fix.create_direct_exchange_fallback_fix()
    
    # Save fixes to files for manual application
    with open("bridge_initialization_fix.py", "w") as f:
        f.write(bridge_init_fix)
    
    with open("bridge_robustness_fixes.py", "w") as f:
        f.write("# Cache Bridge Robustness Fixes\\n\\n")
        for name, code in robustness_fixes:
            f.write(f"# {name}\\n{code}\\n\\n")
    
    with open("direct_exchange_fallback_fix.py", "w") as f:
        f.write(direct_fallback_fix)
    
    logger.info("💾 Fix files generated:")
    logger.info("  - bridge_initialization_fix.py")
    logger.info("  - bridge_robustness_fixes.py") 
    logger.info("  - direct_exchange_fallback_fix.py")
    
    # Show what needs to be applied
    fixes_needed = await fix.apply_fixes_to_vps()
    
    logger.info("\\n🚀 NEXT STEPS:")
    logger.info("1. Apply the generated fixes to the VPS codebase")
    logger.info("2. Restart the Virtuoso service: sudo systemctl restart virtuoso.service")
    logger.info("3. Monitor logs: sudo journalctl -u virtuoso.service -f")
    logger.info("4. Test dashboard endpoint: curl http://5.223.63.4:8003/api/dashboard/data")
    
    return fixes_needed

if __name__ == "__main__":
    asyncio.run(main())