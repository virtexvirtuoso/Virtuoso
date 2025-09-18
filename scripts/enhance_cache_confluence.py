#!/usr/bin/env python3
"""Enhance DashboardCacheManager to include confluence scores"""

enhanced_code = '''"""
Dashboard Cache Manager - Enhanced with Confluence Integration
Handles data flow from main service to all dashboard endpoints
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional
import aiomcache

logger = logging.getLogger(__name__)

class DashboardCacheManager:
    """Manages cache data for all dashboard types - Enhanced with Confluence"""
    
    def __init__(self):
        self.client = None
        self.connected = False
        self._connection_lock = asyncio.Lock()
        self._last_push = 0
        
    async def connect(self):
        """Connect to Memcached with robust error handling"""
        async with self._connection_lock:
            if self.connected and self.client:
                # Test existing connection
                try:
                    await self.client.set(b'test:heartbeat', b'ok', exptime=1)
                    return True
                except:
                    # Connection failed, recreate
                    self.connected = False
                    self.client = None
                
            try:
                # Create fresh client
                self.client = aiomcache.Client('localhost', 11211, pool_size=4)
                
                # Test connection
                await self.client.set(b'test:connection', b'ok', exptime=1)
                test = await self.client.get(b'test:connection')
                
                if test == b'ok':
                    self.connected = True
                    logger.info("✅ Dashboard Cache Manager connected to Memcached")
                    return True
                else:
                    raise Exception("Connection test failed")
                    
            except Exception as e:
                logger.error(f"❌ Failed to connect to Memcached: {e}")
                self.connected = False
                self.client = None
                return False
    
    def _get_confluence_scores(self) -> Dict[str, Dict[str, Any]]:
        """Get confluence scores from DashboardIntegration service"""
        try:
            # Try to get the global DashboardIntegration instance
            import sys
            
            # Look for dashboard integration in various places
            confluence_data = {}
            
            # Method 1: Check if it's in the main module
            if 'src.main' in sys.modules:
                main_module = sys.modules['src.main']
                if hasattr(main_module, 'app') and hasattr(main_module.app, 'state'):
                    # Look for dashboard integration in app state
                    for attr_name in dir(main_module.app.state):
                        attr_value = getattr(main_module.app.state, attr_name, None)
                        if attr_value and hasattr(attr_value, '_confluence_cache'):
                            confluence_cache = getattr(attr_value, '_confluence_cache', {})
                            current_time = time.time()
                            
                            # Extract valid confluence scores (not older than 5 minutes)
                            for symbol, data in confluence_cache.items():
                                if isinstance(data, dict) and 'timestamp' in data:
                                    age = current_time - data['timestamp']
                                    if age < 300:  # 5 minutes
                                        confluence_data[symbol] = {
                                            'score': data.get('score', 50),
                                            'components': data.get('components', {}),
                                            'timestamp': data.get('timestamp', current_time),
                                            'age': age
                                        }
                            
                            if confluence_data:
                                logger.debug(f"Found {len(confluence_data)} confluence scores from dashboard integration")
                                break
            
            # Method 2: Check global variables (fallback)
            if not confluence_data:
                for module_name in sys.modules:
                    if 'dashboard_integration' in module_name:
                        module = sys.modules[module_name]
                        for attr_name in dir(module):
                            attr_value = getattr(module, attr_name, None)
                            if attr_value and hasattr(attr_value, '_confluence_cache'):
                                confluence_cache = getattr(attr_value, '_confluence_cache', {})
                                current_time = time.time()
                                
                                for symbol, data in confluence_cache.items():
                                    if isinstance(data, dict) and 'timestamp' in data:
                                        age = current_time - data['timestamp']
                                        if age < 300:  # 5 minutes
                                            confluence_data[symbol] = {
                                                'score': data.get('score', 50),
                                                'components': data.get('components', {}),
                                                'timestamp': data.get('timestamp', current_time),
                                                'age': age
                                            }
                                
                                if confluence_data:
                                    logger.debug(f"Found {len(confluence_data)} confluence scores from module {module_name}")
                                    break
            
            return confluence_data
            
        except Exception as e:
            logger.debug(f"Could not access confluence scores: {e}")
            return {}
    
    async def push_complete_market_data(self, market_data: Dict[str, Any]):
        """Push comprehensive market data for all dashboards with confluence scores"""
        # Rate limiting - don't push more than once per 10 seconds
        now = time.time()
        if now - self._last_push < 10:
            logger.debug("Rate limiting cache push")
            return True
            
        # Ensure connection
        if not await self.connect():
            logger.error("Cannot push data - not connected to cache")
            return False
            
        try:
            timestamp = int(time.time())
            symbols_list = market_data.get('symbols', [])
            
            if not symbols_list:
                logger.warning("No symbols data to push to cache")
                return False
            
            # Get confluence scores
            confluence_scores = self._get_confluence_scores()
            logger.debug(f"Retrieved {len(confluence_scores)} confluence scores")
            
            # 1. Market Overview (used by all dashboards)
            total_volume = sum(s.get('volume_24h', s.get('volume', 0)) for s in symbols_list)
            total_change = sum(s.get('change_24h', 0) for s in symbols_list)
            avg_change = total_change / max(len(symbols_list), 1)
            
            overview = {
                "total_symbols": len(symbols_list),
                "total_volume": total_volume,
                "total_volume_24h": total_volume,
                "average_change": avg_change,
                "volatility": abs(avg_change) * 0.5,  # Simple volatility estimate
                "timestamp": timestamp
            }
            
            # Use longer expiration (5 minutes) and handle set errors
            try:
                result = await self.client.set(b'market:overview', json.dumps(overview).encode(), exptime=300)
                if result:
                    logger.debug(f"✓ Pushed market overview: {len(symbols_list)} symbols")
                else:
                    logger.warning("Failed to set market:overview")
            except Exception as e:
                logger.error(f"Error setting market:overview: {e}")
                return False
            
            # 2. Tickers (as dict for compatibility) WITH CONFLUENCE SCORES
            tickers_dict = {}
            for symbol_data in symbols_list[:50]:  # Limit to 50 symbols
                symbol = symbol_data.get('symbol', '')
                if symbol:
                    ticker_data = {
                        'price': symbol_data.get('price', 0),
                        'change_24h': symbol_data.get('change_24h', 0),
                        'volume_24h': symbol_data.get('volume_24h', symbol_data.get('volume', 0)),
                        'signal': self._derive_signal(symbol_data.get('change_24h', 0))
                    }
                    
                    # Add confluence score if available
                    if symbol in confluence_scores:
                        confluence_data = confluence_scores[symbol]
                        ticker_data['confluence_score'] = confluence_data['score']
                        ticker_data['confluence_components'] = confluence_data.get('components', {})
                        ticker_data['confluence_age'] = confluence_data.get('age', 0)
                    else:
                        ticker_data['confluence_score'] = 50  # Default neutral score
                    
                    tickers_dict[symbol] = ticker_data
            
            try:
                result = await self.client.set(b'market:tickers', json.dumps(tickers_dict).encode(), exptime=300)
                if result:
                    confluence_count = len([t for t in tickers_dict.values() if t.get('confluence_score', 50) != 50])
                    logger.debug(f"✓ Pushed tickers: {len(tickers_dict)} symbols ({confluence_count} with confluence)")
            except Exception as e:
                logger.error(f"Error setting market:tickers: {e}")
            
            # 3. Enhanced Signals with Confluence Scores
            try:
                signals_list = []
                for symbol_data in symbols_list[:20]:  # Top 20 signals
                    symbol = symbol_data.get('symbol', '')
                    if symbol:
                        signal_data = {
                            "symbol": symbol,
                            "signal": self._derive_signal(symbol_data.get('change_24h', 0)),
                            "confidence": min(abs(symbol_data.get('change_24h', 0)) * 10, 100),
                            "price": symbol_data.get('price', 0),
                            "change_24h": symbol_data.get('change_24h', 0)
                        }
                        
                        # Add confluence data if available
                        if symbol in confluence_scores:
                            confluence_data = confluence_scores[symbol]
                            signal_data['confluence_score'] = confluence_data['score']
                            signal_data['confluence_signal'] = self._derive_confluence_signal(confluence_data['score'])
                            signal_data['confluence_components'] = confluence_data.get('components', {})
                        else:
                            signal_data['confluence_score'] = 50
                            signal_data['confluence_signal'] = 'neutral'
                        
                        signals_list.append(signal_data)
                
                signals_summary = {
                    "signals": signals_list,
                    "total_count": len(signals_list),
                    "confluence_count": len([s for s in signals_list if s.get('confluence_score', 50) != 50]),
                    "timestamp": timestamp
                }
                
                await self.client.set(b'analysis:signals', json.dumps(signals_summary).encode(), exptime=300)
                logger.debug(f"✓ Pushed enhanced signals: {len(signals_list)} signals with confluence")
            except Exception as e:
                logger.error(f"Error setting analysis:signals: {e}")
            
            # 4. Dedicated Confluence Scores Cache
            if confluence_scores:
                try:
                    confluence_summary = {
                        "confluence_scores": [
                            {
                                "symbol": symbol,
                                "score": data['score'],
                                "signal": self._derive_confluence_signal(data['score']),
                                "components": data.get('components', {}),
                                "age": data.get('age', 0),
                                "timestamp": data.get('timestamp', timestamp)
                            }
                            for symbol, data in confluence_scores.items()
                        ],
                        "total_count": len(confluence_scores),
                        "timestamp": timestamp
                    }
                    
                    await self.client.set(b'analysis:confluence', json.dumps(confluence_summary).encode(), exptime=300)
                    logger.debug(f"✓ Pushed confluence summary: {len(confluence_scores)} scores")
                except Exception as e:
                    logger.error(f"Error setting analysis:confluence: {e}")
            
            # 5. Movers (enhanced with confluence)
            try:
                sorted_by_change = sorted(symbols_list, key=lambda x: x.get('change_24h', 0))
                
                gainers = sorted_by_change[-5:] if len(sorted_by_change) >= 5 else sorted_by_change
                losers = sorted_by_change[:5] if len(sorted_by_change) >= 5 else []
                
                # Add confluence scores to movers
                for mover_list in [gainers, losers]:
                    for mover in mover_list:
                        symbol = mover.get('symbol', '')
                        if symbol in confluence_scores:
                            mover['confluence_score'] = confluence_scores[symbol]['score']
                        else:
                            mover['confluence_score'] = 50
                
                movers = {"gainers": gainers, "losers": losers}
                await self.client.set(b'market:movers', json.dumps(movers).encode(), exptime=300)
                logger.debug("✓ Pushed market movers with confluence")
            except Exception as e:
                logger.error(f"Error setting market:movers: {e}")
            
            # 6. Market regime
            try:
                regime = "bullish" if avg_change > 1 else "bearish" if avg_change < -1 else "neutral"
                await self.client.set(b'analysis:market_regime', regime.encode(), exptime=300)
                logger.debug(f"✓ Pushed market regime: {regime}")
            except Exception as e:
                logger.error(f"Error setting analysis:market_regime: {e}")
            
            # 7. Volume leaders (enhanced with confluence)
            try:
                sorted_by_volume = sorted(symbols_list, key=lambda x: x.get('volume_24h', x.get('volume', 0)), reverse=True)
                volume_leaders = sorted_by_volume[:10]
                
                # Add confluence scores
                for leader in volume_leaders:
                    symbol = leader.get('symbol', '')
                    if symbol in confluence_scores:
                        leader['confluence_score'] = confluence_scores[symbol]['score']
                    else:
                        leader['confluence_score'] = 50
                
                await self.client.set(b'market:volume_leaders', json.dumps(volume_leaders).encode(), exptime=300)
                logger.debug("✓ Pushed volume leaders with confluence")
            except Exception as e:
                logger.error(f"Error setting market:volume_leaders: {e}")
            
            self._last_push = now
            confluence_summary = f" (with {len(confluence_scores)} confluence scores)" if confluence_scores else ""
            logger.info(f"✅ Pushed comprehensive market data: {len(symbols_list)} symbols{confluence_summary}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error pushing market data to cache: {e}")
            # Reset connection on error
            self.connected = False
            self.client = None
            return False
    
    def _derive_signal(self, change_24h: float) -> str:
        """Derive trading signal from price change"""
        if change_24h > 3:
            return "strong_buy"
        elif change_24h > 1:
            return "buy"
        elif change_24h < -3:
            return "strong_sell"
        elif change_24h < -1:
            return "sell"
        else:
            return "neutral"
    
    def _derive_confluence_signal(self, score: float) -> str:
        """Derive signal from confluence score"""
        if score >= 75:
            return "strong_buy"
        elif score >= 65:
            return "buy"
        elif score >= 55:
            return "weak_buy"
        elif score <= 25:
            return "strong_sell"
        elif score <= 35:
            return "sell"
        elif score <= 45:
            return "weak_sell"
        else:
            return "neutral"
    
    async def get_cache_data(self, key: str) -> Any:
        """Get data from cache"""
        if not await self.connect():
            return None
            
        try:
            data = await self.client.get(key.encode())
            if data:
                if key == 'analysis:market_regime':
                    return data.decode()
                return json.loads(data.decode())
            return None
        except Exception as e:
            logger.debug(f"Cache read error for {key}: {e}")
            return None

# Singleton instance
dashboard_cache = DashboardCacheManager()
'''

print("Creating enhanced DashboardCacheManager with confluence integration...")

with open('dashboard_cache_manager_enhanced.py', 'w') as f:
    f.write(enhanced_code)

print("\n✅ Enhanced DashboardCacheManager created!")
print("\nKey enhancements:")
print("- 🎯 Automatically detects and retrieves confluence scores from DashboardIntegration")
print("- 📊 Adds confluence_score to all ticker data")
print("- 🚀 Enhanced signals with confluence information")
print("- 📈 Dedicated confluence cache key (analysis:confluence)")
print("- 🔄 Confluence-enhanced movers and volume leaders")
print("- 🎨 Confluence signal derivation (strong_buy, buy, neutral, etc.)")
print("\nNew cache keys:")
print("- analysis:confluence (dedicated confluence scores)")
print("- Enhanced market:tickers (with confluence_score field)")
print("- Enhanced analysis:signals (with confluence data)")
print("\nTo deploy:")
print("scp dashboard_cache_manager_enhanced.py linuxuser@${VPS_HOST}:/home/linuxuser/trading/Virtuoso_ccxt/src/core/dashboard_cache_manager.py")