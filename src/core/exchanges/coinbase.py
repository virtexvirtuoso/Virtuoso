from typing import Dict, List, Optional, Any
import logging
import time
import hmac
import hashlib
import base64
import json
from datetime import datetime
import aiohttp
from .base import BaseExchange
import decimal
import binascii
import asyncio
from src.utils.task_tracker import create_tracked_task

logger = logging.getLogger(__name__)

class CoinbaseExchange(BaseExchange):
    """Coinbase Advanced Trading Implementation"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.session = None
        self.base_url = "https://api.coinbase.com/api/v3/brokerage"  # Advanced Trade API
        self.public_url = "https://api.exchange.coinbase.com"  # Public API
        self.markets = {}
        self.options = {
            'versions': {
                'public': 'v3',
                'private': 'v3',
            },
            'precisionMode': 'DECIMAL_PLACES',
            'defaultType': 'spot',  # Using spot for Advanced Trade API
            'hostname': 'api.coinbase.com',
        }
        
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """Generate signature for Coinbase Advanced Trading API"""
        # The message string should be timestamp + method + requestPath + body
        message = f"{timestamp}{method}{request_path}{body}"
        
        # Convert the API secret to bytes
        try:
            # First try to decode as base64
            key_bytes = base64.b64decode(self.config['api_credentials']['api_secret'])
        except binascii.Error:
            # If not base64 encoded, use the raw secret
            key_bytes = self.config['api_credentials']['api_secret'].encode('utf-8')
            
        message_bytes = message.encode('utf-8')
        
        # Create HMAC SHA256 hash using the key
        hmac_obj = hmac.new(key_bytes, message_bytes, hashlib.sha256)
        
        # Get the hex digest and encode it in base64
        signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
        return signature
        
    async def initialize(self) -> bool:
        """Initialize Coinbase exchange connection"""
        if self.initialized:
            return True
            
        try:
            # Test connection by making a simple request
            timestamp = str(int(time.time()))
            request_path = "/api/v3/brokerage/accounts"
            signature = self._generate_signature(timestamp, "GET", request_path)
            
            headers = {
                'Content-Type': 'application/json',
                'CB-ACCESS-KEY': self.config['api_credentials']['api_key'],
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
            }
            
            if 'organization_id' in self.config['api_credentials']:
                headers['CB-ACCESS-ORGANIZATION-ID'] = self.config['api_credentials']['organization_id']
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/accounts",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        self.initialized = True
                        logger.info("Coinbase exchange initialized successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Coinbase API error: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase exchange: {str(e)}")
            return False
            
    async def _authenticated_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """Make authenticated request to Coinbase Advanced Trading API"""
        await self._wait_for_rate_limit()
        
        timestamp = str(int(time.time()))
        request_path = f"/api/v3/brokerage{endpoint}"
        body = json.dumps(data) if data else ''
        
        try:
            signature = self._generate_signature(timestamp, method.upper(), request_path, body)
            
            headers = {
                'Content-Type': 'application/json',
                'CB-ACCESS-KEY': self.config['api_credentials']['api_key'],
                'CB-ACCESS-SIGN': signature,
                'CB-ACCESS-TIMESTAMP': timestamp,
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"
                if params:
                    # Convert params to query string
                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    url = f"{url}?{query_string}"
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        return json.loads(response_text)
                    else:
                        error_msg = f"Coinbase API error: {response.status} - {response_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in authenticated request: {str(e)}")
            raise
                
    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance from Coinbase"""
        try:
            response = await self._authenticated_request('GET', '/accounts')
            balances = {}
            
            for account in response.get('accounts', []):
                currency = account['currency']
                balances[currency] = {
                    'free': float(account.get('available_balance', {}).get('value', 0)),
                    'used': float(account.get('hold', {}).get('value', 0)),
                    'total': float(account.get('balance', {}).get('value', 0))
                }
                
            return balances
        except Exception as e:
            logger.error(f"Error fetching Coinbase balance: {str(e)}")
            raise
            
    async def fetch_market_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive market data from Coinbase"""
        try:
            # Parallel fetching of different data types
            ticker_task = create_tracked_task(self.fetch_ticker(symbol), name=f"ticker_{symbol}")
            orderbook_task = create_tracked_task(self.fetch_orderbook(symbol), name=f"orderbook_{symbol}")
            trades_task = create_tracked_task(self.fetch_recent_trades(symbol), name=f"trades_{symbol}")
            
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
            logger.error(f"Error fetching Coinbase market data for {symbol}: {str(e)}")
            raise
            
    async def _public_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Make public request to Coinbase Exchange API"""
        await self._wait_for_rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.public_url}{endpoint}"
                if params:
                    # Convert params to query string
                    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                    url = f"{url}?{query_string}"
                
                async with session.request(
                    method=method,
                    url=url
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        return json.loads(response_text)
                    else:
                        error_msg = f"Coinbase API error: {response.status} - {response_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in public request: {str(e)}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data from Coinbase Exchange"""
        try:
            response = await self._public_request('GET', f'/products/{symbol}/ticker')
            stats = await self._public_request('GET', f'/products/{symbol}/stats')
            
            return {
                'symbol': symbol,
                'last': float(response['price']),
                'bid': float(response.get('bid', 0)),
                'ask': float(response.get('ask', 0)),
                'volume': float(stats.get('volume', 0)),
                'timestamp': int(time.time() * 1000),
                'high': float(stats.get('high', 0)),
                'low': float(stats.get('low', 0)),
                'percentage': float(stats.get('price_change_percent', 0)),
                'index_price': float(response.get('price', 0)),
                'funding_rate': 0.0,  # Not available in spot
                'next_funding_time': None,  # Not available in spot
                'open_interest': 0.0  # Not available in spot
            }
        except Exception as e:
            logger.error(f"Error fetching Coinbase ticker for {symbol}: {str(e)}")
            raise
            
    async def fetch_orderbook(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        """Fetch orderbook data from Coinbase Exchange"""
        try:
            response = await self._public_request(
                'GET',
                f'/products/{symbol}/book',
                params={'level': min(3, limit)}  # Level 3 is the maximum depth
            )
            return {
                'symbol': symbol,
                'bids': [[float(bid[0]), float(bid[1])] for bid in response.get('bids', [])],
                'asks': [[float(ask[0]), float(ask[1])] for ask in response.get('asks', [])],
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.utcnow().isoformat(),
                'nonce': response.get('sequence')
            }
        except Exception as e:
            logger.error(f"Error fetching Coinbase orderbook for {symbol}: {str(e)}")
            raise
            
    async def fetch_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent trades from Coinbase Exchange"""
        try:
            response = await self._public_request(
                'GET',
                f'/products/{symbol}/trades',
                params={'limit': limit}
            )
            return [
                {
                    'id': trade.get('trade_id', str(i)),
                    'price': float(trade['price']),
                    'amount': float(trade['size']),
                    'cost': float(trade['price']) * float(trade['size']),
                    'side': trade['side'].lower(),
                    'timestamp': int(datetime.fromisoformat(trade['time'].replace('Z', '+00:00')).timestamp() * 1000),
                    'datetime': trade['time'],
                    'fee': None,
                    'type': trade.get('type', 'limit'),
                    'liquidation': False  # Not available in spot
                }
                for i, trade in enumerate(response)  # Response is a list of trades
            ]
        except Exception as e:
            logger.error(f"Error fetching Coinbase trades for {symbol}: {str(e)}")
            raise
            
    async def fetch_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical kline data from Coinbase"""
        try:
            params = {
                'granularity': interval,
                'limit': limit
            }
            
            if start_time:
                params['start'] = datetime.fromtimestamp(start_time / 1000).isoformat()
            if end_time:
                params['end'] = datetime.fromtimestamp(end_time / 1000).isoformat()
                
            response = await self._authenticated_request(
                'GET',
                f'/products/{symbol}/candles',
                params=params
            )
            
            return [
                {
                    'timestamp': int(candle['time'] * 1000),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume']),
                    'timeframe': interval,
                    'symbol': symbol
                }
                for candle in response.get('candles', [])
            ]
        except Exception as e:
            logger.error(f"Error fetching Coinbase klines for {symbol}: {str(e)}")
            raise
            
    async def close(self):
        """Close exchange connection"""
        if self.session:
            await self.session.close() 
    async def fetch_orders(self, symbol: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch orders from Coinbase"""
        try:
            params = {}
            if symbol:
                params['product_id'] = symbol
            if limit:
                params['limit'] = limit
                
            response = await self._authenticated_request(
                'GET',
                '/orders',
                params=params
            )
            
            return [
                {
                    'id': order['order_id'],
                    'client_id': order.get('client_order_id'),
                    'symbol': order['product_id'],
                    'status': order['status'].lower(),
                    'type': order['order_type'].lower(),
                    'side': order['side'].lower(),
                    'price': float(order.get('limit_price', 0)),
                    'amount': float(order.get('base_size', 0)),
                    'filled': float(order.get('filled_size', 0)),
                    'remaining': float(order.get('remaining_size', 0)),
                    'cost': float(order.get('filled_size', 0)) * float(order.get('average_filled_price', 0)),
                    'average': float(order.get('average_filled_price', 0)),
                    'timestamp': int(datetime.fromisoformat(order['created_time'].replace('Z', '+00:00')).timestamp() * 1000),
                    'datetime': order['created_time'],
                    'lastTradeTimestamp': int(datetime.fromisoformat(order.get('last_fill_time', order['created_time']).replace('Z', '+00:00')).timestamp() * 1000) if order.get('last_fill_time') else None,
                    'fee': {
                        'cost': float(order.get('total_fees', 0)),
                        'currency': order.get('quote_currency', 'USD')
                    }
                }
                for order in response.get('orders', [])
            ]
        except Exception as e:
            logger.error(f"Error fetching Coinbase orders: {str(e)}")
            raise

    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch positions from Coinbase"""
        try:
            response = await self._authenticated_request('GET', '/positions')
            return [
                {
                    'symbol': position['product_id'],
                    'size': float(position.get('position_size', 0)),
                    'notional': float(position.get('notional_size', 0)),
                    'entry_price': float(position.get('entry_price', 0)),
                    'mark_price': float(position.get('mark_price', 0)),
                    'unrealized_pnl': float(position.get('unrealized_pnl', 0)),
                    'liquidation_price': float(position.get('liquidation_price', 0)),
                    'leverage': float(position.get('leverage', 1)),
                    'timestamp': int(time.time() * 1000)
                }
                for position in response.get('positions', [])
                if not symbol or position['product_id'] == symbol
            ]
        except Exception as e:
            logger.error(f"Error fetching Coinbase positions: {str(e)}")
            raise

    async def fetch_status(self) -> Dict[str, Any]:
        """Fetch Coinbase exchange status"""
        try:
            response = await self._authenticated_request('GET', '/products/status')
            return {
                'status': response.get('status', 'unknown'),
                'updated': int(time.time() * 1000),
                'eta': None,
                'url': None
            }
        except Exception as e:
            logger.error(f"Error fetching Coinbase status: {str(e)}")
            raise

    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets from Coinbase"""
        try:
            response = await self._authenticated_request('GET', '/products')
            
            self.markets = {}
            result = []
            
            for product in response.get('products', []):
                market = {
                    'id': product['product_id'],
                    'symbol': product['product_id'],
                    'base': product['base_currency'],
                    'quote': product['quote_currency'],
                    'baseId': product['base_currency'],
                    'quoteId': product['quote_currency'],
                    'active': product['status'] == 'online',
                    'type': 'spot',
                    'spot': True,
                    'margin': False,
                    'future': False,
                    'swap': False,
                    'option': False,
                    'contract': False,
                    'precision': {
                        'price': self._get_precision(product.get('quote_increment', '0.00000001')),
                        'amount': self._get_precision(product.get('base_increment', '0.00000001'))
                    },
                    'limits': {
                        'amount': {
                            'min': float(product.get('base_min_size', 0)),
                            'max': float(product.get('base_max_size', float('inf')))
                        },
                        'price': {
                            'min': float(product.get('quote_increment', 0)),
                            'max': float('inf')
                        },
                        'cost': {
                            'min': float(product.get('min_market_funds', 0)),
                            'max': float(product.get('max_market_funds', float('inf')))
                        }
                    },
                    'info': product
                }
                
                self.markets[market['symbol']] = market
                result.append(market)
                
            return result
        except Exception as e:
            logger.error(f"Error fetching Coinbase markets: {str(e)}")
            raise

    def _get_precision(self, increment: str) -> int:
        """Calculate precision from increment string"""
        try:
            return abs(decimal.Decimal(increment).as_tuple().exponent)
        except:
            return 8  # Default precision

    async def fetch_my_trades(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch user's trades"""
        try:
            params = {}
            if symbol:
                params['product_id'] = symbol
            if limit:
                params['limit'] = limit
            if since:
                params['start_date'] = datetime.fromtimestamp(since / 1000).isoformat()
                
            response = await self._authenticated_request(
                'GET',
                '/fills',
                params=params
            )
            
            return [
                {
                    'id': fill['trade_id'],
                    'order': fill['order_id'],
                    'symbol': fill['product_id'],
                    'side': fill['side'].lower(),
                    'price': float(fill['price']),
                    'amount': float(fill['size']),
                    'cost': float(fill['price']) * float(fill['size']),
                    'fee': {
                        'cost': float(fill.get('fee', 0)),
                        'currency': fill.get('fee_currency', 'USD')
                    },
                    'timestamp': int(datetime.fromisoformat(fill['trade_time'].replace('Z', '+00:00')).timestamp() * 1000),
                    'datetime': fill['trade_time'],
                    'type': fill.get('order_type', 'limit').lower(),
                    'info': fill
                }
                for fill in response.get('fills', [])
            ]
        except Exception as e:
            logger.error(f"Error fetching Coinbase trades: {str(e)}")
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
        """Create a new order on Coinbase"""
        try:
            order_data = {
                'product_id': symbol,
                'side': side.lower(),
                'order_type': type.lower(),
                'base_size': str(amount)
            }

            if price is not None:
                order_data['limit_price'] = str(price)

            if params:
                order_data.update(params)

            response = await self._authenticated_request(
                'POST',
                '/orders',
                data=order_data
            )

            return {
                'id': response['order_id'],
                'client_id': response.get('client_order_id'),
                'timestamp': int(datetime.fromisoformat(response['created_time'].replace('Z', '+00:00')).timestamp() * 1000),
                'datetime': response['created_time'],
                'symbol': response['product_id'],
                'type': response['order_type'].lower(),
                'side': response['side'].lower(),
                'price': float(response.get('limit_price', 0)),
                'amount': float(response.get('base_size', 0)),
                'filled': float(response.get('filled_size', 0)),
                'remaining': float(response.get('remaining_size', 0)),
                'status': response['status'].lower(),
                'fee': {
                    'cost': float(response.get('total_fees', 0)),
                    'currency': response.get('quote_currency', 'USD')
                }
            }
        except Exception as e:
            logger.error(f"Error creating Coinbase order: {str(e)}")
            raise

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an existing order on Coinbase"""
        try:
            response = await self._authenticated_request(
                'DELETE',
                f'/orders/{order_id}'
            )
            
            return {
                'id': response['order_id'],
                'symbol': response.get('product_id'),
                'status': 'canceled',
                'timestamp': int(time.time() * 1000),
                'datetime': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error canceling Coinbase order: {str(e)}")
            raise

    async def update_position(self, symbol: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update position parameters on Coinbase"""
        try:
            # Coinbase doesn't support direct position updates
            # We need to create new orders to modify positions
            position = await self.fetch_positions(symbol)
            if not position:
                raise ValueError(f"No position found for {symbol}")

            orders = []
            if 'stopLoss' in params:
                orders.append(await self.create_order(
                    symbol=symbol,
                    type='stop',
                    side='sell' if position[0]['size'] > 0 else 'buy',
                    amount=abs(position[0]['size']),
                    price=params['stopLoss']
                ))

            if 'takeProfit' in params:
                orders.append(await self.create_order(
                    symbol=symbol,
                    type='limit',
                    side='sell' if position[0]['size'] > 0 else 'buy',
                    amount=abs(position[0]['size']),
                    price=params['takeProfit']
                ))

            return {
                'symbol': symbol,
                'orders': orders,
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"Error updating Coinbase position: {str(e)}")
            raise 
