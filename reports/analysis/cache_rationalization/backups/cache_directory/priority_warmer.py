"""
Priority-based Cache Warming System
Ensures mobile-critical data loads first during system startup
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PriorityCacheWarmer:
    """
    Intelligent cache warming system that prioritizes mobile dashboard data
    """
    
    def __init__(self, market_monitor=None, cache_adapter=None):
        self.market_monitor = market_monitor
        self.cache_adapter = cache_adapter
        self.warming_active = False
        self.priority_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
            'XRPUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT'
        ]
        self.warming_stats = {
            'start_time': None,
            'priority_complete': False,
            'total_symbols_warmed': 0,
            'priority_symbols_warmed': 0,
            'mobile_ready_time': None
        }
    
    async def warm_mobile_cache(self) -> Dict[str, Any]:
        """
        Warm cache with mobile-priority data first
        Returns mobile data as soon as priority symbols are ready
        """
        if self.warming_active:
            logger.debug("Cache warming already active")
            return await self._get_current_mobile_data()
        
        self.warming_active = True
        self.warming_stats['start_time'] = time.time()
        
        try:
            logger.info("🔥 Starting priority cache warming for mobile dashboard")
            
            # Phase 1: Warm priority symbols (critical mobile data)
            mobile_data = await self._warm_priority_symbols()
            
            if mobile_data and mobile_data.get('confluence_scores'):
                self.warming_stats['mobile_ready_time'] = time.time()
                self.warming_stats['priority_complete'] = True
                elapsed = self.warming_stats['mobile_ready_time'] - self.warming_stats['start_time']
                logger.info(f"🎯 Mobile-priority cache warm complete in {elapsed:.2f}s - {len(mobile_data['confluence_scores'])} symbols ready")
                
                # Continue warming remaining symbols in background
                asyncio.create_task(self._warm_remaining_symbols())
                
                return mobile_data
            
            # Fallback: If priority warming fails, try direct exchange
            logger.warning("Priority cache warming failed - using direct exchange fallback")
            return await self._get_fallback_mobile_data()
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return await self._get_fallback_mobile_data()
        finally:
            # Don't set warming_active = False here, let background task finish
            pass
    
    async def _warm_priority_symbols(self) -> Optional[Dict[str, Any]]:
        """Warm cache with priority symbols first"""
        if not self.market_monitor:
            logger.warning("Market monitor not available for cache warming")
            return None
        
        try:
            # Get current symbols being monitored
            monitored_symbols = getattr(self.market_monitor, 'symbols', [])
            
            if not monitored_symbols:
                logger.warning("No symbols available in market monitor")
                return None
            
            # Find priority symbols that are actually monitored
            available_priority = [s for s in self.priority_symbols if s in monitored_symbols]
            
            if not available_priority:
                logger.warning("No priority symbols found in monitored symbols")
                # Use first 5 available symbols as priority
                available_priority = monitored_symbols[:5]
            
            logger.info(f"Warming priority symbols: {available_priority}")
            
            # Force analysis of priority symbols
            priority_results = []
            for symbol in available_priority:
                try:
                    # Trigger confluence analysis for this symbol
                    if hasattr(self.market_monitor, 'confluence_analyzer'):
                        result = await self._analyze_symbol_priority(symbol)
                        if result:
                            priority_results.append(result)
                            self.warming_stats['priority_symbols_warmed'] += 1
                except Exception as e:
                    logger.debug(f"Failed to warm {symbol}: {e}")
                    continue
            
            if priority_results:
                # Create mobile data structure
                mobile_data = await self._create_mobile_data_from_results(priority_results)
                logger.info(f"✅ Priority warming complete: {len(priority_results)} symbols warmed")
                return mobile_data
            
            return None
            
        except Exception as e:
            logger.error(f"Priority symbol warming failed: {e}")
            return None
    
    async def _analyze_symbol_priority(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Force analysis of a priority symbol"""
        try:
            if not hasattr(self.market_monitor, 'confluence_analyzer'):
                return None
            
            confluence_analyzer = self.market_monitor.confluence_analyzer
            
            # Get market data for the symbol
            if hasattr(self.market_monitor, 'market_data_manager'):
                market_data = await self.market_monitor.market_data_manager.get_ohlcv(symbol)
                if market_data is not None and len(market_data) > 0:
                    # Run confluence analysis
                    analysis_result = await confluence_analyzer.analyze_confluence(symbol, market_data)
                    
                    if analysis_result:
                        # Format for mobile response
                        return {
                            'symbol': symbol,
                            'confluence_score': analysis_result.get('score', 50),
                            'price': float(market_data.iloc[-1]['close']) if len(market_data) > 0 else 0,
                            'price_change_percent': analysis_result.get('price_change_24h', 0),
                            'volume_24h': int(analysis_result.get('volume_24h', 0)),
                            'sentiment': analysis_result.get('sentiment', 'NEUTRAL'),
                            'reliability': 95,  # High reliability from direct analysis
                            'components': analysis_result.get('components', {}),
                            'has_breakdown': True,
                            'timestamp': int(time.time())
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"Symbol analysis failed for {symbol}: {e}")
            return None
    
    async def _create_mobile_data_from_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create mobile data structure from analysis results"""
        
        # Sort by confluence score
        results.sort(key=lambda x: x.get('confluence_score', 0), reverse=True)
        
        # Calculate market overview
        changes = [r.get('price_change_percent', 0) for r in results]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        bullish_count = sum(1 for change in changes if change > 1)
        bearish_count = sum(1 for change in changes if change < -1)
        
        if bullish_count > len(changes) * 0.6:
            regime = 'BULLISH'
        elif bearish_count > len(changes) * 0.6:
            regime = 'BEARISH'
        else:
            regime = 'NEUTRAL'
        
        # Extract top movers
        gainers = [r for r in results if r.get('price_change_percent', 0) > 0][:3]
        losers = [r for r in results if r.get('price_change_percent', 0) < 0][-3:]
        
        return {
            'confluence_scores': results,
            'market_overview': {
                'market_regime': regime,
                'trend_strength': min(100, abs(avg_change) * 20),
                'volatility': 25.0,  # Default volatility
                'btc_dominance': 59.3,
                'total_volume_24h': sum(r.get('volume_24h', 0) for r in results)
            },
            'top_movers': {
                'gainers': [{'symbol': g['symbol'], 'change_24h': g['price_change_percent'], 'price': g['price']} for g in gainers],
                'losers': [{'symbol': l['symbol'], 'change_24h': l['price_change_percent'], 'price': l['price']} for l in losers[::-1]]
            },
            'status': 'priority_cache_warm',
            'timestamp': int(time.time())
        }
    
    async def _warm_remaining_symbols(self):
        """Background task to warm remaining symbols"""
        try:
            if not self.market_monitor:
                return
            
            monitored_symbols = getattr(self.market_monitor, 'symbols', [])
            remaining_symbols = [s for s in monitored_symbols if s not in self.priority_symbols]
            
            logger.info(f"🔄 Warming {len(remaining_symbols)} remaining symbols in background")
            
            for symbol in remaining_symbols:
                try:
                    await self._analyze_symbol_priority(symbol)
                    self.warming_stats['total_symbols_warmed'] += 1
                    await asyncio.sleep(0.1)  # Small delay to prevent overwhelming
                except Exception as e:
                    logger.debug(f"Background warming failed for {symbol}: {e}")
                    continue
            
            logger.info(f"✅ Background cache warming complete: {self.warming_stats['total_symbols_warmed']} total symbols warmed")
            
        except Exception as e:
            logger.error(f"Background warming failed: {e}")
        finally:
            self.warming_active = False
    
    async def _get_current_mobile_data(self) -> Dict[str, Any]:
        """Get current mobile data from cache or analysis"""
        try:
            if self.cache_adapter:
                return await self.cache_adapter.get_mobile_data()
            return await self._get_fallback_mobile_data()
        except Exception:
            return await self._get_fallback_mobile_data()
    
    async def _get_fallback_mobile_data(self) -> Dict[str, Any]:
        """Fallback mobile data when warming fails"""
        from src.api.services.mobile_fallback_service import mobile_fallback_service
        return await mobile_fallback_service.get_fallback_mobile_data()
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics"""
        stats = self.warming_stats.copy()
        if stats['start_time']:
            stats['elapsed_time'] = time.time() - stats['start_time']
        return stats

# Global instance
priority_cache_warmer = PriorityCacheWarmer()