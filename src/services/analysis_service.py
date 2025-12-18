"""
Phase 2B: Independent Analysis Service
Reads market data from cache and calculates indicators
Runs independently - if market service fails, uses last cached data
"""
import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import aiomcache

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Independent analysis calculator
    Reads market data from cache, calculates indicators, stores results
    """
    
    def __init__(self, cache_host: str = 'localhost', cache_port: int = 11211):
        """
        Initialize the analysis service
        
        Args:
            cache_host: Memcached host
            cache_port: Memcached port
        """
        self.cache_host = cache_host
        self.cache_port = cache_port
        self.cache_client: Optional[aiomcache.Client] = None
        self.running = False
        self.update_interval = 10  # seconds (slower than market data)
        self.error_count = 0
        self.last_analysis = None
        
    async def initialize(self):
        """Initialize cache connection"""
        try:
            self.cache_client = aiomcache.Client(self.cache_host, self.cache_port)
            await self.cache_client.set(b'service:analysis:status', b'initializing', exptime=10)
            logger.info(f"✅ Analysis service connected to Memcached at {self.cache_host}:{self.cache_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Memcached: {e}")
            return False
    
    async def start(self):
        """
        Main service loop - runs independently
        Reads market data from cache, calculates indicators, stores results
        """
        if not await self.initialize():
            logger.error("Failed to initialize analysis service")
            return
            
        self.running = True
        logger.info("🚀 Analysis Service starting...")
        
        await self._update_service_status('running')
        
        while self.running:
            try:
                # Read market data from cache
                market_data = await self._get_market_data()
                
                if market_data:
                    start_time = time.time()
                    
                    # Calculate various indicators
                    analysis = await self._perform_analysis(market_data)
                    
                    analysis_time = (time.time() - start_time) * 1000  # ms
                    
                    # Store analysis results
                    await self._store_analysis(analysis, analysis_time)
                    
                    self.error_count = 0
                    self.last_analysis = datetime.now(timezone.utc)
                    
                    logger.debug(f"✅ Analysis completed in {analysis_time:.0f}ms")
                else:
                    logger.warning("⚠️ No market data available in cache")
                    
            except asyncio.CancelledError:
                logger.info("Analysis service cancelled")
                break
            except Exception as e:
                self.error_count += 1
                logger.error(f"❌ Analysis service error: {e} (error #{self.error_count})")
                
                if self.error_count > 5:
                    await asyncio.sleep(30)
                    
            await asyncio.sleep(self.update_interval)
        
        await self._cleanup()
    
    async def _get_market_data(self) -> Optional[Dict]:
        """Read market data from cache"""
        try:
            # Get raw ticker data
            tickers_data = await self.cache_client.get(b'market:tickers')
            if not tickers_data:
                return None
                
            tickers = json.loads(tickers_data.decode())
            
            # Get dashboard data if available
            dashboard_data = await self.cache_client.get(b'market:dashboard')
            dashboard = json.loads(dashboard_data.decode()) if dashboard_data else {}
            
            return {
                'tickers': tickers,
                'dashboard': dashboard,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get market data from cache: {e}")
            return None
    
    async def _perform_analysis(self, market_data: Dict) -> Dict:
        """
        Perform various market analysis calculations
        """
        tickers = market_data.get('tickers', {})
        
        if not tickers:
            return {}
        
        analysis = {
            'timestamp': time.time(),
            'symbol_count': len(tickers)
        }
        
        try:
            # Extract price and volume data
            prices = [t['price'] for t in tickers.values() if t.get('price')]
            volumes = [t['volume'] for t in tickers.values() if t.get('volume')]
            changes = [t['change_24h'] for t in tickers.values() if t.get('change_24h') is not None]
            
            # Market Statistics
            analysis['market_stats'] = self._calculate_market_stats(prices, volumes, changes)
            
            # Volatility Analysis
            analysis['volatility'] = self._calculate_volatility(changes)
            
            # Momentum Indicators
            analysis['momentum'] = self._calculate_momentum(tickers)
            
            # Market Breadth
            analysis['breadth'] = self._calculate_breadth(changes)
            
            # Volume Analysis
            analysis['volume_analysis'] = self._calculate_volume_analysis(tickers)
            
            # Correlation hints (simplified)
            analysis['market_regime'] = self._determine_market_regime(changes, volumes)
            
        except Exception as e:
            logger.error(f"Error in analysis calculations: {e}")
            
        return analysis
    
    def _calculate_market_stats(self, prices: List[float], volumes: List[float], changes: List[float]) -> Dict:
        """Calculate basic market statistics"""
        stats = {}
        
        if prices:
            stats['avg_price'] = statistics.mean(prices)
            stats['median_price'] = statistics.median(prices)
            
        if volumes:
            stats['total_volume'] = sum(volumes)
            stats['avg_volume'] = statistics.mean(volumes)
            stats['volume_std'] = statistics.stdev(volumes) if len(volumes) > 1 else 0
            
        if changes:
            stats['avg_change'] = statistics.mean(changes)
            stats['median_change'] = statistics.median(changes)
            stats['change_std'] = statistics.stdev(changes) if len(changes) > 1 else 0
            
        return stats
    
    def _calculate_volatility(self, changes: List[float]) -> Dict:
        """Calculate market volatility metrics"""
        if not changes or len(changes) < 2:
            return {'status': 'insufficient_data'}
            
        std_dev = statistics.stdev(changes)
        
        # Classify volatility
        if std_dev < 2:
            level = 'low'
        elif std_dev < 5:
            level = 'medium'
        elif std_dev < 10:
            level = 'high'
        else:
            level = 'extreme'
            
        return {
            'std_deviation': std_dev,
            'level': level,
            'range': max(changes) - min(changes)
        }
    
    def _calculate_momentum(self, tickers: Dict) -> Dict:
        """Calculate momentum indicators"""
        gainers = 0
        losers = 0
        neutral = 0
        
        strong_gainers = []  # > 10%
        strong_losers = []   # < -10%
        
        for symbol, data in tickers.items():
            change = data.get('change_24h', 0)
            
            if change > 0.1:
                gainers += 1
                if change > 10:
                    strong_gainers.append(symbol)
            elif change < -0.1:
                losers += 1
                if change < -10:
                    strong_losers.append(symbol)
            else:
                neutral += 1
                
        total = gainers + losers + neutral
        
        return {
            'gainers': gainers,
            'losers': losers,
            'neutral': neutral,
            'gainer_ratio': gainers / total if total > 0 else 0,
            'strong_gainers': strong_gainers[:5],
            'strong_losers': strong_losers[:5],
            'momentum_score': (gainers - losers) / total if total > 0 else 0
        }
    
    def _calculate_breadth(self, changes: List[float]) -> Dict:
        """Calculate market breadth indicators"""
        if not changes:
            return {}
            
        advancing = len([c for c in changes if c > 0])
        declining = len([c for c in changes if c < 0])
        unchanged = len([c for c in changes if c == 0])
        
        total = len(changes)
        
        # Advance/Decline ratio
        ad_ratio = advancing / declining if declining > 0 else float('inf')
        
        # McClellan Oscillator simplified
        breadth_thrust = (advancing - declining) / total if total > 0 else 0
        
        return {
            'advancing': advancing,
            'declining': declining,
            'unchanged': unchanged,
            'ad_ratio': min(ad_ratio, 10),  # Cap at 10 for sanity
            'breadth_thrust': breadth_thrust,
            'breadth_strength': 'positive' if breadth_thrust > 0.2 else 'negative' if breadth_thrust < -0.2 else 'neutral'
        }
    
    def _calculate_volume_analysis(self, tickers: Dict) -> Dict:
        """Analyze volume patterns"""
        volume_by_change = {'gainers': [], 'losers': []}
        
        for data in tickers.values():
            volume = data.get('volume', 0)
            change = data.get('change_24h', 0)
            
            if change > 0:
                volume_by_change['gainers'].append(volume)
            elif change < 0:
                volume_by_change['losers'].append(volume)
                
        gainer_volume = sum(volume_by_change['gainers'])
        loser_volume = sum(volume_by_change['losers'])
        total_volume = gainer_volume + loser_volume
        
        return {
            'gainer_volume': gainer_volume,
            'loser_volume': loser_volume,
            'volume_ratio': gainer_volume / loser_volume if loser_volume > 0 else float('inf'),
            'volume_concentration': 'bullish' if gainer_volume > loser_volume * 1.5 else 'bearish' if loser_volume > gainer_volume * 1.5 else 'neutral'
        }
    
    def _determine_market_regime(self, changes: List[float], volumes: List[float]) -> str:
        """Determine overall market regime"""
        if not changes:
            return 'unknown'
            
        avg_change = statistics.mean(changes) if changes else 0
        volatility = statistics.stdev(changes) if len(changes) > 1 else 0
        
        if avg_change > 2 and volatility < 5:
            return 'bullish_trend'
        elif avg_change > 2 and volatility >= 5:
            return 'volatile_bullish'
        elif avg_change < -2 and volatility < 5:
            return 'bearish_trend'
        elif avg_change < -2 and volatility >= 5:
            return 'volatile_bearish'
        elif volatility > 10:
            return 'high_volatility'
        elif volatility < 2:
            return 'low_volatility'
        else:
            return 'ranging'
    
    async def _store_analysis(self, analysis: Dict, analysis_time: float):
        """Store analysis results in cache"""
        try:
            # Main analysis result
            await self.cache_client.set(
                b'analysis:results',
                json.dumps(analysis).encode(),
                exptime=60
            )
            
            # Store specific analysis components for quick access
            for key in ['market_stats', 'volatility', 'momentum', 'breadth', 'volume_analysis']:
                if key in analysis:
                    await self.cache_client.set(
                        f'analysis:{key}'.encode(),
                        json.dumps(analysis[key]).encode(),
                        exptime=60
                    )
            
            # Market regime (important for trading decisions)
            if 'market_regime' in analysis:
                await self.cache_client.set(
                    b'analysis:market_regime',
                    analysis['market_regime'].encode(),
                    exptime=60
                )
            
            # Update health metrics
            health_data = {
                'status': 'healthy',
                'last_analysis': time.time(),
                'analysis_time_ms': analysis_time,
                'error_count': self.error_count
            }
            
            await self.cache_client.set(
                b'analysis:health',
                json.dumps(health_data).encode(),
                exptime=60
            )
            
        except Exception as e:
            logger.error(f"Failed to store analysis in cache: {e}")
    
    async def _update_service_status(self, status: str):
        """Update service status in cache"""
        try:
            status_data = {
                'service': 'analysis',
                'status': status,
                'timestamp': time.time(),
                'error_count': self.error_count,
                'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None
            }
            await self.cache_client.set(
                b'service:analysis:status',
                json.dumps(status_data).encode(),
                exptime=60
            )
        except Exception as e:
            logger.error(f"Failed to update service status: {e}")
    
    async def stop(self):
        """Gracefully stop the service"""
        logger.info("Stopping Analysis Service...")
        self.running = False
        await self._update_service_status('stopping')
    
    async def _cleanup(self):
        """Clean up resources"""
        try:
            await self._update_service_status('stopped')
            if self.cache_client:
                await self.cache_client.close()
            logger.info("✅ Analysis Service stopped cleanly")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def run_analysis_service():
    """
    Standalone runner for the analysis service
    Can be run as a separate process/systemd service
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = AnalysisService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await service.stop()
    except Exception as e:
        logger.error(f"Service crashed: {e}")
        await service.stop()


if __name__ == "__main__":
    # Run as standalone service
    asyncio.run(run_analysis_service())