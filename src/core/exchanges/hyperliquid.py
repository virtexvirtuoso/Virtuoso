from typing import Dict, List, Optional, Any
import logging
import time
import json
import asyncio
from .base import BaseExchange
import aiohttp
import websockets

logger = logging.getLogger(__name__)

class HyperliquidExchange(BaseExchange):
    """Hyperliquid Exchange Implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.session = None
        self.base_url = "https://api.hyperliquid.xyz"
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.markets = {}
        self.options = {
            'versions': {
                'public': 'v1',
                'private': 'v1',
            },
            'precisionMode': 'DECIMAL_PLACES',
            'defaultType': 'perpetual',
            'hostname': 'api.hyperliquid.xyz',
        }
        
    async def initialize(self) -> bool:
        """Initialize Hyperliquid exchange connection"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection by fetching meta info
            async with self.session.post(f"{self.base_url}", json={"type": "meta"}) as response:
                if response.status == 200:
                    self.initialized = True
                    logger.info("Hyperliquid exchange initialized successfully")
                    return True
                else:
                    logger.error(f"Failed to initialize: {await response.text()}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to initialize Hyperliquid exchange: {str(e)}")
            return False
            
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive market data from Hyperliquid"""
        if not self.initialized:
            await self.initialize()
            
        try:
            await self._wait_for_rate_limit()
            
            # Fetch all data in parallel
            ticker_task = asyncio.create_task(self.fetch_ticker(symbol))
            orderbook_task = asyncio.create_task(self.fetch_orderbook(symbol))
            trades_task = asyncio.create_task(self.fetch_recent_trades(symbol))
            
            ticker = await ticker_task
            orderbook = await orderbook_task
            trades = await trades_task
            
            return {
                'ticker': ticker,
                'orderbook': orderbook,
                'recent_trades': trades,
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid market data for {symbol}: {str(e)}")
            raise
            
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data from Hyperliquid"""
        try:
            await self._wait_for_rate_limit()
            coin = symbol.split('-')[0]  # Extract coin from symbol (e.g., 'BTC' from 'BTC-PERP')
            
            # Fetch current price
            async with self.session.post(f"{self.base_url}", json={"type": "allMids"}) as response:
                if response.status == 200:
                    all_data = await response.json()
                    logger.debug(f"allMids response: {all_data}")
                    
                    # Find data for our symbol
                    if coin not in all_data:
                        raise Exception(f"No data found for {symbol}")
                    
                    mid_price = float(all_data[coin])
                    
                    # Fetch orderbook for bid/ask
                    async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as book_response:
                        book_data = await book_response.json()
                        logger.debug(f"l2Book response: {book_data}")
                        
                        if 'levels' in book_data and isinstance(book_data['levels'], list) and len(book_data['levels']) >= 2:
                            bid_data = book_data['levels'][0]  # First array contains bids
                            ask_data = book_data['levels'][1]  # Second array contains asks
                            
                            best_bid = float(bid_data[0]['px']) if bid_data else mid_price
                            best_ask = float(ask_data[0]['px']) if ask_data else mid_price
                            bid_size = float(bid_data[0]['sz']) if bid_data else 0
                            ask_size = float(ask_data[0]['sz']) if ask_data else 0
                        else:
                            best_bid = best_ask = mid_price
                            bid_size = ask_size = 0
                    
                    # Create ticker response
                    ticker_data = {
                        'symbol': symbol,
                        'last': mid_price,
                        'bid': best_bid,
                        'ask': best_ask,
                        'bidVolume': bid_size,
                        'askVolume': ask_size,
                        'high': mid_price,  # Default to mid price if no 24h data
                        'low': mid_price,   # Default to mid price if no 24h data
                        'volume': 0,        # Default to 0 if no volume data
                        'percentage': 0,    # Default to 0 if no percentage data
                        'timestamp': int(time.time() * 1000),
                        'baseVolume': 0,    # Default to 0 if no base volume data
                        'info': {'mid': mid_price}
                    }
                    
                    return ticker_data
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid ticker for {symbol}: {str(e)}")
            raise
            
    async def fetch_orderbook(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """Fetch orderbook data from Hyperliquid"""
        try:
            await self._wait_for_rate_limit()
            coin = symbol.split('-')[0]
            
            async with self.session.post(f"{self.base_url}", json={"type": "l2Book", "coin": coin}) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract and format bids and asks
                    bids = []
                    asks = []
                    
                    if 'levels' in data and isinstance(data['levels'], list) and len(data['levels']) >= 2:
                        bid_data = data['levels'][0]  # First array contains bids
                        ask_data = data['levels'][1]  # Second array contains asks
                        
                        for bid in bid_data[:limit]:
                            bids.append([float(bid['px']), float(bid['sz'])])
                            
                        for ask in ask_data[:limit]:
                            asks.append([float(ask['px']), float(ask['sz'])])
                    
                    return {
                        'symbol': symbol,
                        'bids': bids,
                        'asks': asks,
                        'timestamp': int(time.time() * 1000)
                    }
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid orderbook for {symbol}: {str(e)}")
            raise
            
    async def fetch_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent trades from Hyperliquid"""
        try:
            await self._wait_for_rate_limit()
            coin = symbol.split('-')[0]
            
            async with self.session.post(f"{self.base_url}", json={"type": "recentTrades", "coin": coin}) as response:
                if response.status == 200:
                    trades_response = await response.json()
                    
                    # Handle case where response is a list
                    trades = trades_response if isinstance(trades_response, list) else trades_response.get('trades', [])
                    
                    formatted_trades = []
                    for trade in trades[:limit]:
                        try:
                            formatted_trade = {
                                'id': str(trade.get('tid', '')),
                                'symbol': symbol,
                                'side': 'buy' if trade.get('side', '') == 'B' else 'sell',
                                'price': float(trade['px']),
                                'amount': float(trade['sz']),
                                'timestamp': int(trade.get('ts', time.time() * 1000)),
                                'datetime': datetime.fromtimestamp(int(trade.get('ts', time.time() * 1000)) / 1000).isoformat(),
                                'fee': None  # Hyperliquid doesn't provide fee info in public trades
                            }
                            formatted_trades.append(formatted_trade)
                        except (KeyError, ValueError) as e:
                            logger.warning(f"Error formatting trade: {str(e)}, trade data: {trade}")
                            continue
                    
                    return formatted_trades
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid trades for {symbol}: {str(e)}")
            raise
            
    async def close(self):
        """Close exchange connection"""
        if self.session:
            await self.session.close() 

    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical kline data from Hyperliquid"""
        try:
            await self._wait_for_rate_limit()
            coin = symbol.split('-')[0]
            
            # Convert interval to Hyperliquid format
            interval_mapping = {
                '1': '1m',
                '5': '5m',
                '15': '15m',
                '30': '30m',
                '60': '1h',
                '240': '4h',
                'D': '1d'
            }
            
            interval_str = interval_mapping.get(interval, '1h')
            
            async with self.session.post(f"{self.base_url}", json={
                "type": "candleSnapshot",
                "coin": coin,
                "interval": interval_str,
                "limit": limit or 100
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            'timestamp': int(candle['time']),
                            'open': float(candle['open']),
                            'high': float(candle['high']),
                            'low': float(candle['low']),
                            'close': float(candle['close']),
                            'volume': float(candle['volume']),
                            'timeframe': interval,
                            'symbol': symbol
                        }
                        for candle in data
                    ]
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid klines for {symbol}: {str(e)}")
            raise

    async def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create an order on Hyperliquid (placeholder - requires authentication)"""
        raise NotImplementedError("Order creation requires authentication")

    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance from Hyperliquid (placeholder - requires authentication)"""
        raise NotImplementedError("Balance fetching requires authentication")

    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch positions from Hyperliquid (placeholder - requires authentication)"""
        raise NotImplementedError("Position fetching requires authentication")

    async def fetch_orders(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Fetch orders from Hyperliquid (placeholder - requires authentication)"""
        raise NotImplementedError("Order fetching requires authentication")

    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Hyperliquid"""
        try:
            await self._wait_for_rate_limit()
            
            async with self.session.post(f"{self.base_url}", json={"type": "meta"}) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            'id': coin,
                            'symbol': f"{coin}-PERP",
                            'base': coin,
                            'quote': 'USD',
                            'type': 'perp',
                            'spot': False,
                            'margin': False,
                            'swap': True,
                            'future': False,
                            'option': False,
                            'active': True,
                            'contract': True,
                            'linear': True,
                            'inverse': False,
                            'contractSize': 1,
                            'info': info
                        }
                        for coin, info in data['universe'].items()
                    ]
                else:
                    raise Exception(f"Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid markets: {str(e)}")
            raise

    async def fetch_status(self) -> Dict[str, Any]:
        """Fetch Hyperliquid exchange status"""
        try:
            await self._wait_for_rate_limit()
            
            async with self.session.post(f"{self.base_url}", json={"type": "meta"}) as response:
                if response.status == 200:
                    return {
                        'status': 'ok',
                        'updated': int(time.time() * 1000),
                        'eta': None,
                        'url': self.base_url
                    }
                else:
                    return {
                        'status': 'error',
                        'updated': int(time.time() * 1000),
                        'eta': None,
                        'url': self.base_url
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching Hyperliquid status: {str(e)}")
            raise

    async def update_position(self, symbol: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update position parameters on Hyperliquid (placeholder - requires authentication)"""
        raise NotImplementedError("Position updating requires authentication") 