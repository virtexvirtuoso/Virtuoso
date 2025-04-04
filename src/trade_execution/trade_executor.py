# src/trade_execution/trade_executor.py

import logging
import time
import hmac
import hashlib
import json
import urllib.parse
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
import ccxt.async_support as ccxt
from decimal import Decimal, ROUND_DOWN

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TradeExecutor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.api_key = config['exchanges']['bybit']['api_credentials']['api_key']
        self.api_secret = config['exchanges']['bybit']['api_credentials']['api_secret']
        self.base_url = config['exchanges']['bybit'].get('endpoint', 'https://api.bybit.com')
        self.is_demo = "api-demo.bybit.com" in self.base_url
        
        # Position management settings
        self.position_config = config.get('position_manager', {})
        self.base_position_pct = self.position_config.get('base_position_pct', 0.03)
        self.min_confluence_score = self.position_config.get('min_confluence_score', 70)
        self.trailing_stop_pct = self.position_config.get('trailing_stop_pct', 0.02)
        self.scale_factor = self.position_config.get('scale_factor', 0.01)
        self.max_position_pct = self.position_config.get('max_position_pct', 0.10)
        
        # Create an async CCXT client for Bybit
        self.exchange = ccxt.bybit({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'urls': {
                'api': self.base_url,
            }
        })
        
        # Session for direct API calls when needed
        self._session = None
        
        # Active positions tracking
        self.active_positions = {}

    async def initialize(self):
        """Initialize the executor by creating HTTP session and loading market data"""
        self._session = aiohttp.ClientSession()
        
        # Load and store market data for symbols
        await self.exchange.load_markets()
        logger.info(f"Initialized TradeExecutor with {'demo' if self.is_demo else 'live'} environment")
        
        if self.is_demo:
            # Apply for demo funds if in demo mode
            await self._apply_for_demo_funds()

    async def close(self):
        """Close connections and clean up resources"""
        if self._session:
            await self._session.close()
        
        if self.exchange:
            await self.exchange.close()

    async def _apply_for_demo_funds(self):
        """Request demo trading funds if using demo environment"""
        if not self.is_demo:
            return
        
        try:
            # Apply for demo USDT
            request_data = {
                "adjustType": 0,
                "utaDemoApplyMoney": [
                    {
                        "coin": "USDT",
                        "amountStr": "100000"
                    }
                ]
            }
            response = await self._signed_request(
                "/v5/account/demo-apply-money",
                request_data,
                "POST"
            )
            
            if response.get('retCode') == 0:
                logger.info("Successfully applied for demo trading funds")
            else:
                logger.warning(f"Failed to apply for demo funds: {response.get('retMsg')}")
        except Exception as e:
            logger.error(f"Error applying for demo funds: {str(e)}")

    async def _get_wallet_balance(self) -> Dict[str, Any]:
        """Get wallet balance information"""
        try:
            response = await self._signed_request("/v5/account/wallet-balance", {"accountType": "UNIFIED"}, "GET")
            if response.get('retCode') == 0:
                return response.get('result', {})
            else:
                logger.error(f"Failed to get wallet balance: {response.get('retMsg')}")
                return {}
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return {}

    async def _signed_request(self, endpoint: str, params: Dict[str, Any], method: str) -> Dict[str, Any]:
        """
        Create and send a signed request to Bybit API
        
        Args:
            endpoint: API endpoint
            params: Request parameters
            method: HTTP method (GET, POST, etc)
            
        Returns:
            API response as dictionary
        """
        timestamp = str(int(time.time() * 1000))
        params['api_key'] = self.api_key
        params['timestamp'] = timestamp
        params['recv_window'] = '5000'
        
        # Sort parameters by key
        sorted_params = dict(sorted(params.items()))
        
        # Create signature
        query_string = urllib.parse.urlencode(sorted_params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to parameters
        sorted_params['sign'] = signature
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                async with self._session.get(url, params=sorted_params) as response:
                    return await response.json()
            elif method == "POST":
                headers = {'Content-Type': 'application/json'}
                # For POST requests, remove signature from body and add as header
                sign = sorted_params.pop('sign')
                async with self._session.post(
                    url, 
                    json=sorted_params,
                    headers={
                        'X-BAPI-API-KEY': self.api_key,
                        'X-BAPI-SIGN': sign,
                        'X-BAPI-TIMESTAMP': timestamp,
                        'X-BAPI-RECV-WINDOW': '5000',
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"API request error: {str(e)}")
            raise

    async def get_market_prism_score(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate a complete market prism score based on the six dimensions
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dictionary with scores for each dimension and overall score
        """
        # This would typically integrate with your analysis engine
        # For implementation, we'll use a placeholder that returns random scores
        # In a real implementation, this would call your market analysis system
        
        # Placeholder implementation - replace with actual analysis
        import random
        
        technical_score = random.uniform(0, 100)
        volume_score = random.uniform(0, 100)
        orderflow_score = random.uniform(0, 100)
        orderbook_score = random.uniform(0, 100)
        price_structure_score = random.uniform(0, 100)
        sentiment_score = random.uniform(0, 100)
        
        # Weight the dimensions according to current market conditions
        # These weights would normally be dynamically adjusted
        weights = {
            'technical': 0.25,
            'volume': 0.15,
            'orderflow': 0.20,
            'orderbook': 0.15,
            'price_structure': 0.15,
            'sentiment': 0.10
        }
        
        # Calculate overall score
        overall_score = (
            technical_score * weights['technical'] +
            volume_score * weights['volume'] +
            orderflow_score * weights['orderflow'] +
            orderbook_score * weights['orderbook'] +
            price_structure_score * weights['price_structure'] +
            sentiment_score * weights['sentiment']
        )
        
        return {
            'symbol': symbol,
            'scores': {
                'technical': technical_score,
                'volume': volume_score,
                'orderflow': orderflow_score,
                'orderbook': orderbook_score,
                'price_structure': price_structure_score,
                'sentiment': sentiment_score,
                'overall': overall_score
            },
            'weights': weights,
            'signal': self._interpret_score(overall_score)
        }
    
    def _interpret_score(self, score: float) -> Dict[str, Any]:
        """
        Interpret a score and generate trading signals
        
        Args:
            score: Overall confluence score (0-100)
            
        Returns:
            Dictionary with signal information
        """
        if score >= self.min_confluence_score:
            return {
                'direction': 'long',
                'strength': (score - self.min_confluence_score) / (100 - self.min_confluence_score),
                'action': 'buy'
            }
        elif score <= (100 - self.min_confluence_score):  # e.g., score <= 30 if min_confluence_score is 70
            return {
                'direction': 'short',
                'strength': ((100 - self.min_confluence_score) - score) / (100 - self.min_confluence_score),
                'action': 'sell'
            }
        else:
            return {
                'direction': 'neutral',
                'strength': 0,
                'action': 'hold'
            }

    def calculate_position_size(self, symbol: str, side: str, available_balance: float, 
                               confluence_score: float) -> float:
        """
        Calculate position size based on confluence score, account balance, and risk parameters
        
        Args:
            symbol: Trading pair
            side: Trade side (buy/sell)
            available_balance: Available balance to trade with
            confluence_score: The overall confluence score (0-100)
            
        Returns:
            Position size in base currency
        """
        # Base position is a percentage of available balance
        base_position = available_balance * self.base_position_pct
        
        # Scale position based on signal strength
        if side == 'buy' and confluence_score > 75:
            # Increase position for stronger long signals
            score_above_threshold = confluence_score - 75
            scaling_factor = min(score_above_threshold * self.scale_factor, 
                               self.max_position_pct - self.base_position_pct)
            position_size = base_position + (available_balance * scaling_factor)
        elif side == 'sell' and confluence_score < 25:
            # Increase position for stronger short signals
            score_below_threshold = 25 - confluence_score
            scaling_factor = min(score_below_threshold * self.scale_factor,
                               self.max_position_pct - self.base_position_pct)
            position_size = base_position + (available_balance * scaling_factor)
        else:
            # Use base position for moderate signals
            position_size = base_position
        
        # Cap at maximum position size
        max_position = available_balance * self.max_position_pct
        position_size = min(position_size, max_position)
        
        return position_size

    async def execute_trade(self, symbol: str, side: str, quantity: float, 
                           stop_loss_pct: Optional[float] = None,
                           take_profit_pct: Optional[float] = None,
                           is_trailing_stop: bool = True) -> Dict[str, Any]:
        """
        Execute a trade with optional stop loss and take profit
        
        Args:
            symbol: Trading pair
            side: Trade side (buy/sell)
            quantity: Trade quantity
            stop_loss_pct: Optional stop loss percentage
            take_profit_pct: Optional take profit percentage
            is_trailing_stop: Whether to use trailing stop
            
        Returns:
            Trade execution result
        """
        logger.debug(f"Executing trade - Symbol: {symbol}, Side: {side}, Quantity: {quantity}")
        
        try:
            # Convert CCXT symbol format (BTC/USDT) to Bybit format (BTCUSDT)
            bybit_symbol = symbol.replace('/', '')
            
            # Get current market price
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Prepare order parameters
            order_params = {
                "category": "spot",
                "symbol": bybit_symbol,
                "side": side.upper(),
                "orderType": "Market",
                "qty": str(quantity),
            }
            
            # Place the main order
            order_result = await self._signed_request(
                "/v5/order/create",
                order_params,
                "POST"
            )
            
            if order_result.get('retCode') != 0:
                logger.error(f"Order failed: {order_result.get('retMsg')}")
                return {'success': False, 'error': order_result.get('retMsg')}
            
            order_id = order_result.get('result', {}).get('orderId')
            
            # Set stop loss if specified
            if stop_loss_pct and order_id:
                await self._set_stop_loss(
                    symbol=bybit_symbol,
                    side=side,
                    entry_price=current_price,
                    stop_pct=stop_loss_pct,
                    quantity=quantity,
                    is_trailing=is_trailing_stop
                )
            
            # Set take profit if specified
            if take_profit_pct and order_id:
                await self._set_take_profit(
                    symbol=bybit_symbol,
                    side=side,
                    entry_price=current_price,
                    take_profit_pct=take_profit_pct,
                    quantity=quantity
                )
            
            # Track the position
            self.active_positions[order_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': current_price,
                'entry_time': time.time(),
                'order_id': order_id
            }
            
            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': current_price
            }
            
        except Exception as e:
            logger.error(f"Trade execution error: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def _set_stop_loss(self, symbol: str, side: str, entry_price: float, 
                            stop_pct: float, quantity: float, is_trailing: bool = True) -> Dict[str, Any]:
        """
        Set a stop loss order for a position
        
        Args:
            symbol: Trading pair symbol
            side: Original order side (buy/sell)
            entry_price: Entry price of the position
            stop_pct: Stop loss percentage
            quantity: Position quantity
            is_trailing: Whether to use trailing stop
            
        Returns:
            Stop loss order result
        """
        # Calculate stop price
        if side.lower() == 'buy':
            stop_price = entry_price * (1 - stop_pct)
            stop_side = 'Sell'
        else:
            stop_price = entry_price * (1 + stop_pct)
            stop_side = 'Buy'
        
        # Round to appropriate precision
        stop_price = round(stop_price, 6)
        
        # Prepare stop loss parameters
        stop_params = {
            "category": "spot", 
            "symbol": symbol,
            "side": stop_side,
            "orderType": "Market",
            "qty": str(quantity),
            "triggerDirection": 2 if side.lower() == 'buy' else 1,
            "triggerPrice": str(stop_price),
        }
        
        if is_trailing:
            # Add trailing stop parameters
            stop_params["orderType"] = "Market"
            stop_params["triggerType"] = "TrailingStop"
            stop_params["tpslMode"] = "Partial"
            stop_params["slTriggerBy"] = "LastPrice"
            
            # Calculate trailing distance as percentage of entry price
            trailing_distance = entry_price * stop_pct
            stop_params["trailingValue"] = str(round(trailing_distance, 6))
        
        try:
            # Place the stop loss order
            result = await self._signed_request(
                "/v5/order/create",
                stop_params,
                "POST"
            )
            
            if result.get('retCode') == 0:
                logger.info(f"Stop loss set for {symbol} at {stop_price}")
                return {'success': True, 'stop_price': stop_price}
            else:
                logger.error(f"Failed to set stop loss: {result.get('retMsg')}")
                return {'success': False, 'error': result.get('retMsg')}
        except Exception as e:
            logger.error(f"Error setting stop loss: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def _set_take_profit(self, symbol: str, side: str, entry_price: float,
                              take_profit_pct: float, quantity: float) -> Dict[str, Any]:
        """
        Set a take profit order for a position
        
        Args:
            symbol: Trading pair symbol
            side: Original order side (buy/sell)
            entry_price: Entry price of the position
            take_profit_pct: Take profit percentage
            quantity: Position quantity
            
        Returns:
            Take profit order result
        """
        # Calculate take profit price
        if side.lower() == 'buy':
            take_profit_price = entry_price * (1 + take_profit_pct)
            tp_side = 'Sell'
        else:
            take_profit_price = entry_price * (1 - take_profit_pct)
            tp_side = 'Buy'
        
        # Round to appropriate precision
        take_profit_price = round(take_profit_price, 6)
        
        # Prepare take profit parameters
        tp_params = {
            "category": "spot",
            "symbol": symbol,
            "side": tp_side,
            "orderType": "Limit",
            "qty": str(quantity),
            "price": str(take_profit_price),
            "timeInForce": "GoodTillCancel",
            "reduceOnly": True
        }
        
        try:
            # Place the take profit order
            result = await self._signed_request(
                "/v5/order/create",
                tp_params,
                "POST"
            )
            
            if result.get('retCode') == 0:
                logger.info(f"Take profit set for {symbol} at {take_profit_price}")
                return {'success': True, 'take_profit_price': take_profit_price}
            else:
                logger.error(f"Failed to set take profit: {result.get('retMsg')}")
                return {'success': False, 'error': result.get('retMsg')}
        except Exception as e:
            logger.error(f"Error setting take profit: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """
        Cancel all open orders for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Result of cancellation operation
        """
        try:
            # Convert CCXT symbol format to Bybit format
            bybit_symbol = symbol.replace('/', '')
            
            # Prepare parameters
            params = {
                "category": "spot",
                "symbol": bybit_symbol
            }
            
            # Send cancel all orders request
            result = await self._signed_request(
                "/v5/order/cancel-all",
                params,
                "POST"
            )
            
            if result.get('retCode') == 0:
                logger.info(f"Cancelled all orders for {symbol}")
                return {'success': True}
            else:
                logger.error(f"Failed to cancel orders: {result.get('retMsg')}")
                return {'success': False, 'error': result.get('retMsg')}
        except Exception as e:
            logger.error(f"Error cancelling orders: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Returns:
            List of open positions
        """
        try:
            # For spot trading, we need to get open orders
            response = await self._signed_request(
                "/v5/order/realtime",
                {"category": "spot"},
                "GET"
            )
            
            if response.get('retCode') == 0:
                return response.get('result', {}).get('list', [])
            else:
                logger.error(f"Failed to get open positions: {response.get('retMsg')}")
                return []
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            return []

    async def simulate_trade(self, symbol: str, side: str, quantity: float, 
                            confluence_score: float) -> Dict[str, Any]:
        """
        Simulate a trade without actual execution
        
        Args:
            symbol: Trading pair
            side: Trade side (buy/sell)
            quantity: Trade quantity
            confluence_score: Confluence score for this trade
            
        Returns:
            Simulated trade result
        """
        logger.debug(f"Simulated trade - Symbol: {symbol}, Side: {side}, Quantity: {quantity}")
        
        # Get current market price
        ticker = await self.exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Calculate stop loss price
        if side.lower() == 'buy':
            stop_price = current_price * (1 - self.trailing_stop_pct)
        else:
            stop_price = current_price * (1 + self.trailing_stop_pct)
        
        # Generate a simulated order ID
        import uuid
        order_id = str(uuid.uuid4())
        
        return {
            'success': True,
            'simulated': True,
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': current_price,
            'confluence_score': confluence_score,
            'stop_price': stop_price,
            'timestamp': time.time()
        }

    async def monitor_positions(self):
        """
        Monitor and manage active positions
        Updates trailing stops and checks for position closures
        """
        if not self.active_positions:
            return
        
        positions_to_update = list(self.active_positions.items())
        
        for order_id, position in positions_to_update:
            try:
                symbol = position['symbol']
                
                # Get current price
                ticker = await self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Check if position needs to be updated or closed
                entry_price = position['entry_price']
                side = position['side']
                
                # Update position in tracking dict
                self.active_positions[order_id]['current_price'] = current_price
                
                # Calculate current P&L
                if side.lower() == 'buy':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price
                
                self.active_positions[order_id]['pnl_pct'] = pnl_pct
                
                logger.debug(f"Position {symbol} {side} - Entry: {entry_price}, Current: {current_price}, P&L: {pnl_pct:.2%}")
                
            except Exception as e:
                logger.error(f"Error monitoring position {order_id}: {str(e)}")

    async def analyze_and_trade(self, symbols: List[str], dry_run: bool = False):
        """
        Analyze symbols and execute trades based on market prism scores
        
        Args:
            symbols: List of symbols to analyze
            dry_run: If True, simulate trades instead of executing them
        """
        # Get account balance
        balance_info = await self._get_wallet_balance()
        
        # Calculate total USDT available (adjust for your account structure)
        total_balance = 0
        account_info = balance_info.get('list', [])
        for account in account_info:
            coins = account.get('coin', [])
            for coin in coins:
                if coin.get('coin') == 'USDT':
                    total_balance += float(coin.get('availableToWithdraw', 0))
        
        logger.info(f"Total available balance: {total_balance} USDT")
        
        for symbol in symbols:
            try:
                # Get market prism score
                prism_result = await self.get_market_prism_score(symbol)
                overall_score = prism_result['scores']['overall']
                signal = prism_result['signal']
                
                logger.info(f"{symbol} - Overall score: {overall_score:.2f}, Signal: {signal['direction']}")
                
                # Check if we should take a position
                if signal['action'] in ['buy', 'sell']:
                    # Calculate position size
                    position_size = self.calculate_position_size(
                        symbol=symbol,
                        side=signal['action'],
                        available_balance=total_balance,
                        confluence_score=overall_score
                    )
                    
                    # Execute or simulate the trade
                    if dry_run:
                        result = await self.simulate_trade(
                            symbol=symbol,
                            side=signal['action'],
                            quantity=position_size,
                            confluence_score=overall_score
                        )
                        logger.info(f"Simulated {signal['action']} for {symbol}: {position_size} at {result['price']}")
                    else:
                        result = await self.execute_trade(
                            symbol=symbol,
                            side=signal['action'],
                            quantity=position_size,
                            stop_loss_pct=self.trailing_stop_pct,
                            is_trailing_stop=True
                        )
                        
                        if result['success']:
                            logger.info(f"Executed {signal['action']} for {symbol}: {position_size} at {result['price']}")
                        else:
                            logger.error(f"Trade execution failed: {result.get('error')}")
                else:
                    logger.info(f"No trading signal for {symbol}")
            
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue
        
        # Monitor existing positions
        await self.monitor_positions()
