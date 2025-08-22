"""
Direct Market Data Service - Phase 1 Implementation
Minimal, working market data fetcher without abstractions
"""
import aiohttp
import asyncio
import json
import time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DirectMarketData:
    """Minimal market data fetcher that actually works"""
    
    @staticmethod
    async def fetch_tickers(limit: int = 20) -> Dict:
        """
        Direct fetch from Bybit - no abstractions, no complex timeouts
        Returns formatted ticker data ready for dashboard
        """
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear"}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.bybit.com',
            'Referer': 'https://www.bybit.com/'
        }
        
        try:
            # Simple session with basic timeout - proven to work
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            return DirectMarketData._format_tickers(data, limit)
                    else:
                        logger.error(f"HTTP {response.status} from Bybit")
        except asyncio.TimeoutError:
            logger.error("Timeout fetching market data (30s)")
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
        
        return {}
    
    @staticmethod
    def _format_tickers(data: Dict, limit: int) -> Dict:
        """Simple formatting for dashboard consumption"""
        tickers = {}
        items = data.get('result', {}).get('list', [])
        
        # Sort by volume to get most active symbols
        sorted_items = sorted(items, 
                            key=lambda x: float(x.get('volume24h', 0)), 
                            reverse=True)
        
        for item in sorted_items[:limit]:
            symbol = item.get('symbol', '')
            # Convert BTCUSDT to BTC/USDT format
            if 'USDT' in symbol and '/' not in symbol:
                symbol = symbol.replace('USDT', '/USDT')
            
            tickers[symbol] = {
                'symbol': symbol,
                'price': float(item.get('lastPrice', 0)),
                'bid': float(item.get('bid1Price', 0)),
                'ask': float(item.get('ask1Price', 0)),
                'volume': float(item.get('volume24h', 0)),
                'change_24h': float(item.get('price24hPcnt', 0)) * 100,
                'high_24h': float(item.get('highPrice24h', 0)),
                'low_24h': float(item.get('lowPrice24h', 0)),
                'timestamp': int(time.time())
            }
        
        logger.info(f"✅ Fetched {len(tickers)} tickers from Bybit")
        return tickers
    
    @staticmethod
    async def fetch_single_ticker(symbol: str) -> Dict:
        """Fetch single symbol data - useful for testing"""
        # Convert BTC/USDT to BTCUSDT format for API
        api_symbol = symbol.replace('/', '')
        
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            "category": "linear",
            "symbol": api_symbol
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.bybit.com',
            'Referer': 'https://www.bybit.com/'
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('retCode') == 0:
                            items = data.get('result', {}).get('list', [])
                            if items:
                                return DirectMarketData._format_single(items[0])
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
        
        return {}
    
    @staticmethod
    def _format_single(item: Dict) -> Dict:
        """Format single ticker response"""
        symbol = item.get('symbol', '').replace('USDT', '/USDT')
        return {
            'symbol': symbol,
            'price': float(item.get('lastPrice', 0)),
            'volume': float(item.get('volume24h', 0)),
            'change_24h': float(item.get('price24hPcnt', 0)) * 100,
            'timestamp': int(time.time())
        }
    
    @staticmethod
    async def get_dashboard_data() -> Dict:
        """
        Get formatted data specifically for dashboard display
        Includes market overview and top movers
        """
        tickers = await DirectMarketData.fetch_tickers(50)
        
        if not tickers:
            return {
                'status': 'error',
                'message': 'Unable to fetch market data',
                'data': {}
            }
        
        # Calculate market overview
        total_volume = sum(t['volume'] for t in tickers.values())
        avg_change = sum(t['change_24h'] for t in tickers.values()) / len(tickers)
        
        # Get top gainers and losers
        sorted_by_change = sorted(tickers.values(), 
                                key=lambda x: x['change_24h'], 
                                reverse=True)
        
        return {
            'status': 'success',
            'timestamp': int(time.time()),
            'overview': {
                'total_symbols': len(tickers),
                'total_volume_24h': total_volume,
                'average_change_24h': round(avg_change, 2),
                'data_source': 'Bybit'
            },
            'top_gainers': sorted_by_change[:5],
            'top_losers': sorted_by_change[-5:],
            'all_tickers': tickers
        }


# Standalone cache updater (optional, for Phase 2 prep)
class MarketDataUpdater:
    """Background updater for continuous data flow"""
    
    def __init__(self, cache_client=None):
        self.cache = cache_client
        self.running = False
        
    async def start(self):
        """Run continuous updates every 5 seconds"""
        self.running = True
        logger.info("Starting market data updater...")
        
        while self.running:
            try:
                data = await DirectMarketData.fetch_tickers()
                
                if data and self.cache:
                    # Store in cache for other services
                    await self.cache.set('market:tickers', json.dumps(data))
                    await self.cache.set('market:updated', str(int(time.time())))
                    logger.debug(f"Updated cache with {len(data)} tickers")
                    
            except Exception as e:
                logger.error(f"Updater error: {e}")
            
            await asyncio.sleep(5)
    
    def stop(self):
        """Stop the updater"""
        self.running = False
        logger.info("Market data updater stopped")


# Test function for standalone testing
async def test_direct_fetch():
    """Test the direct market data fetcher"""
    print("Testing Direct Market Data Fetcher...")
    print("=" * 50)
    
    # Test 1: Fetch multiple tickers
    print("\n1. Fetching top 10 tickers...")
    tickers = await DirectMarketData.fetch_tickers(10)
    if tickers:
        print(f"✅ Success! Got {len(tickers)} tickers")
        for symbol, data in list(tickers.items())[:3]:
            print(f"   {symbol}: ${data['price']:.2f} ({data['change_24h']:+.2f}%)")
    else:
        print("❌ Failed to fetch tickers")
    
    # Test 2: Fetch single ticker
    print("\n2. Fetching BTC/USDT...")
    btc = await DirectMarketData.fetch_single_ticker("BTC/USDT")
    if btc:
        print(f"✅ BTC/USDT: ${btc['price']:.2f}")
    else:
        print("❌ Failed to fetch BTC/USDT")
    
    # Test 3: Get dashboard data
    print("\n3. Getting dashboard data...")
    dashboard = await DirectMarketData.get_dashboard_data()
    if dashboard['status'] == 'success':
        print(f"✅ Dashboard data ready")
        print(f"   Total symbols: {dashboard['overview']['total_symbols']}")
        print(f"   Avg 24h change: {dashboard['overview']['average_change_24h']}%")
        if dashboard['top_gainers']:
            top = dashboard['top_gainers'][0]
            print(f"   Top gainer: {top['symbol']} (+{top['change_24h']:.2f}%)")
    else:
        print("❌ Failed to get dashboard data")
    
    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    # Run test when executed directly
    asyncio.run(test_direct_fetch())