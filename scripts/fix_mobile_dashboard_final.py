#!/usr/bin/env python3
"""
Fix mobile dashboard final issues:
1. Add market breadth to mobile-data endpoint
2. Fetch real price/change data from Bybit
3. Populate top movers with real data
"""

import asyncio
import aiomcache
import aiohttp
import json
import logging
import time
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MobileDashboardFixer:
    def __init__(self):
        self.client = None
        self.session = None
        
    async def get_client(self):
        if self.client is None:
            self.client = aiomcache.Client('localhost', 11211, pool_size=2)
        return self.client
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def fetch_bybit_tickers(self) -> Dict[str, Any]:
        """Fetch real ticker data from Bybit"""
        try:
            session = await self.get_session()
            url = "https://api.bybit.com/v5/market/tickers?category=spot"
            
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result', {})
            return {}
        except Exception as e:
            logger.error(f"Error fetching Bybit tickers: {e}")
            return {}
    
    async def process_ticker_data(self, tickers: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticker data to extract prices and changes"""
        ticker_list = tickers.get('list', [])
        processed = {}
        
        for ticker in ticker_list:
            symbol = ticker.get('symbol', '')
            if symbol.endswith('USDT'):
                processed[symbol] = {
                    'symbol': symbol,
                    'price': float(ticker.get('lastPrice', 0)),
                    'change_24h': float(ticker.get('price24hPcnt', 0)) * 100,  # Convert to percentage
                    'volume': float(ticker.get('volume24h', 0)),
                    'turnover_24h': float(ticker.get('turnover24h', 0))
                }
        
        return processed
    
    async def update_signals_with_prices(self, ticker_data: Dict[str, Any]):
        """Update cached signals with real price data"""
        try:
            client = await self.get_client()
            
            # Get existing signals
            signals_data = await client.get(b'analysis:signals')
            if not signals_data:
                logger.warning("No signals data found in cache")
                return False
            
            signals = json.loads(signals_data.decode())
            updated_count = 0
            
            # Update each signal with price data
            for signal in signals.get('signals', []):
                symbol = signal.get('symbol', '')
                if symbol in ticker_data:
                    ticker = ticker_data[symbol]
                    signal['price'] = ticker['price']
                    signal['change_24h'] = ticker['change_24h']
                    signal['volume'] = ticker['volume']
                    signal['turnover_24h'] = ticker['turnover_24h']
                    updated_count += 1
            
            # Save updated signals back to cache
            await client.set(
                b'analysis:signals',
                json.dumps(signals).encode(),
                exptime=300
            )
            
            logger.info(f"✅ Updated {updated_count} signals with price data")
            return True
            
        except Exception as e:
            logger.error(f"Error updating signals: {e}")
            return False
    
    async def calculate_market_breadth(self, ticker_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate real market breadth from ticker data"""
        up_count = 0
        down_count = 0
        flat_count = 0
        
        for symbol, data in ticker_data.items():
            change = data.get('change_24h', 0)
            if change > 0.1:  # More than 0.1% up
                up_count += 1
            elif change < -0.1:  # More than 0.1% down
                down_count += 1
            else:
                flat_count += 1
        
        total = up_count + down_count + flat_count
        breadth_percentage = (up_count / total * 100) if total > 0 else 50
        
        # Determine sentiment
        if breadth_percentage > 65:
            sentiment = 'bullish'
        elif breadth_percentage > 55:
            sentiment = 'slightly_bullish'
        elif breadth_percentage > 45:
            sentiment = 'neutral'
        elif breadth_percentage > 35:
            sentiment = 'slightly_bearish'
        else:
            sentiment = 'bearish'
        
        return {
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'total_count': total,
            'breadth_percentage': round(breadth_percentage, 1),
            'market_sentiment': sentiment,
            'timestamp': int(time.time())
        }
    
    async def update_market_breadth(self, breadth_data: Dict[str, Any]):
        """Update market breadth in cache"""
        try:
            client = await self.get_client()
            
            await client.set(
                b'market:breadth',
                json.dumps(breadth_data).encode(),
                exptime=300
            )
            
            logger.info(f"✅ Updated market breadth: {breadth_data['up_count']}↑ {breadth_data['down_count']}↓ ({breadth_data['breadth_percentage']}% Bullish)")
            return True
            
        except Exception as e:
            logger.error(f"Error updating market breadth: {e}")
            return False
    
    async def update_top_movers(self, ticker_data: Dict[str, Any]):
        """Calculate and update top movers"""
        try:
            client = await self.get_client()
            
            # Convert to list and sort
            tickers_list = list(ticker_data.values())
            
            # Sort by change percentage
            gainers = sorted([t for t in tickers_list if t['change_24h'] > 0], 
                           key=lambda x: x['change_24h'], reverse=True)[:10]
            losers = sorted([t for t in tickers_list if t['change_24h'] < 0], 
                          key=lambda x: x['change_24h'])[:10]
            
            movers_data = {
                'gainers': gainers,
                'losers': losers,
                'timestamp': int(time.time())
            }
            
            await client.set(
                b'market:movers',
                json.dumps(movers_data).encode(),
                exptime=300
            )
            
            logger.info(f"✅ Updated movers: {len(gainers)} gainers, {len(losers)} losers")
            
            # Log top 3 of each
            if gainers:
                logger.info(f"  Top gainer: {gainers[0]['symbol']} +{gainers[0]['change_24h']:.2f}%")
            if losers:
                logger.info(f"  Top loser: {losers[0]['symbol']} {losers[0]['change_24h']:.2f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating movers: {e}")
            return False
    
    async def run_fix(self):
        """Run the complete fix"""
        logger.info("🔧 Starting Mobile Dashboard Final Fix...")
        
        # Fetch real ticker data
        logger.info("📊 Fetching real ticker data from Bybit...")
        ticker_response = await self.fetch_bybit_tickers()
        
        if not ticker_response:
            logger.error("❌ Failed to fetch ticker data")
            return False
        
        # Process ticker data
        ticker_data = await self.process_ticker_data(ticker_response)
        logger.info(f"✅ Processed {len(ticker_data)} tickers")
        
        # Update signals with prices
        await self.update_signals_with_prices(ticker_data)
        
        # Calculate and update market breadth
        breadth_data = await self.calculate_market_breadth(ticker_data)
        await self.update_market_breadth(breadth_data)
        
        # Update top movers
        await self.update_top_movers(ticker_data)
        
        logger.info("✅ Mobile Dashboard Fix Complete!")
        return True
    
    async def continuous_update(self, interval: int = 60):
        """Run continuous updates"""
        logger.info(f"🔄 Starting continuous update service (interval: {interval}s)")
        
        while True:
            try:
                await self.run_fix()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                logger.info("🛑 Stopping continuous update service")
                break
            except Exception as e:
                logger.error(f"Error in continuous update: {e}")
                await asyncio.sleep(10)
    
    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            await self.client.close()
        if self.session:
            await self.session.close()

async def main():
    fixer = MobileDashboardFixer()
    
    # Run once to test
    success = await fixer.run_fix()
    
    if success:
        # Ask if should run continuously
        print("\nRun continuous updates? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            await fixer.continuous_update(interval=60)
    
    await fixer.cleanup()

if __name__ == "__main__":
    asyncio.run(main())