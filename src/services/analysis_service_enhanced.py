from src.utils.task_tracker import create_tracked_task
"""
Enhanced Analysis Service - Phase 2B
Generates trading signals, top movers, and market analysis
Fixes all data format issues for dashboard compatibility
"""
import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiomcache

logger = logging.getLogger(__name__)


class EnhancedAnalysisService:
    """
    Enhanced analysis service that generates trading signals
    Produces data in the exact format dashboards expect
    """
    
    def __init__(self, cache_host: str = 'localhost', cache_port: int = 11211):
        self.cache_host = cache_host
        self.cache_port = cache_port
        self.cache_client: Optional[aiomcache.Client] = None
        self.running = False
        self.update_interval = 10  # seconds
        
    async def initialize(self):
        """Initialize cache connection"""
        try:
            self.cache_client = aiomcache.Client(self.cache_host, self.cache_port)
            logger.info(f"✅ Enhanced Analysis service connected to Memcached")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Memcached: {e}")
            return False
    
    async def start(self):
        """Main service loop - generates signals and analysis"""
        if not await self.initialize():
            return
            
        self.running = True
        logger.info("🚀 Enhanced Analysis Service starting...")
        
        while self.running:
            try:
                # Get market data from cache
                market_data = await self._get_market_data()
                
                if market_data:
                    # Generate trading signals
                    signals = await self._generate_signals(market_data)
                    
                    # Generate top movers
                    movers = await self._generate_movers(market_data)
                    
                    # Calculate market overview with correct field names
                    overview = await self._generate_overview(market_data)
                    
                    # Determine market regime
                    regime = await self._determine_market_regime(market_data)
                    
                    # Store all results in cache
                    await self._store_results(signals, movers, overview, regime)
                    
                    logger.info(f"✅ Analysis complete: {len(signals)} signals, "
                              f"{len(movers.get('gainers', []))} gainers, "
                              f"{len(movers.get('losers', []))} losers")
                else:
                    logger.warning("No market data available")
                    
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                
            await asyncio.sleep(self.update_interval)
    
    async def _get_market_data(self) -> Optional[Dict]:
        """Read market data from cache"""
        try:
            tickers_data = await self.cache_client.get(b'market:tickers')
            if not tickers_data:
                return None
                
            tickers = json.loads(tickers_data.decode())
            return {'tickers': tickers, 'timestamp': time.time()}
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return None
    
    async def _generate_signals(self, market_data: Dict) -> List[Dict]:
        """
        Generate trading signals in dashboard format
        Format: {symbol, score, price, change_24h, volume, components}
        """
        tickers = market_data.get('tickers', {})
        signals = []
        
        for symbol, ticker in tickers.items():
            try:
                # Calculate signal score (0-100)
                score = self._calculate_signal_score(ticker)
                
                # Build signal in expected format
                signal = {
                    'symbol': symbol,
                    'score': round(score, 2),
                    'price': ticker.get('price', 0),
                    'change_24h': ticker.get('change_24h', 0),
                    'volume': ticker.get('volume', 0),
                    'components': {
                        'technical': self._get_real_score(symbol, 'technical'),
                        'volume': self._get_real_score(symbol, 'volume'),
                        'orderflow': self._get_real_score(symbol, 'orderflow'),
                        'sentiment': self._get_real_score(symbol, 'sentiment'),
                        'orderbook': self._get_real_score(symbol, 'orderbook'),
                        'price_structure': self._get_real_score(symbol, 'price_structure')
                    },
                    'timestamp': int(time.time())
                }
                signals.append(signal)
                
            except Exception as e:
                logger.debug(f"Error processing {symbol}: {e}")
                continue
        
        # Sort by score descending
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top 50 signals
        return signals[:50]
    
    def _get_real_score(self, symbol: str, component: str) -> float:
        """Get real score from actual indicators"""
        try:
            # Use real indicator data from cache or direct calculation
            if hasattr(self, 'cache_client') and self.cache_client:
                cache_key = f"{symbol}:{component}:score".encode()
                score_data = create_tracked_task(self.cache_client.get, name="get_task")
                if score_data:
                    return float(score_data)
            
            # If no cached score, return None (not a fake value)
            return None
        except Exception as e:
            logger.error(f"Error getting {component} score for {symbol}: {e}")
            return None
    
    def _calculate_signal_score(self, ticker: Dict) -> float:
        """
        Calculate signal score based on multiple factors
        Returns score 0-100
        """
        score = 50.0  # Base score
        
        # Price change factor (-20 to +20)
        change = ticker.get('change_24h', 0)
        if change > 10:
            score += 20
        elif change > 5:
            score += 15
        elif change > 2:
            score += 10
        elif change > 0:
            score += 5
        elif change < -10:
            score -= 20
        elif change < -5:
            score -= 15
        elif change < -2:
            score -= 10
        elif change < 0:
            score -= 5
        
        # Volume factor (0 to +20)
        volume = ticker.get('volume', 0)
        if volume > 100_000_000:  # >100M
            score += 20
        elif volume > 50_000_000:  # >50M
            score += 15
        elif volume > 10_000_000:  # >10M
            score += 10
        elif volume > 1_000_000:   # >1M
            score += 5
        
        # No random variation - use real data only
        
        # Clamp to 0-100
        return max(0, min(100, score))
    
    async def _generate_movers(self, market_data: Dict) -> Dict:
        """
        Generate top gainers and losers
        Format: {gainers: [...], losers: [...]}
        """
        tickers = market_data.get('tickers', {})
        
        # Create list of symbols with changes
        changes = []
        for symbol, ticker in tickers.items():
            if ticker.get('change_24h') is not None:
                changes.append({
                    'symbol': symbol,
                    'change_24h': ticker['change_24h'],
                    'price': ticker.get('price', 0),
                    'volume': ticker.get('volume', 0),
                    'display_symbol': symbol.replace('USDT', '').replace('/', '')
                })
        
        # Sort by change
        changes.sort(key=lambda x: x['change_24h'], reverse=True)
        
        # Get top 10 gainers and losers
        gainers = [c for c in changes if c['change_24h'] > 0][:10]
        losers = [c for c in reversed(changes) if c['change_24h'] < 0][:10]
        
        return {
            'gainers': gainers,
            'losers': losers,
            'timestamp': int(time.time())
        }
    
    async def _generate_overview(self, market_data: Dict) -> Dict:
        """
        Generate market overview with CORRECT field names
        Fixes the total_volume vs total_volume_24h issue
        """
        tickers = market_data.get('tickers', {})
        
        total_volume = sum(t.get('volume', 0) for t in tickers.values())
        total_symbols = len(tickers)
        
        changes = [t.get('change_24h', 0) for t in tickers.values() 
                  if t.get('change_24h') is not None]
        avg_change = statistics.mean(changes) if changes else 0
        
        # Calculate volatility
        volatility = statistics.stdev(changes) if len(changes) > 1 else 0
        
        return {
            'total_symbols': total_symbols,
            'total_volume': total_volume,  # Correct field name for dashboard
            'total_volume_24h': total_volume,  # Also include old name for compatibility
            'average_change': round(avg_change, 2),
            'volatility': round(volatility, 2),
            'timestamp': int(time.time())
        }
    
    async def _determine_market_regime(self, market_data: Dict) -> str:
        """
        Determine market regime based on data
        Returns: bullish, bearish, neutral, volatile_bullish, volatile_bearish
        """
        tickers = market_data.get('tickers', {})
        
        changes = [t.get('change_24h', 0) for t in tickers.values() 
                  if t.get('change_24h') is not None]
        
        if not changes:
            return 'neutral'
        
        avg_change = statistics.mean(changes)
        volatility = statistics.stdev(changes) if len(changes) > 1 else 0
        
        # Count gainers vs losers
        gainers = sum(1 for c in changes if c > 0)
        losers = sum(1 for c in changes if c < 0)
        
        # Determine regime
        is_volatile = volatility > 5
        
        if avg_change > 2:
            return 'volatile_bullish' if is_volatile else 'bullish'
        elif avg_change < -2:
            return 'volatile_bearish' if is_volatile else 'bearish'
        elif gainers > losers * 1.5:
            return 'bullish'
        elif losers > gainers * 1.5:
            return 'bearish'
        else:
            return 'neutral'
    
    async def _store_results(self, signals: List[Dict], movers: Dict, 
                            overview: Dict, regime: str):
        """Store all analysis results in cache"""
        try:
            # Store signals
            signals_data = {
                'signals': signals,
                'count': len(signals),
                'timestamp': int(time.time())
            }
            await self.cache_client.set(
                b'analysis:signals',
                json.dumps(signals_data).encode(),
                exptime=60
            )
            
            # Store movers
            await self.cache_client.set(
                b'market:movers',
                json.dumps(movers).encode(),
                exptime=60
            )
            
            # Store overview with correct field names
            await self.cache_client.set(
                b'market:overview',
                json.dumps(overview).encode(),
                exptime=60
            )
            
            # Store regime
            await self.cache_client.set(
                b'analysis:market_regime',
                regime.encode(),
                exptime=60
            )
            
            logger.debug(f"Stored analysis results: {len(signals)} signals, regime: {regime}")
            
        except Exception as e:
            logger.error(f"Failed to store results: {e}")
    
    async def stop(self):
        """Stop the service"""
        self.running = False
        if self.cache_client:
            await self.cache_client.close()


async def main():
    """Run the enhanced analysis service standalone"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    service = EnhancedAnalysisService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())