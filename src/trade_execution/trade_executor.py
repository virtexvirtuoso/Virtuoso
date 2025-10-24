# src/trade_execution/trade_executor.py

import logging
import time
import hmac
import hashlib
import json
import urllib.parse
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
import aiohttp
import ccxt.async_support as ccxt
from decimal import Decimal, ROUND_DOWN
import os
import uuid
from dotenv import load_dotenv

# Add import for AlertManager
from src.monitoring.alert_manager import AlertManager

logger = logging.getLogger(__name__)

class TradeExecutor:
    """
    Advanced trade execution engine with market prism analysis integration
    """
    
    def __init__(self, config: Dict[str, Any], alert_manager: Optional['AlertManager'] = None):
        """
        Initialize the TradeExecutor
        
        Args:
            config: Configuration dictionary containing API credentials and settings
            alert_manager: Optional AlertManager instance. If not provided, will create one.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extract exchange configuration
        exchange_config = config.get('exchanges', {}).get('bybit', {})
        if not exchange_config:
            raise ValueError("Bybit exchange configuration not found")
        
        # API credentials
        self.api_key = exchange_config.get('api_key')
        self.api_secret = exchange_config.get('api_secret')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("API key and secret are required")
        
        # Trading configuration
        trading_config = config.get('trading', {})
        self.is_demo = trading_config.get('demo_mode', True)
        self.max_position_size = trading_config.get('max_position_size', 0.1)  # 10% of balance
        self.default_leverage = trading_config.get('default_leverage', 1)
        # Use long/short with backward compatibility for buy/sell
        self.long_threshold = trading_config.get('long_threshold', trading_config.get('buy_threshold', 70))
        self.short_threshold = trading_config.get('short_threshold', trading_config.get('sell_threshold', 30))
        
        # Risk management
        risk_config = config.get('risk_management', {})
        self.max_daily_loss = risk_config.get('max_daily_loss', 0.05)  # 5%
        self.max_drawdown = risk_config.get('max_drawdown', 0.10)  # 10%
        self.stop_loss_pct = risk_config.get('default_stop_loss', 0.02)  # 2%
        self.take_profit_pct = risk_config.get('default_take_profit', 0.04)  # 4%
        
        # Exchange setup
        if self.is_demo:
            self.base_url = "https://api-testnet.bybit.com"
            self.logger.info("Using Bybit testnet (demo mode)")
        else:
            self.base_url = "https://api.bybit.com"
            self.logger.info("Using Bybit mainnet (live trading)")
        
        # Initialize exchange
        self.exchange = ccxt.bybit({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'sandbox': self.is_demo,
            'enableRateLimit': True,
        })
        
        # HTTP session for direct API calls
        self._session = None
        
        # Active positions tracking
        self.active_positions = {}
        
        # Initialize AlertManager
        if alert_manager:
            self.alert_manager = alert_manager
            self.logger.info("Using provided AlertManager instance")
        else:
            # Import AlertManager here to avoid circular import
            from src.monitoring.alert_manager import AlertManager
            self.alert_manager = AlertManager(config)
            self.logger.info("Created new AlertManager instance")

    async def initialize(self):
        """Initialize the executor by creating HTTP session and loading market data"""
        self._session = aiohttp.ClientSession()
        
        # Load and store market data for symbols
        await self.exchange.load_markets()
        logger.info(f"Initialized TradeExecutor with {'demo' if self.is_demo else 'live'} environment")
        
        if self.is_demo:
            # Apply for demo trading funds if in demo mode
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
        
        # Use real confluence analyzer for actual analysis
        try:
            # Import the real confluence analyzer
            from src.core.analysis.confluence import ConfluenceAnalyzer
            
            # Get or create analyzer instance
            if not hasattr(self, '_confluence_analyzer'):
                self._confluence_analyzer = ConfluenceAnalyzer()
            
            # Get real market data for analysis
            market_data = {}
            if hasattr(self, 'market_data_manager'):
                market_data = self.market_data_manager.get_market_data(symbol)
            
            # Perform real analysis
            analyzer = getattr(self, '_confluence_analyzer', None)
            if not (analyzer and hasattr(analyzer, 'analyze') and callable(getattr(analyzer, 'analyze'))):
                logger.debug(f"_confluence_analyzer missing or analyze() not callable; using fallback for {symbol}")
                # Return fallback mock analysis result
                return {
                    'confluence_score': 50.0,
                    'technical_score': 0.5,
                    'volume_score': 0.5,
                    'orderflow_score': 0.5,
                    'sentiment_score': 0.5,
                    'components': {},
                    'signal': 'neutral',
                    'timestamp': time.time() * 1000
                }

            try:
                analysis_result = analyzer.analyze(market_data)
            except Exception as e:
                logger.debug(f"_confluence_analyzer.analyze error for {symbol}: {e}")
                # Return fallback mock analysis result
                return {
                    'confluence_score': 50.0,
                    'technical_score': 0.5,
                    'volume_score': 0.5,
                    'orderflow_score': 0.5,
                    'sentiment_score': 0.5,
                    'components': {},
                    'signal': 'neutral',
                    'timestamp': time.time() * 1000
                }
            
            # Extract scores from real analysis
            technical_score = analysis_result.get('technical_score', 0) * 100
            volume_score = analysis_result.get('volume_score', 0) * 100
            orderflow_score = analysis_result.get('orderflow_score', 0) * 100
            orderbook_score = analysis_result.get('orderbook_score', 0) * 100
            price_structure_score = analysis_result.get('price_structure_score', 0) * 100
            sentiment_score = analysis_result.get('sentiment_score', 0) * 100
            
        except Exception as e:
            self.logger.error(f"Failed to get real confluence scores: {e}")
            # Return None to indicate analysis failure rather than random data
            return None
        
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
        if score >= self.long_threshold:
            return {
                'direction': 'long',
                'strength': (score - self.long_threshold) / (100 - self.long_threshold),
                'action': 'buy'
            }
        elif score <= self.short_threshold:
            return {
                'direction': 'short',
                'strength': (self.short_threshold - score) / self.short_threshold,
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
        # First check if the signal meets minimum threshold
        if side == 'buy' and confluence_score < self.long_threshold:
            # Don't take long positions if score is below long threshold
            return 0.0
        elif side == 'sell' and confluence_score > self.short_threshold:
            # Don't take short positions if score is above short threshold
            return 0.0

        # Base position is a percentage of available balance
        base_position = available_balance * self.max_position_size

        # Scale position based on signal strength
        # For buy, calculate scaling relative to long threshold
        if side == 'buy' and confluence_score > self.long_threshold:
            # Increase position for stronger long signals
            score_above_threshold = confluence_score - self.long_threshold
            scaling_factor = min(score_above_threshold * 0.01,
                               self.max_position_size - self.max_position_size)
            position_size = base_position + (available_balance * scaling_factor)
        # For sell, calculate scaling relative to short threshold
        elif side == 'sell' and confluence_score < self.short_threshold:
            # Increase position for stronger short signals
            score_below_threshold = self.short_threshold - confluence_score
            scaling_factor = min(score_below_threshold * 0.01,
                               self.max_position_size - self.max_position_size)
            position_size = base_position + (available_balance * scaling_factor)
        else:
            # Use base position for moderate signals
            position_size = base_position
        
        # Cap at maximum position size
        max_position = available_balance * self.max_position_size
        position_size = min(position_size, max_position)
        
        return position_size

    async def execute_trade(self, symbol: str, side: str, quantity: float, 
                           stop_loss_pct: Optional[float] = None,
                           take_profit_pct: Optional[float] = None,
                           is_trailing_stop: bool = True,
                           confluence_score: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a trade with optional stop loss and take profit
        
        Args:
            symbol: Trading pair
            side: Trade side (buy/sell)
            quantity: Trade quantity
            stop_loss_pct: Optional stop loss percentage
            take_profit_pct: Optional take profit percentage
            is_trailing_stop: Whether to use trailing stop
            confluence_score: Confluence score that triggered this trade
            
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
            stop_loss_set = False
            stop_loss_result = None
            if stop_loss_pct and order_id:
                stop_loss_result = await self._set_stop_loss(
                    symbol=bybit_symbol,
                    side=side,
                    entry_price=current_price,
                    stop_pct=stop_loss_pct,
                    quantity=quantity,
                    is_trailing=is_trailing_stop
                )
                stop_loss_set = stop_loss_result.get('success', False)
            
            # Set take profit if specified
            take_profit_set = False
            take_profit_result = None
            if take_profit_pct and order_id:
                take_profit_result = await self._set_take_profit(
                    symbol=bybit_symbol,
                    side=side,
                    entry_price=current_price,
                    take_profit_pct=take_profit_pct,
                    quantity=quantity
                )
                take_profit_set = take_profit_result.get('success', False)
            
            # Track the position
            self.active_positions[order_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': current_price,
                'entry_time': time.time(),
                'order_id': order_id
            }
            
            # Calculate USD value of the position
            position_size_usd = quantity * current_price
            
            # Send trade execution alert
            try:
                # Generate a unique transaction ID
                transaction_id = str(uuid.uuid4())[:8]
                
                # Send alert for the executed trade
                await self.alert_manager.send_trade_execution_alert(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=current_price,
                    trade_type="entry",
                    order_id=order_id,
                    transaction_id=transaction_id,
                    confluence_score=confluence_score,
                    stop_loss_pct=stop_loss_pct if stop_loss_set else None,
                    take_profit_pct=take_profit_pct if take_profit_set else None,
                    position_size_usd=position_size_usd,
                    exchange="Bybit"
                )
                logger.info(f"Sent trade execution alert for {symbol}")
            except Exception as alert_error:
                logger.error(f"Error sending trade execution alert: {str(alert_error)}")
            
            return {
                'success': True,
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': current_price,
                'stop_loss_set': stop_loss_set,
                'take_profit_set': take_profit_set
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
        
        # Calculate score-based stop loss instead of position-based
        stop_loss_pct = self.calculate_score_based_stop_loss(
            side=side,
            confluence_score=confluence_score
        )
        
        # Calculate stop loss price
        if side.lower() == 'buy':
            stop_price = current_price * (1 - stop_loss_pct)
        else:
            stop_price = current_price * (1 + stop_loss_pct)
        
        # Generate a simulated order ID
        order_id = str(uuid.uuid4())
        
        # Calculate position size in USD
        position_size_usd = quantity * current_price
        
        # Send simulated trade execution alert
        try:
            # Generate a unique transaction ID
            transaction_id = str(uuid.uuid4())[:8]
            
            # Send alert for the simulated trade
            await self.alert_manager.send_trade_execution_alert(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=current_price,
                trade_type="entry",
                order_id=f"sim-{order_id[:8]}",  # Add 'sim-' prefix to distinguish simulated trades
                transaction_id=transaction_id,
                confluence_score=confluence_score,
                stop_loss_pct=stop_loss_pct,
                position_size_usd=position_size_usd,
                exchange="Bybit (Simulated)"
            )
            logger.info(f"Sent simulated trade alert for {symbol}")
        except Exception as alert_error:
            logger.error(f"Error sending simulated trade alert: {str(alert_error)}")
        
        return {
            'success': True,
            'simulated': True,
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': current_price,
            'confluence_score': confluence_score,
            'stop_loss_pct': stop_loss_pct,
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
                    
                    # Calculate stop loss based on confidence score instead of position size
                    stop_loss_pct = self.calculate_score_based_stop_loss(
                        side=signal['action'],
                        confluence_score=overall_score
                    )
                    
                    # Log position sizing and stop loss information
                    logger.info(f"Position size: {position_size:.2f} ({(position_size/total_balance)*100:.2f}% of balance)")
                    logger.info(f"Score-based stop loss: {stop_loss_pct*100:.2f}%")
                    
                    # Execute or simulate the trade
                    if dry_run:
                        result = await self.simulate_trade(
                            symbol=symbol,
                            side=signal['action'],
                            quantity=position_size,
                            confluence_score=overall_score
                        )
                        logger.info(f"Simulated {signal['action']} for {symbol}: {position_size} at {result['price']} with {stop_loss_pct*100:.2f}% stop loss")
                    else:
                        result = await self.execute_trade(
                            symbol=symbol,
                            side=signal['action'],
                            quantity=position_size,
                            stop_loss_pct=stop_loss_pct,
                            is_trailing_stop=True,
                            confluence_score=overall_score  # Pass the score to execute_trade
                        )
                        
                        if result['success']:
                            logger.info(f"Executed {signal['action']} for {symbol}: {position_size} at {result['price']} with {stop_loss_pct*100:.2f}% stop loss")
                        else:
                            logger.error(f"Trade execution failed: {result.get('error')}")
                else:
                    logger.info(f"No trading signal for {symbol}")
            
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue
        
        # Monitor existing positions
        await self.monitor_positions()

    def calculate_scaled_stop_loss(self, position_size: float, available_balance: float) -> float:
        """
        Calculate a scaled stop loss percentage based on position size
        Larger positions get tighter stops for better risk management
        
        Args:
            position_size: The calculated position size
            available_balance: Available balance to trade with
            
        Returns:
            Stop loss percentage (decimal format, e.g., 0.02 for 2%)
        """
        # Calculate what percentage of max position this represents
        position_pct = position_size / available_balance
        max_position_pct = self.max_position_size
        
        # Calculate where this position falls between base and max position
        # 0.0 means at base position, 1.0 means at max position
        if position_pct <= self.max_position_size:
            # For base positions, use the default trailing stop
            return self.stop_loss_pct
        
        position_scale = (position_pct - self.max_position_size) / (max_position_pct - self.max_position_size)
        
        # Calculate scaled stop loss
        # As position_scale increases from 0 to 1, stop loss tightens from default to min value
        # Default trailing stop: typically 2% (0.02) or whatever is set in config
        # Minimum stop loss: now 2/3 of default instead of 1/2 for more forgiving stops
        min_stop_pct = self.stop_loss_pct * (2/3)  # Increased from half to two-thirds
        scaled_stop_pct = self.stop_loss_pct - (position_scale * (self.stop_loss_pct - min_stop_pct))
        
        return scaled_stop_pct
        
    def calculate_score_based_stop_loss(self, side: str, confluence_score: float) -> float:
        """
        Calculate stop loss percentage based on confluence score rather than position size.
        Higher scores get wider stops since we have more confidence in the trade direction.
        
        Args:
            side: Trade side (buy/sell)
            confluence_score: The overall confluence score (0-100)
            
        Returns:
            Stop loss percentage (decimal format, e.g., 0.03 for 3%)
        """
        # Base stop loss from config
        base_stop = self.stop_loss_pct
        # Maximum stop (for highest confidence trades) - 1.5x the base
        max_stop = base_stop * 1.5
        # Minimum stop (for threshold trades) - 0.8x the base
        min_stop = base_stop * 0.8
        
        if side.lower() == 'buy':
            # For long trades: Higher score = higher confidence = wider stop
            if confluence_score <= self.long_threshold:
                return min_stop

            # Calculate normalized score (0 to 1) where 0 is at threshold and 1 is at 100
            normalized_score = (confluence_score - self.long_threshold) / (100 - self.long_threshold)
            # Scale stop loss based on normalized score
            return min_stop + (normalized_score * (max_stop - min_stop))
        else:  # sell
            # For short trades: Lower score = higher confidence = wider stop
            if confluence_score >= self.short_threshold:
                return min_stop

            # Calculate normalized score (0 to 1) where 0 is at threshold and 1 is at 0
            normalized_score = (self.short_threshold - confluence_score) / self.short_threshold
            # Scale stop loss based on normalized score
            return min_stop + (normalized_score * (max_stop - min_stop))

    async def close_position(self, order_id: str) -> Dict[str, Any]:
        """
        Close a position by order ID
        
        Args:
            order_id: Original order ID that opened the position
            
        Returns:
            Result of the close operation
        """
        logger.debug(f"Closing position for order ID: {order_id}")
        
        try:
            # Check if position exists in tracking
            if order_id not in self.active_positions:
                logger.warning(f"Position with order ID {order_id} not found in tracking")
                return {'success': False, 'error': 'Position not found'}
            
            # Get position details
            position = self.active_positions[order_id]
            symbol = position['symbol']
            original_side = position['side']
            quantity = position['quantity']
            entry_price = position['entry_price']
            
            # Determine closing side (opposite of entry)
            close_side = 'sell' if original_side.lower() == 'buy' else 'buy'
            
            # Convert CCXT symbol format to Bybit format
            bybit_symbol = symbol.replace('/', '')
            
            # Get current market price
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calculate profit/loss
            if original_side.lower() == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Prepare order parameters for closing
            order_params = {
                "category": "spot",
                "symbol": bybit_symbol,
                "side": close_side.upper(),
                "orderType": "Market",
                "qty": str(quantity),
            }
            
            # Place the closing order
            order_result = await self._signed_request(
                "/v5/order/create",
                order_params,
                "POST"
            )
            
            if order_result.get('retCode') != 0:
                logger.error(f"Close order failed: {order_result.get('retMsg')}")
                return {'success': False, 'error': order_result.get('retMsg')}
            
            close_order_id = order_result.get('result', {}).get('orderId')
            
            # Calculate USD value of the closed position
            position_size_usd = quantity * current_price
            
            # Send trade execution alert for position close
            try:
                # Generate a unique transaction ID
                transaction_id = str(uuid.uuid4())[:8]
                
                # Send alert for the closed position
                await self.alert_manager.send_trade_execution_alert(
                    symbol=symbol,
                    side=close_side,
                    quantity=quantity,
                    price=current_price,
                    trade_type="exit",
                    order_id=close_order_id,
                    transaction_id=transaction_id,
                    position_size_usd=position_size_usd,
                    exchange="Bybit"
                )
                logger.info(f"Sent position close alert for {symbol}")
            except Exception as alert_error:
                logger.error(f"Error sending position close alert: {str(alert_error)}")
            
            # Remove from active positions tracking
            del self.active_positions[order_id]
            
            return {
                'success': True,
                'order_id': close_order_id,
                'symbol': symbol,
                'side': close_side,
                'quantity': quantity,
                'price': current_price,
                'pnl_pct': pnl_pct
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    async def close_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Close all tracked positions
        
        Returns:
            Dict mapping order IDs to close results
        """
        results = {}
        
        # Get list of position order IDs to avoid modification during iteration
        position_order_ids = list(self.active_positions.keys())
        
        for order_id in position_order_ids:
            results[order_id] = await self.close_position(order_id)
            
        return results
