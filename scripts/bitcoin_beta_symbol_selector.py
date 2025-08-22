#!/usr/bin/env python3
"""
Dynamic Symbol Selection for Bitcoin Beta Calculations
Fetches top symbols by 24h volume from Bybit
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import aiohttp
from aiomcache import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BetaSymbolSelector:
    """Dynamically selects top symbols for beta calculation based on volume"""
    
    def __init__(self):
        self.cache = Client('localhost', 11211)
        self.base_url = 'https://api.bybit.com'
        
        # Configuration
        self.max_symbols = 25  # Maximum symbols to track
        self.min_volume_usd = 10_000_000  # Minimum 24h volume ($10M)
        self.min_price = 0.00001  # Exclude dust/dead coins
        self.update_interval = 86400  # Update daily (24 hours)
        
        # Exclude stablecoins and wrapped tokens
        self.exclude_patterns = [
            'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'GUSD',
            'WBTC', 'WETH', 'STETH', 'WBNB',
            'UST', 'LUNA', 'LUNC',  # Dead/depegged
        ]
        
        # Always include these core symbols if they meet volume criteria
        self.priority_symbols = [
            'BTCUSDT',  # Always included as benchmark
            'ETHUSDT',  # Always include Ethereum
            'SOLUSDT',  # Major L1
            'BNBUSDT',  # Exchange token
        ]
        
        # Sector allocation (optional diversity requirement)
        self.sector_requirements = {
            'layer1': 8,     # L1 blockchains
            'defi': 5,       # DeFi protocols
            'exchange': 2,   # Exchange tokens
            'gaming': 2,     # Gaming/Metaverse
            'other': 8       # Others
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def should_exclude(self, symbol: str) -> bool:
        """Check if symbol should be excluded"""
        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in symbol.upper():
                return True
        
        # Only include USDT pairs
        if not symbol.endswith('USDT'):
            return True
            
        return False
    
    def categorize_symbol(self, symbol: str) -> str:
        """Categorize symbol by sector"""
        symbol_upper = symbol.upper()
        
        # Layer 1 blockchains
        layer1 = ['ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'ATOM', 'NEAR', 'FTM', 
                  'ALGO', 'ICP', 'TRX', 'TON', 'APT', 'SUI', 'SEI']
        for l1 in layer1:
            if l1 in symbol_upper:
                return 'layer1'
        
        # DeFi protocols
        defi = ['UNI', 'AAVE', 'SUSHI', 'COMP', 'CRV', 'MKR', 'SNX', 'CAKE',
                'LDO', 'GMX', 'DYDX', 'BAL', 'YFI', '1INCH']
        for d in defi:
            if d in symbol_upper:
                return 'defi'
        
        # Exchange tokens
        exchange = ['BNB', 'OKB', 'LEO', 'CRO', 'KCS', 'FTT', 'HT', 'GT']
        for e in exchange:
            if e in symbol_upper:
                return 'exchange'
        
        # Gaming/Metaverse
        gaming = ['AXS', 'SAND', 'MANA', 'GALA', 'ENJ', 'IMX', 'GMT', 'APE']
        for g in gaming:
            if g in symbol_upper:
                return 'gaming'
        
        return 'other'
    
    async def fetch_top_symbols(self) -> List[Dict]:
        """Fetch top symbols by 24h volume from Bybit"""
        url = f"{self.base_url}/v5/market/tickers"
        params = {
            'category': 'spot'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['retCode'] == 0:
                        tickers = data['result']['list']
                        
                        # Process and filter tickers
                        valid_tickers = []
                        for ticker in tickers:
                            symbol = ticker['symbol']
                            
                            # Skip if should be excluded
                            if self.should_exclude(symbol):
                                continue
                            
                            # Parse volume and price
                            try:
                                volume_24h = float(ticker.get('volume24h', 0))
                                last_price = float(ticker.get('lastPrice', 0))
                                turnover_24h = float(ticker.get('turnover24h', 0))
                                
                                # Calculate USD volume if not provided
                                if turnover_24h > 0:
                                    volume_usd = turnover_24h
                                else:
                                    volume_usd = volume_24h * last_price
                                
                                # Apply filters
                                if volume_usd < self.min_volume_usd:
                                    continue
                                if last_price < self.min_price:
                                    continue
                                
                                valid_tickers.append({
                                    'symbol': symbol,
                                    'volume_usd': volume_usd,
                                    'volume_24h': volume_24h,
                                    'price': last_price,
                                    'change_24h': float(ticker.get('price24hPcnt', 0)) * 100,
                                    'sector': self.categorize_symbol(symbol)
                                })
                                
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Error processing {symbol}: {e}")
                                continue
                        
                        # Sort by volume
                        valid_tickers.sort(key=lambda x: x['volume_usd'], reverse=True)
                        
                        logger.info(f"Found {len(valid_tickers)} symbols meeting criteria")
                        return valid_tickers
                    else:
                        logger.error(f"API error: {data.get('retMsg')}")
                else:
                    logger.error(f"HTTP error {response.status}")
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
        
        return []
    
    def select_diverse_symbols(self, tickers: List[Dict]) -> List[str]:
        """Select symbols ensuring sector diversity"""
        selected = []
        sector_counts = {sector: 0 for sector in self.sector_requirements.keys()}
        
        # Always include priority symbols if they meet criteria
        for priority in self.priority_symbols:
            ticker = next((t for t in tickers if t['symbol'] == priority), None)
            if ticker:
                selected.append(ticker['symbol'])
                sector = ticker['sector']
                if sector in sector_counts:
                    sector_counts[sector] += 1
        
        # Add top symbols by volume, respecting sector limits
        for ticker in tickers:
            if ticker['symbol'] in selected:
                continue
            
            if len(selected) >= self.max_symbols:
                break
            
            sector = ticker['sector']
            
            # Check if we need more from this sector
            if sector in sector_counts:
                if sector_counts[sector] < self.sector_requirements[sector]:
                    selected.append(ticker['symbol'])
                    sector_counts[sector] += 1
            else:
                # Unknown sector, add to 'other'
                if sector_counts['other'] < self.sector_requirements['other']:
                    selected.append(ticker['symbol'])
                    sector_counts['other'] += 1
        
        # If we haven't reached max, add more by pure volume
        for ticker in tickers:
            if len(selected) >= self.max_symbols:
                break
            if ticker['symbol'] not in selected:
                selected.append(ticker['symbol'])
        
        return selected
    
    async def update_symbol_list(self) -> List[str]:
        """Update the list of symbols to track"""
        logger.info("Updating symbol list based on 24h volume...")
        
        # Fetch top symbols
        tickers = await self.fetch_top_symbols()
        
        if not tickers:
            logger.error("Failed to fetch tickers, using fallback list")
            # Fallback to hardcoded list
            return [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
                'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT', 'NEARUSDT'
            ]
        
        # Select diverse symbols
        selected_symbols = self.select_diverse_symbols(tickers)
        
        # Ensure BTCUSDT is always first (benchmark)
        if 'BTCUSDT' in selected_symbols:
            selected_symbols.remove('BTCUSDT')
        selected_symbols.insert(0, 'BTCUSDT')
        
        # Store in cache
        await self.store_symbol_list(selected_symbols, tickers)
        
        # Log selection
        logger.info(f"Selected {len(selected_symbols)} symbols for beta calculation")
        logger.info(f"Top 5 by volume: {selected_symbols[1:6]}")
        
        # Log sector distribution
        sector_dist = {}
        for symbol in selected_symbols:
            ticker = next((t for t in tickers if t['symbol'] == symbol), None)
            if ticker:
                sector = ticker['sector']
                sector_dist[sector] = sector_dist.get(sector, 0) + 1
        logger.info(f"Sector distribution: {sector_dist}")
        
        return selected_symbols
    
    async def store_symbol_list(self, symbols: List[str], tickers: List[Dict]):
        """Store symbol list and metadata in cache"""
        try:
            # Store symbol list
            symbol_data = {
                'symbols': symbols,
                'count': len(symbols),
                'updated': datetime.now().isoformat(),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
            
            await self.cache.set(
                b'beta:symbol_list',
                json.dumps(symbol_data).encode(),
                exptime=86400  # 24 hour TTL
            )
            
            # Store ticker metadata
            ticker_map = {t['symbol']: t for t in tickers if t['symbol'] in symbols}
            await self.cache.set(
                b'beta:symbol_metadata',
                json.dumps(ticker_map).encode(),
                exptime=86400
            )
            
            logger.info(f"Stored {len(symbols)} symbols in cache")
            
        except Exception as e:
            logger.error(f"Error storing symbol list: {e}")
    
    async def get_current_symbols(self) -> List[str]:
        """Get current symbol list from cache or update if needed"""
        try:
            # Check cache first
            data = await self.cache.get(b'beta:symbol_list')
            if data:
                symbol_data = json.loads(data.decode())
                
                # Check if update needed (older than 24 hours)
                timestamp = symbol_data.get('timestamp', 0)
                age_hours = (datetime.now().timestamp() * 1000 - timestamp) / 1000 / 3600
                
                if age_hours < 24:
                    logger.info(f"Using cached symbol list ({len(symbol_data['symbols'])} symbols, {age_hours:.1f}h old)")
                    return symbol_data['symbols']
                else:
                    logger.info(f"Symbol list expired ({age_hours:.1f}h old), updating...")
            
            # Update needed
            return await self.update_symbol_list()
            
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            # Return fallback list
            return [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
                'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT', 'NEARUSDT'
            ]
    
    async def get_symbol_metadata(self) -> Dict:
        """Get metadata for current symbols"""
        try:
            data = await self.cache.get(b'beta:symbol_metadata')
            if data:
                return json.loads(data.decode())
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
        return {}

async def main():
    """Main entry point for testing"""
    async with BetaSymbolSelector() as selector:
        # Update symbol list
        symbols = await selector.update_symbol_list()
        
        print(f"\n{'='*60}")
        print("DYNAMIC SYMBOL SELECTION RESULTS")
        print('='*60)
        
        print(f"\nSelected {len(symbols)} symbols:")
        
        # Get metadata
        metadata = await selector.get_symbol_metadata()
        
        for i, symbol in enumerate(symbols[:10], 1):
            meta = metadata.get(symbol, {})
            volume_b = meta.get('volume_usd', 0) / 1_000_000_000
            print(f"{i:2}. {symbol:12} Volume: ${volume_b:6.2f}B  "
                  f"Price: ${meta.get('price', 0):10,.2f}  "
                  f"24h: {meta.get('change_24h', 0):+6.2f}%  "
                  f"Sector: {meta.get('sector', 'unknown')}")
        
        if len(symbols) > 10:
            print(f"... and {len(symbols) - 10} more")

if __name__ == '__main__':
    asyncio.run(main())