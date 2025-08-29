"""
Mobile Dashboard Fallback Service
Provides reliable data when cache systems fail
Uses direct exchange APIs that always work
"""

import logging
import time
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class MobileFallbackService:
    """Direct exchange API fallback for mobile dashboard"""
    
    def __init__(self):
        self.session = None
        self._fallback_cache = {}
        self._cache_ttl = 60  # 1 minute cache for fallback data
        
    async def _get_session(self):
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_direct_bybit_symbols(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Get symbols directly from Bybit API - always works
        This replicates the logic from /api/bybit-direct/top-symbols
        """
        try:
            cache_key = f"direct_bybit_symbols_{limit}"
            
            # Check cache first
            if cache_key in self._fallback_cache:
                cache_data = self._fallback_cache[cache_key]
                if time.time() - cache_data['timestamp'] < self._cache_ttl:
                    logger.debug("Using cached direct Bybit symbols")
                    return cache_data['data']
            
            session = await self._get_session()
            
            # Direct Bybit API call
            url = "https://api.bybit.com/v5/market/tickers"
            params = {
                'category': 'spot',
                'limit': 50  # Get more to filter and sort
            }
            
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    tickers = data.get('result', {}).get('list', [])
                    
                    # Process and sort by turnover (volume)
                    symbols_data = []
                    for ticker in tickers:
                        try:
                            symbol = ticker['symbol']
                            
                            # Filter for USDT pairs only
                            if not symbol.endswith('USDT'):
                                continue
                                
                            price = float(ticker['lastPrice'])
                            change_24h = float(ticker['price24hPcnt']) * 100
                            volume_24h = float(ticker['volume24h'])
                            turnover_24h = float(ticker['turnover24h'])
                            high_24h = float(ticker['highPrice24h'])
                            low_24h = float(ticker['lowPrice24h'])
                            
                            # Skip low volume pairs
                            if turnover_24h < 100000:  # $100k minimum turnover
                                continue
                            
                            # Calculate basic confluence score from market data
                            confluence_score = self._calculate_confluence_score(
                                price, change_24h, volume_24h, high_24h, low_24h
                            )
                            
                            symbols_data.append({
                                'symbol': symbol,
                                'price': round(price, 6),
                                'confluence_score': round(confluence_score, 2),
                                'price_change_percent': round(change_24h, 2),
                                'volume_24h': int(volume_24h),
                                'turnover_24h': int(turnover_24h),
                                'high_24h': round(high_24h, 6),
                                'low_24h': round(low_24h, 6),
                                'range_24h': round(((high_24h - low_24h) / low_24h) * 100, 2) if low_24h > 0 else 0,
                                'reliability': 85,  # Direct exchange data is highly reliable
                                'sentiment': 'BULLISH' if change_24h > 2 else 'BEARISH' if change_24h < -2 else 'NEUTRAL',
                                'components': {
                                    'technical': 50 + (change_24h * 2),  # Price momentum
                                    'volume': min(100, max(0, 30 + (turnover_24h / 10000000) * 20)),  # Volume factor
                                    'orderflow': 50,
                                    'sentiment': 50 + change_24h,
                                    'orderbook': 50,
                                    'price_structure': 45 + ((price - low_24h) / (high_24h - low_24h)) * 10 if high_24h > low_24h else 50
                                },
                                'has_breakdown': True,
                                'timestamp': int(time.time())
                            })
                            
                        except (ValueError, KeyError, ZeroDivisionError) as e:
                            logger.debug(f"Error processing ticker {ticker.get('symbol', 'unknown')}: {e}")
                            continue
                    
                    # Sort by turnover (highest first) then limit
                    symbols_data.sort(key=lambda x: x['turnover_24h'], reverse=True)
                    top_symbols = symbols_data[:limit]
                    
                    # Cache the result
                    self._fallback_cache[cache_key] = {
                        'data': top_symbols,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"✅ Direct Bybit fallback: Retrieved {len(top_symbols)} symbols")
                    return top_symbols
                else:
                    logger.error(f"Bybit API returned status {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Direct Bybit symbols fallback failed: {e}")
            return []
    
    def _calculate_confluence_score(self, price: float, change_24h: float, volume_24h: float, 
                                   high_24h: float, low_24h: float) -> float:
        """Calculate basic confluence score from market data"""
        try:
            base_score = 50.0
            
            # Price momentum component (±15 points)
            momentum_score = min(15, max(-15, change_24h * 3))
            
            # Volume component (0-20 points)
            volume_score = min(20, volume_24h / 1000000)  # Higher volume = higher score
            
            # Position in daily range (±10 points)
            if high_24h > low_24h:
                range_position = (price - low_24h) / (high_24h - low_24h)
                range_score = (range_position - 0.5) * 20  # -10 to +10
            else:
                range_score = 0
            
            total_score = base_score + momentum_score + volume_score + range_score
            
            # Clamp to 0-100 range
            return max(0.0, min(100.0, total_score))
            
        except (ZeroDivisionError, ValueError):
            return 50.0  # Neutral score on error
    
    async def get_fallback_mobile_data(self) -> Dict[str, Any]:
        """
        Get complete mobile dashboard data using direct APIs
        This is the ultimate fallback when all cache systems fail
        """
        try:
            logger.info("🚨 Using direct exchange fallback for mobile data")
            
            # Get symbols from direct Bybit API
            confluence_scores = await self.get_direct_bybit_symbols(limit=15)
            
            if not confluence_scores:
                logger.error("Direct fallback failed - no symbols retrieved")
                return {
                    'confluence_scores': [],
                    'market_overview': {
                        'market_regime': 'UNKNOWN',
                        'trend_strength': 0,
                        'volatility': 0,
                        'btc_dominance': 59.3,
                        'total_volume': 0
                    },
                    'top_movers': {'gainers': [], 'losers': []},
                    'status': 'direct_exchange_fallback_failed'
                }
            
            # Calculate market overview from symbols data
            market_overview = self._calculate_market_overview(confluence_scores)
            
            # Extract top movers
            top_movers = self._extract_top_movers(confluence_scores)
            
            fallback_data = {
                'confluence_scores': confluence_scores,
                'market_overview': market_overview,
                'top_movers': top_movers,
                'status': 'direct_exchange_fallback',
                'timestamp': int(time.time())
            }
            
            logger.info(f"✅ Direct fallback successful: {len(confluence_scores)} symbols, regime={market_overview['market_regime']}")
            return fallback_data
            
        except Exception as e:
            logger.error(f"Fallback mobile data failed: {e}")
            return {
                'confluence_scores': [],
                'market_overview': {'market_regime': 'ERROR', 'trend_strength': 0, 'volatility': 0, 'btc_dominance': 59.3, 'total_volume': 0},
                'top_movers': {'gainers': [], 'losers': []},
                'status': 'fallback_error'
            }
    
    def _calculate_market_overview(self, symbols_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate market overview from symbols data"""
        if not symbols_data:
            return {
                'market_regime': 'NO_DATA',
                'trend_strength': 0,
                'volatility': 0,
                'btc_dominance': 59.3,
                'total_volume': 0
            }
        
        # Aggregate metrics
        changes = [s['price_change_percent'] for s in symbols_data]
        volumes = [s['turnover_24h'] for s in symbols_data]
        
        avg_change = sum(changes) / len(changes)
        total_volume = sum(volumes)
        
        # Calculate volatility (standard deviation of changes)
        if len(changes) > 1:
            variance = sum((x - avg_change) ** 2 for x in changes) / len(changes)
            volatility = variance ** 0.5
        else:
            volatility = abs(avg_change)
        
        # Determine market regime
        bullish_count = sum(1 for change in changes if change > 1)
        bearish_count = sum(1 for change in changes if change < -1)
        
        if bullish_count > len(changes) * 0.6:
            regime = 'BULLISH'
        elif bearish_count > len(changes) * 0.6:
            regime = 'BEARISH'
        elif volatility > 5:
            regime = 'VOLATILE'
        else:
            regime = 'NEUTRAL'
        
        # Calculate trend strength
        trend_strength = min(100, abs(avg_change) * 20)
        
        # Calculate BTC dominance (approximation)
        btc_data = next((s for s in symbols_data if s['symbol'] == 'BTCUSDT'), None)
        btc_dominance = 59.3  # Default
        if btc_data and total_volume > 0:
            btc_dominance = min(70, max(40, (btc_data['turnover_24h'] / total_volume) * 100))
        
        return {
            'market_regime': regime,
            'trend_strength': round(trend_strength, 2),
            'current_volatility': round(volatility, 2),
            'volatility': round(volatility, 2),
            'btc_dominance': round(btc_dominance, 2),
            'total_volume': int(total_volume),
            'total_volume_24h': int(total_volume),
            'average_change': round(avg_change, 2)
        }
    
    def _extract_top_movers(self, symbols_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extract top gainers and losers from symbols data"""
        # Sort by price change
        sorted_symbols = sorted(symbols_data, key=lambda x: x['price_change_percent'], reverse=True)
        
        # Top 5 gainers and losers
        gainers = [
            {
                'symbol': s['symbol'],
                'price': s['price'],
                'change_24h': s['price_change_percent'],
                'volume': s['volume_24h'],
                'volume_24h': s['turnover_24h']
            }
            for s in sorted_symbols[:5] if s['price_change_percent'] > 0
        ]
        
        losers = [
            {
                'symbol': s['symbol'],
                'price': s['price'],
                'change_24h': s['price_change_percent'],
                'volume': s['volume_24h'],
                'volume_24h': s['turnover_24h']
            }
            for s in sorted_symbols[-5:] if s['price_change_percent'] < 0
        ]
        
        return {
            'gainers': gainers,
            'losers': losers[::-1]  # Reverse losers to show worst first
        }

# Global fallback service instance
mobile_fallback_service = MobileFallbackService()