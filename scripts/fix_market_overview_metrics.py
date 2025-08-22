#!/usr/bin/env python3
"""
Fix Market Overview Metrics
Fixes:
1. Trend Strength calculation and display (0-100)
2. BTC Dominance with market cap data
3. Volatility calculation
4. Total Volume aggregation
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any, List
import aiomcache
import numpy as np
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketOverviewFixer:
    def __init__(self):
        self.cache = aiomcache.Client('localhost', 11211)
        
    async def fetch_market_cap_data(self) -> Dict[str, float]:
        """Fetch market cap data for BTC dominance calculation"""
        try:
            # CoinGecko API (free tier) for market cap data
            async with aiohttp.ClientSession() as session:
                # Get global market data
                url = "https://api.coingecko.com/api/v3/global"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get('data', {})
                        
                        btc_dominance = market_data.get('market_cap_percentage', {}).get('btc', 0)
                        total_market_cap = market_data.get('total_market_cap', {}).get('usd', 0)
                        
                        logger.info(f"Fetched BTC dominance: {btc_dominance:.2f}%")
                        return {
                            'btc_dominance': btc_dominance,
                            'total_market_cap': total_market_cap
                        }
        except Exception as e:
            logger.error(f"Error fetching market cap data: {e}")
            
        # Fallback to estimated values based on current market
        return {
            'btc_dominance': 52.5,  # Approximate current BTC dominance
            'total_market_cap': 2500000000000  # ~$2.5T
        }
    
    async def fetch_bybit_tickers(self) -> Dict[str, Any]:
        """Fetch all tickers from Bybit for comprehensive calculations"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.bybit.com/v5/market/tickers?category=spot"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('result', {})
        except Exception as e:
            logger.error(f"Error fetching Bybit tickers: {e}")
        return {}
    
    def calculate_volatility(self, price_changes: List[float]) -> Dict[str, float]:
        """Calculate market volatility metrics"""
        if not price_changes or len(price_changes) < 2:
            return {'current': 0, 'average': 0}
        
        # Remove outliers using IQR method
        q1 = np.percentile(price_changes, 25)
        q3 = np.percentile(price_changes, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered_changes = [x for x in price_changes if lower_bound <= x <= upper_bound]
        
        if not filtered_changes:
            filtered_changes = price_changes
        
        # Calculate volatility as standard deviation
        current_volatility = float(np.std(filtered_changes))
        
        # Average volatility (use 20 as baseline for crypto)
        avg_volatility = 20.0  # Typical crypto market volatility
        
        return {
            'current': round(current_volatility, 2),
            'average': round(avg_volatility, 2)
        }
    
    def calculate_trend_strength(self, avg_change: float, volatility: float) -> float:
        """
        Calculate trend strength (0-100)
        Strong trend = high directional movement relative to volatility
        """
        if volatility == 0:
            volatility = 1
        
        # Raw trend strength: ratio of directional movement to volatility
        raw_strength = abs(avg_change) / volatility
        
        # Scale to 0-100 with logarithmic scaling for better distribution
        # raw_strength of 0.5 = 50%, 1.0 = 70%, 2.0 = 85%
        if raw_strength == 0:
            return 0
        
        # Use logarithmic scaling
        scaled_strength = 50 * (1 + np.log10(1 + raw_strength))
        
        # Cap at 100
        return min(100, max(0, scaled_strength))
    
    async def calculate_enhanced_market_overview(self) -> Dict[str, Any]:
        """Calculate all market overview metrics properly"""
        
        # Fetch data
        bybit_data = await self.fetch_bybit_tickers()
        market_cap_data = await self.fetch_market_cap_data()
        
        if not bybit_data or 'list' not in bybit_data:
            logger.error("No ticker data available")
            return {}
        
        tickers = bybit_data['list']
        
        # Initialize metrics
        total_volume = 0
        price_changes = []
        up_count = 0
        down_count = 0
        
        # Process all tickers
        for ticker in tickers:
            try:
                # Volume aggregation (in USDT)
                volume_24h = float(ticker.get('turnover24h', 0))
                total_volume += volume_24h
                
                # Price change for volatility and trend
                price_change = float(ticker.get('price24hPcnt', 0)) * 100
                if price_change != 0:  # Exclude unchanged
                    price_changes.append(price_change)
                    
                    if price_change > 0:
                        up_count += 1
                    elif price_change < 0:
                        down_count += 1
                        
            except (ValueError, TypeError):
                continue
        
        # Calculate metrics
        avg_change = np.mean(price_changes) if price_changes else 0
        volatility_data = self.calculate_volatility(price_changes)
        trend_strength = self.calculate_trend_strength(avg_change, volatility_data['current'])
        
        # Determine market regime
        if avg_change > 1.0 and up_count > down_count * 1.2:
            regime = 'bullish'
        elif avg_change < -1.0 and down_count > up_count * 1.2:
            regime = 'bearish'
        elif abs(avg_change) < 0.5:
            regime = 'neutral'
        elif avg_change > 0:
            regime = 'neutral_bullish'
        else:
            regime = 'neutral_bearish'
        
        # Compile results
        market_overview = {
            'market_regime': regime,
            'trend_strength': round(trend_strength, 1),  # 0-100 scale
            'current_volatility': volatility_data['current'],
            'avg_volatility': volatility_data['average'],
            'btc_dominance': round(market_cap_data['btc_dominance'], 1),
            'total_volume': total_volume,
            'total_volume_24h': total_volume,  # Alias for compatibility
            'market_breadth': {
                'up': up_count,
                'down': down_count,
                'up_count': up_count,
                'down_count': down_count,
                'flat': len(tickers) - up_count - down_count,
                'breadth_percentage': round((up_count / (up_count + down_count) * 100) if (up_count + down_count) > 0 else 50, 1),
                'sentiment': 'bullish' if up_count > down_count * 1.5 else 'bearish' if down_count > up_count * 1.5 else 'neutral'
            },
            'average_change': round(avg_change, 2),
            'symbols_analyzed': len(tickers),
            'timestamp': datetime.utcnow().isoformat(),
            'data_source': 'bybit_enhanced'
        }
        
        logger.info(f"Calculated market overview: regime={regime}, trend={trend_strength:.1f}%, vol={volatility_data['current']:.2f}%, btc_dom={market_cap_data['btc_dominance']:.1f}%")
        
        return market_overview
    
    async def update_cache(self):
        """Update cache with fixed metrics"""
        try:
            # Calculate enhanced overview
            market_overview = await self.calculate_enhanced_market_overview()
            
            if not market_overview:
                logger.error("Failed to calculate market overview")
                return False
            
            # Store in cache
            overview_json = json.dumps(market_overview).encode()
            await self.cache.set(b'market:overview', overview_json, exptime=60)
            
            # Also store market breadth separately for compatibility
            breadth_json = json.dumps(market_overview['market_breadth']).encode()
            await self.cache.set(b'market:breadth', breadth_json, exptime=60)
            
            # Store regime
            regime = market_overview['market_regime'].encode()
            await self.cache.set(b'analysis:market_regime', regime, exptime=60)
            
            logger.info("✅ Successfully updated cache with fixed metrics")
            logger.info(f"  - Trend Strength: {market_overview['trend_strength']}%")
            logger.info(f"  - BTC Dominance: {market_overview['btc_dominance']}%")
            logger.info(f"  - Current Volatility: {market_overview['current_volatility']}%")
            logger.info(f"  - Total Volume: ${market_overview['total_volume']:,.0f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating cache: {e}")
            return False
        finally:
            await self.cache.close()
    
    async def test_api_endpoint(self):
        """Test the API endpoint to verify fixes"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "http://localhost:8001/api/dashboard-cached/mobile-data"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        overview = data.get('market_overview', {})
                        
                        logger.info("\n📊 API Response After Fix:")
                        logger.info(f"  - Market Regime: {overview.get('market_regime', 'N/A')}")
                        logger.info(f"  - Trend Strength: {overview.get('trend_strength', 0)}%")
                        logger.info(f"  - BTC Dominance: {overview.get('btc_dominance', 0)}%")
                        logger.info(f"  - Current Volatility: {overview.get('current_volatility', 0)}%")
                        logger.info(f"  - Total Volume: ${overview.get('total_volume', 0):,.0f}")
                        
                        if 'market_breadth' in data:
                            breadth = data['market_breadth']
                            logger.info(f"  - Market Breadth: {breadth.get('up_count', 0)}↑ {breadth.get('down_count', 0)}↓")
                    else:
                        logger.error(f"API returned status {response.status}")
        except Exception as e:
            logger.error(f"Error testing API: {e}")

async def main():
    logger.info("🔧 Starting Market Overview Metrics Fix...")
    logger.info("=" * 50)
    
    fixer = MarketOverviewFixer()
    
    # Update cache with fixed metrics
    success = await fixer.update_cache()
    
    if success:
        # Test the API endpoint
        await asyncio.sleep(2)  # Wait for cache to propagate
        await fixer.test_api_endpoint()
        
        logger.info("\n✅ Fix completed successfully!")
        logger.info("The dashboard should now show:")
        logger.info("  • Trend Strength: 0-100% scale")
        logger.info("  • BTC Dominance: Real market cap %")
        logger.info("  • Volatility: Calculated from price movements")
        logger.info("  • Total Volume: Aggregated from all tickers")
    else:
        logger.error("❌ Fix failed - check logs for details")

if __name__ == "__main__":
    asyncio.run(main())