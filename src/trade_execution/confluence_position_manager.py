import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)

class ConfluenceBasedPositionManager:
    """Manages trading positions based on confluence scores"""
    
    def __init__(self, config: Dict[str, Any], exchange=None):
        """Initialize the confluence-based position manager
        
        Args:
            config: Configuration dictionary
            exchange: Optional exchange instance to use instead of creating a new one
        """
        self.config = config
        self.exchange = exchange
        
        # Extract exchange configuration
        exchange_config = config.get('exchanges', {}).get('bybit', {})
        self.api_key = exchange_config.get('api_credentials', {}).get('api_key')
        self.api_secret = exchange_config.get('api_credentials', {}).get('api_secret')
        self.base_url = exchange_config.get('endpoint', 'https://api.bybit.com')
        self.is_demo = "api-demo.bybit.com" in self.base_url
        
        # Position settings
        position_config = config.get('position_manager', {})
        self.base_position_pct = position_config.get('base_position_pct', 0.03)  # 3% base position
        self.min_confluence_score = position_config.get('min_confluence_score', 70)
        self.trailing_stop_pct = position_config.get('trailing_stop_pct', 0.02)  # 2% trailing stop
        self.scale_factor = position_config.get('scale_factor', 0.01)  # 1% increase per point above threshold
        self.max_position_pct = position_config.get('max_position_pct', 0.10)  # 10% maximum position
        
        # Threshold for scaling up position size
        self.scaling_threshold = position_config.get('scaling_threshold', {
            'long': 75,  # Score above which to start scaling for longs
            'short': 25   # Score below which to start scaling for shorts
        })
        
        # Log configuration
        logger.info(f"Position manager configured with:")
        logger.info(f"- Base position: {self.base_position_pct:.1%}")
        logger.info(f"- Max position: {self.max_position_pct:.1%}")
        logger.info(f"- Trailing stop: {self.trailing_stop_pct:.1%}")
        logger.info(f"- Scaling factor: {self.scale_factor:.1%} per point")
        logger.info(f"- Scaling thresholds: long={self.scaling_threshold['long']}, short={self.scaling_threshold['short']}")
        
        # Active positions and orders tracking
        self.active_positions = {}
        self.trailing_stops = {}
    
    async def initialize(self) -> bool:
        """Initialize the position manager"""
        try:
            # Create exchange if not provided
            if not self.exchange:
                # Initialize CCXT client
                self.exchange = ccxt.bybit({
                    'apiKey': self.api_key,
                    'secret': self.api_secret,
                    'enableRateLimit': True,
                    'urls': {'api': self.base_url}
                })
                
                # Load markets
                await self.exchange.load_markets()
                
            logger.info("Position manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize position manager: {str(e)}")
            return False
    
    def calculate_position_size(self, symbol: str, side: str, 
                              confluence_score: float, account_balance: float) -> float:
        """Calculate position size based on confluence score.
        
        Args:
            symbol: Trading symbol (e.g. 'BTC/USDT')
            side: Trade side ('buy' or 'sell')
            confluence_score: The confluence score (0-100)
            account_balance: Available account balance
            
        Returns:
            Position size in quote currency
        """
        # Check if the confluence score meets the minimum threshold
        if side == 'buy' and confluence_score < self.min_confluence_score:
            logger.info(f"Confluence score {confluence_score} below minimum {self.min_confluence_score} for long")
            return 0
        elif side == 'sell' and confluence_score > (100 - self.min_confluence_score):
            logger.info(f"Confluence score {confluence_score} above maximum {100 - self.min_confluence_score} for short")
            return 0
        
        # Start with the base position percentage (3%)
        position_pct = self.base_position_pct
        
        # Scale up position size based on how strong the signal is
        if side == 'buy' and confluence_score > self.scaling_threshold['long']:
            # For every point above the threshold, increase position size
            extra_points = confluence_score - self.scaling_threshold['long']
            extra_size = extra_points * self.scale_factor
            position_pct += extra_size
            logger.info(f"Scaling up long position: +{extra_size:.2%} for {extra_points} points above threshold")
            logger.info(f"Position size increased from {self.base_position_pct:.2%} to {position_pct:.2%}")
            
        elif side == 'sell' and confluence_score < self.scaling_threshold['short']:
            # For short positions, scale based on how far below the threshold
            extra_points = self.scaling_threshold['short'] - confluence_score
            extra_size = extra_points * self.scale_factor
            position_pct += extra_size
            logger.info(f"Scaling up short position: +{extra_size:.2%} for {extra_points} points below threshold")
            logger.info(f"Position size increased from {self.base_position_pct:.2%} to {position_pct:.2%}")
        
        # Cap at maximum position size (10%)
        if position_pct > self.max_position_pct:
            logger.info(f"Capping position size from {position_pct:.2%} to {self.max_position_pct:.2%}")
            position_pct = self.max_position_pct
        
        # Calculate position size in quote currency
        position_size = account_balance * position_pct
        logger.info(f"Final position size: {position_pct:.2%} of {account_balance} = {position_size:.2f} USDT")
        
        return position_size
    
    async def open_position(self, symbol: str, side: str, confluence_score: float) -> Dict[str, Any]:
        """Open a new position based on confluence score.
        
        Args:
            symbol: Trading symbol
            side: Trade side ('buy' or 'sell')
            confluence_score: Confluence score (0-100)
            
        Returns:
            Dict with position details
        """
        try:
            # Get account balance
            balance = await self.exchange.fetch_balance()
            available_balance = balance['free']['USDT']  # Assuming USDT as quote currency
            
            # Calculate position size
            position_size = self.calculate_position_size(
                symbol, side, confluence_score, available_balance
            )
            
            if position_size <= 0:
                logger.info("Position size is zero or negative, skipping trade")
                return {"status": "rejected", "reason": "position_size_zero"}
            
            # Get current market price
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calculate quantity in base currency
            quantity = position_size / current_price
            
            # Place market order
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=quantity
            )
            
            # Set trailing stop order
            await self._set_trailing_stop(symbol, side, current_price, quantity, order['id'])
            
            # Track the position
            self.active_positions[order['id']] = {
                'symbol': symbol,
                'side': side,
                'entry_price': current_price,
                'quantity': quantity,
                'confluence_score': confluence_score,
                'timestamp': time.time(),
                'trailing_stop': True
            }
            
            logger.info(f"Opened {side} position for {symbol}: {quantity} @ {current_price}")
            return {
                "status": "success",
                "order_id": order['id'],
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": current_price,
                "value": position_size
            }
            
        except Exception as e:
            logger.error(f"Failed to open position: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    async def _set_trailing_stop(self, symbol: str, side: str, entry_price: float, 
                               quantity: float, order_id: str) -> bool:
        """Set a trailing stop for the position.
        
        Args:
            symbol: Trading symbol
            side: Original trade side ('buy' or 'sell')
            entry_price: Entry price of the position
            quantity: Position quantity
            order_id: Original order ID
            
        Returns:
            True if trailing stop was set successfully
        """
        try:
            # Calculate activation price based on side
            if side == 'buy':
                # For long positions, trailing stop is below entry price
                activation_price = entry_price * (1 - self.trailing_stop_pct)
                stop_side = 'sell'
            else:
                # For short positions, trailing stop is above entry price
                activation_price = entry_price * (1 + self.trailing_stop_pct)
                stop_side = 'buy'
            
            # Place trailing stop order
            trailing_stop_order = await self.exchange.create_order(
                symbol=symbol,
                type='trailing_stop',
                side=stop_side,
                amount=quantity,
                params={
                    'activationPrice': activation_price,
                    'callbackRate': self.trailing_stop_pct * 100  # Convert to percentage points
                }
            )
            
            # Track the trailing stop
            self.trailing_stops[order_id] = trailing_stop_order['id']
            
            logger.info(f"Set trailing stop for {symbol} {side} position at {activation_price}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set trailing stop: {str(e)}")
            return False
    
    async def update_trailing_stops(self) -> None:
        """Update trailing stops for all active positions based on price movement"""
        for order_id, position in list(self.active_positions.items()):
            try:
                # Check if the position has a trailing stop
                if order_id not in self.trailing_stops:
                    continue
                
                # Get current market price
                ticker = await self.exchange.fetch_ticker(position['symbol'])
                current_price = ticker['last']
                
                # Calculate price movement since entry
                entry_price = position['entry_price']
                
                if position['side'] == 'buy':
                    # For long positions, update stop if price moved up
                    price_movement = (current_price - entry_price) / entry_price
                    if price_movement > 0:
                        # Calculate new stop level (2% below current price)
                        new_stop = current_price * (1 - self.trailing_stop_pct)
                        
                        # Only update if new stop is higher than previous
                        current_stop = position.get('current_stop', 0)
                        if new_stop > current_stop:
                            await self._update_trailing_stop(
                                order_id, position, new_stop, current_price
                            )
                
                elif position['side'] == 'sell':
                    # For short positions, update stop if price moved down
                    price_movement = (entry_price - current_price) / entry_price
                    if price_movement > 0:
                        # Calculate new stop level (2% above current price)
                        new_stop = current_price * (1 + self.trailing_stop_pct)
                        
                        # Only update if new stop is lower than previous
                        current_stop = position.get('current_stop', float('inf'))
                        if new_stop < current_stop:
                            await self._update_trailing_stop(
                                order_id, position, new_stop, current_price
                            )
                
            except Exception as e:
                logger.error(f"Error updating trailing stop: {str(e)}")
    
    async def _update_trailing_stop(self, order_id: str, position: Dict[str, Any], 
                                  new_stop: float, current_price: float) -> bool:
        """Update a trailing stop order.
        
        Args:
            order_id: Original order ID
            position: Position details
            new_stop: New stop price
            current_price: Current market price
            
        Returns:
            True if stop was updated successfully
        """
        try:
            # Cancel the existing stop order
            stop_id = self.trailing_stops.get(order_id)
            if stop_id:
                await self.exchange.cancel_order(stop_id, position['symbol'])
            
            # Create a new stop order
            stop_side = 'sell' if position['side'] == 'buy' else 'buy'
            
            # Place new trailing stop order
            trailing_stop_order = await self.exchange.create_order(
                symbol=position['symbol'],
                type='trailing_stop',
                side=stop_side,
                amount=position['quantity'],
                params={
                    'activationPrice': new_stop,
                    'callbackRate': self.trailing_stop_pct * 100
                }
            )
            
            # Update tracking
            self.trailing_stops[order_id] = trailing_stop_order['id']
            position['current_stop'] = new_stop
            position['stop_updated_at'] = time.time()
            
            logger.info(f"Updated trailing stop for {position['symbol']} to {new_stop} (market: {current_price})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update trailing stop: {str(e)}")
            return False
    
    async def close_position(self, order_id: str) -> Dict[str, Any]:
        """Close a specific position.
        
        Args:
            order_id: The order ID to close
            
        Returns:
            Close result
        """
        try:
            position = self.active_positions.get(order_id)
            if not position:
                return {"status": "error", "reason": "position_not_found"}
            
            # Place order to close the position
            close_side = 'sell' if position['side'] == 'buy' else 'buy'
            
            order = await self.exchange.create_order(
                symbol=position['symbol'],
                type='market',
                side=close_side,
                amount=position['quantity']
            )
            
            # Cancel any trailing stops
            if order_id in self.trailing_stops:
                try:
                    await self.exchange.cancel_order(
                        self.trailing_stops[order_id], 
                        position['symbol']
                    )
                except Exception as e:
                    logger.warning(f"Failed to cancel trailing stop: {str(e)}")
                
                del self.trailing_stops[order_id]
            
            # Remove position from tracking
            del self.active_positions[order_id]
            
            logger.info(f"Closed {position['side']} position for {position['symbol']}")
            return {
                "status": "success",
                "close_order_id": order['id'],
                "symbol": position['symbol'],
                "side": close_side,
                "quantity": position['quantity']
            }
            
        except Exception as e:
            logger.error(f"Failed to close position: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    async def close_all_positions(self) -> Dict[str, Any]:
        """Close all active positions.
        
        Returns:
            Results of closing positions
        """
        results = {}
        for order_id in list(self.active_positions.keys()):
            results[order_id] = await self.close_position(order_id)
        
        return results
    
    async def get_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions.
        
        Returns:
            List of active positions
        """
        return [
            {**details, "order_id": order_id} 
            for order_id, details in self.active_positions.items()
        ] 