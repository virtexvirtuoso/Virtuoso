"""
Optimized Cache Adapter for Dashboard Data
Uses intelligent retry logic, warming, and comprehensive monitoring
"""
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
from src.core.cache_system import optimized_cache_system, CacheStatus

logger = logging.getLogger(__name__)

class OptimizedCacheAdapter:
    """
    Enhanced cache adapter optimized for dashboard reliability
    
    Features:
    - Intelligent retry logic with exponential backoff
    - Smart cache warming to prevent empty data
    - Circuit breaker pattern for resilience
    - Comprehensive performance monitoring
    - Multi-tier fallback strategies
    - Data validation and sanitization
    """
    
    def __init__(self):
        self.cache_system = optimized_cache_system
        self.fallback_enabled = True
        self.data_validation_enabled = True
        
        # Cache warming triggers
        self._warmup_completed = False
        self._last_warmup_time = 0
        self.warmup_interval = 300  # 5 minutes between warmups
        
    async def _ensure_cache_warm(self) -> bool:
        """Ensure cache is warmed before serving data"""
        current_time = time.time()
        
        # Check if we need to warm the cache
        if (not self._warmup_completed or 
            current_time - self._last_warmup_time > self.warmup_interval):
            
            logger.info("Triggering cache warmup for optimal dashboard performance")
            warmup_results = await self.cache_system.warm_cache()
            
            self._last_warmup_time = current_time
            self._warmup_completed = True
            
            # Check if warmup was successful
            if warmup_results.get('status') != 'not_needed' and warmup_results.get('error'):
                logger.warning(f"Cache warmup had issues: {warmup_results}")
                return False
            
            logger.info("Cache warmup completed successfully")
            return True
        
        return True
    
    def _validate_market_data(self, data: Dict[str, Any], data_type: str) -> bool:
        """Validate that market data is realistic and not corrupted"""
        if not self.data_validation_enabled:
            return True
        
        if not isinstance(data, dict):
            return False
        
        try:
            if data_type == 'overview':
                # Validate market overview data
                symbols = data.get('total_symbols', 0)
                volume = data.get('total_volume', 0)
                
                # Realistic bounds for crypto market
                if symbols < 0 or symbols > 10000:  # Unrealistic symbol count
                    logger.warning(f"Invalid symbol count in overview: {symbols}")
                    return False
                
                if volume < 0 or volume > 1e15:  # Unrealistic volume (>$1 quadrillion)
                    logger.warning(f"Invalid volume in overview: {volume}")
                    return False
                
            elif data_type == 'signals':
                signals = data.get('signals', [])
                if not isinstance(signals, list):
                    return False
                
                # Validate individual signals
                for signal in signals[:5]:  # Check first 5 signals
                    if not isinstance(signal, dict):
                        continue
                    
                    price = signal.get('price', 0)
                    score = signal.get('score', 0)
                    
                    if price < 0 or price > 1e8:  # Unrealistic price
                        logger.warning(f"Invalid price in signal {signal.get('symbol', 'unknown')}: {price}")
                        return False
                    
                    if score < 0 or score > 100:  # Score out of range
                        logger.warning(f"Invalid score in signal {signal.get('symbol', 'unknown')}: {score}")
                        return False
                        
            elif data_type == 'movers':
                gainers = data.get('gainers', [])
                losers = data.get('losers', [])
                
                if not isinstance(gainers, list) or not isinstance(losers, list):
                    return False
                
                # Check for realistic price changes
                for mover in (gainers + losers)[:3]:
                    if not isinstance(mover, dict):
                        continue
                    
                    change = mover.get('change_24h', 0)
                    if abs(change) > 1000:  # >1000% change unrealistic
                        logger.warning(f"Unrealistic change in mover {mover.get('symbol', 'unknown')}: {change}%")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating {data_type} data: {e}")
            return False
    
    async def _get_with_fallback(self, key: str, default: Any = None, data_type: str = None) -> Any:
        """Get data with intelligent fallbacks and validation"""
        # Ensure cache is warm
        await self._ensure_cache_warm()
        
        # Primary cache read with retries
        data, status = await self.cache_system.get_with_retry(key, default)
        
        # Validate data if we got something
        if data != default and self._validate_market_data(data, data_type):
            logger.debug(f"Cache {status.value} for {key} - data validated")
            return data
        
        # If validation failed or no data, try fallback strategies
        if status in [CacheStatus.MISS, CacheStatus.ERROR, CacheStatus.TIMEOUT]:
            logger.warning(f"Primary cache {status.value} for {key}, trying fallbacks...")
            
            # Try alternative cache keys
            fallback_data = await self._try_fallback_keys(key, data_type)
            if fallback_data is not None:
                logger.info(f"Fallback data found for {key}")
                return fallback_data
            
            # Generate minimal fallback data to prevent empty dashboards
            if self.fallback_enabled:
                fallback_data = self._generate_fallback_data(key, data_type)
                if fallback_data is not None:
                    logger.info(f"Generated fallback data for {key}")
                    return fallback_data
        
        return data if data != default else default
    
    async def _try_fallback_keys(self, primary_key: str, data_type: str) -> Optional[Any]:
        """Try alternative cache keys for the same data"""
        fallback_keys = {
            'market:overview': ['dashboard:overview', 'market:summary', 'overview'],
            'analysis:signals': ['dashboard:signals', 'signals:latest', 'confluence:scores'],
            'market:movers': ['dashboard:movers', 'movers:latest', 'market:gainers_losers'],
            'market:tickers': ['tickers:latest', 'dashboard:tickers', 'exchange:tickers'],
            'analysis:market_regime': ['market:regime', 'dashboard:regime', 'regime:latest']
        }
        
        if primary_key in fallback_keys:
            for fallback_key in fallback_keys[primary_key]:
                try:
                    data, status = await self.cache_system.get_with_retry(fallback_key, timeout=1.0)
                    if status == CacheStatus.HIT and data and self._validate_market_data(data, data_type):
                        logger.info(f"Found fallback data in {fallback_key} for {primary_key}")
                        return data
                except Exception as e:
                    logger.debug(f"Fallback key {fallback_key} failed: {e}")
        
        return None
    
    def _generate_fallback_data(self, key: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Generate realistic fallback data to prevent empty dashboards"""
        current_time = int(time.time())
        
        fallback_data = {
            'market:overview': {
                'total_symbols': 0,
                'total_volume': 0,
                'total_volume_24h': 0,
                'average_change': 0,
                'volatility': 0,
                'trend_strength': 0,
                'current_volatility': 0,
                'avg_volatility': 20,
                'btc_dominance': 59.3,
                'range_24h': 0,
                'avg_range_24h': 0,
                'reliability': 0,
                'avg_reliability': 0,
                'timestamp': current_time,
                'status': 'fallback_data'
            },
            'analysis:signals': {
                'signals': [],
                'count': 0,
                'timestamp': current_time,
                'status': 'fallback_data'
            },
            'market:movers': {
                'gainers': [],
                'losers': [],
                'timestamp': current_time,
                'status': 'fallback_data'
            },
            'market:tickers': {},
            'analysis:market_regime': 'initializing'
        }
        
        return fallback_data.get(key)
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """Get market overview with optimized caching and fallbacks"""
        overview = await self._get_with_fallback('market:overview', {}, 'overview')
        tickers = await self._get_with_fallback('market:tickers', {}, 'tickers')
        regime = await self._get_with_fallback('analysis:market_regime', 'unknown')
        breadth = await self._get_with_fallback('market:breadth', {})
        
        # Calculate totals with validation
        total_symbols = max(0, overview.get('total_symbols', len(tickers)))
        total_volume = max(0, overview.get('total_volume', overview.get('total_volume_24h', 0)))
        
        result = {
            'active_symbols': total_symbols,
            'total_volume': total_volume,
            'total_volume_24h': total_volume,
            'spot_volume_24h': overview.get('spot_volume_24h', total_volume),
            'linear_volume_24h': overview.get('linear_volume_24h', 0),
            'spot_symbols': overview.get('spot_symbols', total_symbols),
            'linear_symbols': overview.get('linear_symbols', 0),
            'market_regime': regime,
            'trend_strength': max(0, min(100, overview.get('trend_strength', 0))),
            'current_volatility': max(0, overview.get('current_volatility', overview.get('volatility', 0))),
            'avg_volatility': max(0, overview.get('avg_volatility', 20)),
            'btc_dominance': max(0, min(100, overview.get('btc_dominance', 59.3))),
            'volatility': max(0, overview.get('current_volatility', overview.get('volatility', 0))),
            'average_change': overview.get('average_change', 0),
            'range_24h': max(0, overview.get('range_24h', overview.get('avg_range_24h', 0))),
            'avg_range_24h': max(0, overview.get('avg_range_24h', overview.get('range_24h', 0))),
            'reliability': max(0, min(100, overview.get('reliability', overview.get('avg_reliability', 75)))),
            'avg_reliability': max(0, min(100, overview.get('avg_reliability', overview.get('reliability', 75)))),
            'timestamp': int(time.time()),
            'data_source': overview.get('status', 'optimized_cache'),
            'cache_performance': {
                'warmup_completed': self._warmup_completed,
                'last_warmup': self._last_warmup_time
            }
        }
        
        # Add market breadth if available
        if breadth and 'up_count' in breadth:
            result['market_breadth'] = {
                'up': max(0, breadth.get('up_count', 0)),
                'down': max(0, breadth.get('down_count', 0)),
                'flat': max(0, breadth.get('flat_count', 0)),
                'breadth_percentage': max(0, min(100, breadth.get('breadth_percentage', 50))),
                'sentiment': breadth.get('market_sentiment', 'neutral')
            }
        
        return result
    
    async def get_dashboard_overview(self) -> Dict[str, Any]:
        """Get complete dashboard overview with enhanced reliability"""
        overview = await self._get_with_fallback('market:overview', {}, 'overview')
        signals = await self._get_with_fallback('analysis:signals', {}, 'signals')
        regime = await self._get_with_fallback('analysis:market_regime', 'unknown')
        movers = await self._get_with_fallback('market:movers', {}, 'movers')
        
        # Extract and validate data
        total_symbols = max(0, overview.get('total_symbols', 0))
        total_volume = max(0, overview.get('total_volume', overview.get('total_volume_24h', 0)))
        signal_list = signals.get('signals', []) if isinstance(signals, dict) else []
        gainers = movers.get('gainers', []) if isinstance(movers, dict) else []
        losers = movers.get('losers', []) if isinstance(movers, dict) else []
        
        # Validate signal list
        valid_signals = []
        for signal in signal_list[:10]:
            if (isinstance(signal, dict) and 
                signal.get('symbol') and 
                isinstance(signal.get('score', 0), (int, float)) and
                0 <= signal.get('score', 0) <= 100):
                valid_signals.append(signal)
        
        result = {
            'summary': {
                'total_symbols': total_symbols,
                'total_volume': total_volume,
                'total_volume_24h': total_volume,
                'average_change': overview.get('average_change', 0),
                'timestamp': int(time.time())
            },
            'market_regime': regime,
            'signals': valid_signals,
            'top_gainers': gainers[:5],
            'top_losers': losers[:5],
            'momentum': {
                'gainers': len([m for m in gainers if isinstance(m, dict) and m.get('change_24h', 0) > 0]),
                'losers': len([m for m in losers if isinstance(m, dict) and m.get('change_24h', 0) < 0])
            },
            'volatility': {
                'value': max(0, overview.get('volatility', 0)),
                'level': 'high' if overview.get('volatility', 0) > 5 else 'normal'
            },
            'source': 'optimized_cache_adapter',
            'data_source': 'real' if (total_symbols > 0 or len(valid_signals) > 0) else 'fallback',
            'performance_info': {
                'cache_warmup_completed': self._warmup_completed,
                'fallback_enabled': self.fallback_enabled,
                'validation_enabled': self.data_validation_enabled,
                'signals_validated': len(valid_signals),
                'signals_total': len(signal_list)
            }
        }
        
        logger.info(f"Dashboard overview: {total_symbols} symbols, {len(valid_signals)} signals, regime={regime}")
        return result
    
    async def get_signals(self) -> Dict[str, Any]:
        """Get trading signals with enhanced validation"""
        signals_data = await self._get_with_fallback('analysis:signals', {}, 'signals')
        
        # Validate and process signals
        raw_signals = signals_data.get('signals', []) if isinstance(signals_data, dict) else []
        validated_signals = []
        
        for signal in raw_signals:
            if not isinstance(signal, dict):
                continue
            
            # Validate required fields
            symbol = signal.get('symbol', '')
            score = signal.get('score', 0)
            price = signal.get('price', 0)
            
            if (symbol and 
                isinstance(score, (int, float)) and 0 <= score <= 100 and
                isinstance(price, (int, float)) and price >= 0):
                
                # Clean and validate signal data
                clean_signal = {
                    'symbol': str(symbol),
                    'score': round(float(score), 2),
                    'price': round(float(price), 8),
                    'change_24h': round(float(signal.get('change_24h', 0)), 2),
                    'volume': max(0, int(signal.get('volume', 0))),
                    'sentiment': signal.get('sentiment', 'NEUTRAL'),
                    'components': signal.get('components', {}),
                    'timestamp': signal.get('timestamp', int(time.time()))
                }
                validated_signals.append(clean_signal)
        
        result = {
            'signals': validated_signals,
            'count': len(validated_signals),
            'timestamp': signals_data.get('timestamp', int(time.time())) if isinstance(signals_data, dict) else int(time.time()),
            'source': 'optimized_cache',
            'validation_stats': {
                'raw_count': len(raw_signals),
                'validated_count': len(validated_signals),
                'filtered_count': len(raw_signals) - len(validated_signals)
            }
        }
        
        logger.debug(f"Signals processed: {len(raw_signals)} raw, {len(validated_signals)} validated")
        return result
    
    async def get_mobile_data(self) -> Dict[str, Any]:
        """Get mobile dashboard data with comprehensive optimization"""
        overview = await self._get_with_fallback('market:overview', {}, 'overview')
        signals = await self._get_with_fallback('analysis:signals', {}, 'signals')
        movers = await self._get_with_fallback('market:movers', {}, 'movers')
        regime = await self._get_with_fallback('analysis:market_regime', 'unknown')
        btc_dom = await self._get_with_fallback('market:btc_dominance', '59.3')
        
        # Process confluence scores with enhanced validation
        confluence_scores = []
        signal_list = signals.get('signals', []) if isinstance(signals, dict) else []
        
        for signal in signal_list[:15]:  # Top 15 for mobile
            if not isinstance(signal, dict) or not signal.get('symbol'):
                continue
                
            symbol = signal.get('symbol', '')
            
            # Skip system/invalid symbols
            if any(invalid in symbol.upper() for invalid in ['SYSTEM', 'STATUS', 'ERROR']):
                continue
            
            # Validate score
            score = signal.get('score', 50)
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                score = 50
            
            # Validate price
            price = signal.get('price', 0)
            if not isinstance(price, (int, float)) or price < 0:
                price = 0
            
            # Get additional data
            tickers_data = await self._get_with_fallback('market:tickers', {})
            ticker = tickers_data.get(symbol, {}) if isinstance(tickers_data, dict) else {}
            
            # Calculate range safely
            high_24h = max(0, float(ticker.get('high', price))) if ticker.get('high') else price
            low_24h = max(0, float(ticker.get('low', price))) if ticker.get('low') else price
            
            range_24h = 0
            if high_24h > 0 and low_24h > 0 and price > 0 and high_24h != low_24h:
                range_24h = ((high_24h - low_24h) / price) * 100
            
            # Calculate reliability based on volume
            volume_24h = max(0, signal.get('volume', ticker.get('volume', 0)))
            reliability = 75  # Default
            if volume_24h > 10000000:  # >$10M
                reliability = 90
            elif volume_24h > 1000000:  # >$1M
                reliability = 80
            elif volume_24h > 100000:  # >$100k
                reliability = 70
            else:
                reliability = 60
            
            confluence_scores.append({
                "symbol": symbol,
                "score": round(float(score), 2),
                "sentiment": signal.get('sentiment', 'NEUTRAL'),
                "reliability": reliability,
                "price": round(float(price), 8),
                "change_24h": round(float(signal.get('change_24h', 0)), 2),
                "volume_24h": int(volume_24h),
                "high_24h": round(high_24h, 8),
                "low_24h": round(low_24h, 8),
                "range_24h": round(range_24h, 2),
                "components": signal.get('components', {
                    "technical": 50,
                    "volume": 50,
                    "orderflow": 50,
                    "sentiment": 50,
                    "orderbook": 50,
                    "price_structure": 50
                }),
                "has_breakdown": signal.get('has_breakdown', False)
            })
        
        # Get BTC dominance with validation
        btc_dominance = overview.get('btc_dominance', 0)
        if btc_dominance == 0:
            try:
                btc_dominance = float(btc_dom)
            except (ValueError, TypeError):
                btc_dominance = 59.3
        
        # Validate BTC dominance range
        btc_dominance = max(0, min(100, btc_dominance))
        
        # Validate movers data
        gainers = movers.get('gainers', [])[:5] if isinstance(movers, dict) else []
        losers = movers.get('losers', [])[:5] if isinstance(movers, dict) else []
        
        # Filter out invalid movers
        valid_gainers = [g for g in gainers if isinstance(g, dict) and g.get('symbol') and isinstance(g.get('change_24h', 0), (int, float))]
        valid_losers = [l for l in losers if isinstance(l, dict) and l.get('symbol') and isinstance(l.get('change_24h', 0), (int, float))]
        
        result = {
            "market_overview": {
                "market_regime": regime,
                "trend_strength": max(0, min(100, overview.get('trend_strength', 0))),
                "volatility": max(0, overview.get('volatility', 0)),
                "btc_dominance": btc_dominance,
                "total_volume_24h": max(0, overview.get('total_volume', overview.get('total_volume_24h', 0)))
            },
            "confluence_scores": confluence_scores,
            "top_movers": {
                "gainers": valid_gainers,
                "losers": valid_losers
            },
            "timestamp": int(time.time()),
            "status": "success",
            "source": "optimized_cache",
            "performance": {
                "cache_warmup_completed": self._warmup_completed,
                "data_validation_enabled": self.data_validation_enabled,
                "scores_processed": len(confluence_scores),
                "gainers_count": len(valid_gainers),
                "losers_count": len(valid_losers)
            }
        }
        
        logger.info(f"Mobile data: {len(confluence_scores)} scores, {len(valid_gainers)} gainers, {len(valid_losers)} losers")
        return result
    
    async def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache performance metrics"""
        return self.cache_system.get_cache_metrics()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        cache_health = await self.cache_system.health_check()
        
        return {
            'status': cache_health['status'],
            'cache': cache_health,
            'adapter': {
                'warmup_completed': self._warmup_completed,
                'fallback_enabled': self.fallback_enabled,
                'validation_enabled': self.data_validation_enabled,
                'last_warmup_time': self._last_warmup_time
            },
            'timestamp': int(time.time())
        }
    
    async def close(self):
        """Clean shutdown"""
        await self.cache_system.close()

# Global optimized cache adapter instance
optimized_cache_adapter = OptimizedCacheAdapter()