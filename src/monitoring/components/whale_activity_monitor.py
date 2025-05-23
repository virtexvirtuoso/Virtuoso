"""
Whale Activity Monitor Component

This module handles whale activity monitoring functionality including:
- Order book analysis for whale activity detection
- Trade analysis for confirmation
- Alert generation for accumulation/distribution patterns
- Activity data tracking and storage
- Cooldown period management
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional
import numpy as np


class WhaleActivityMonitor:
    """
    Handles whale activity monitoring functionality including orderbook analysis,
    trade analysis, and alert generation for accumulation/distribution patterns.
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
        alert_manager=None
    ):
        """
        Initialize WhaleActivityMonitor.
        
        Args:
            logger: Logger instance
            config: Configuration dictionary
            alert_manager: Alert manager instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config or {}
        self.alert_manager = alert_manager
        
        # Get whale activity configuration
        self.whale_activity_config = self.config.get('whale_activity', {
            'enabled': True,
            'cooldown': 900,  # 15 minutes
            'accumulation_threshold': 1000000,  # $1M USD
            'distribution_threshold': 1000000,  # $1M USD
            'imbalance_threshold': 0.2,  # 20%
            'min_order_count': 5,
            'market_percentage': 0.02  # 2%
        })
        
        # Activity tracking
        self._last_whale_alert: Dict[str, float] = {}
        self._last_whale_activity: Dict[str, Dict[str, Any]] = {}

    async def monitor_whale_activity(self, symbol: str, market_data: Dict[str, Any]) -> None:
        """
        Monitor whale activity (accumulation/distribution) in real-time.
        
        This method analyzes the order book and recent trades to detect significant
        whale activity patterns and sends alerts when thresholds are crossed.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data dictionary containing orderbook and trades
        """
        try:
            # Skip if disabled in config
            if not self.whale_activity_config.get('enabled', True):
                return
                
            # Skip if no alert manager available
            if not self.alert_manager:
                self.logger.debug(f"Skipping whale activity monitoring for {symbol}: No alert manager")
                return
                
            # Check cooldown period
            current_time = time.time()
            last_alert_time = self._last_whale_alert.get(symbol, 0)
            cooldown_period = self.whale_activity_config.get('cooldown', 900)  # 15 min default
            
            if current_time - last_alert_time < cooldown_period:
                self.logger.debug(f"Skipping whale activity alert for {symbol}: In cooldown period")
                return
            
            # Extract orderbook from market data
            orderbook = market_data.get('orderbook')
            if not orderbook or not isinstance(orderbook, dict):
                self.logger.debug(f"No valid orderbook data for {symbol}")
                return
                
            # Ensure bids and asks exist
            if 'bids' not in orderbook or 'asks' not in orderbook:
                self.logger.debug(f"Missing bids or asks in orderbook for {symbol}")
                return
                
            # Get current price info
            ticker = market_data.get('ticker', {})
            current_price = float(ticker.get('last', 0))
            if not current_price:
                self.logger.debug(f"No price information for {symbol}")
                return
            
            # Calculate whale threshold
            whale_threshold = self._calculate_whale_threshold(orderbook)
            if whale_threshold == 0:
                self.logger.debug(f"Could not calculate whale threshold for {symbol}")
                return
            
            # Analyze orderbook for whale activity
            whale_analysis = self._analyze_orderbook_whale_activity(
                orderbook, whale_threshold, current_price
            )
            
            # Enhance with trade analysis
            trade_analysis = self._analyze_trade_whale_activity(
                market_data.get('trades', []), whale_threshold, current_time
            )
            
            # Combine analyses
            current_activity = {**whale_analysis, **trade_analysis}
            current_activity['timestamp'] = int(current_time)
            current_activity['threshold'] = whale_threshold
            
            # Store current activity data
            self._last_whale_activity[symbol] = current_activity
            
            # Log detailed whale activity for debugging
            self.logger.debug(f"Whale activity for {symbol}: " +
                            f"Bids: {current_activity.get('whale_bid_orders', 0)} orders " +
                            f"({current_activity.get('whale_bid_volume', 0):.2f} units, " +
                            f"${current_activity.get('whale_bid_usd', 0):.2f}), " +
                            f"Asks: {current_activity.get('whale_ask_orders', 0)} orders " +
                            f"({current_activity.get('whale_ask_volume', 0):.2f} units, " +
                            f"${current_activity.get('whale_ask_usd', 0):.2f})")
            
            # Check for significant activity and generate alerts
            await self._check_and_generate_alerts(symbol, current_activity, current_price)
                
        except Exception as e:
            self.logger.error(f"Error monitoring whale activity for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())

    def _calculate_whale_threshold(self, orderbook: Dict[str, Any]) -> float:
        """
        Calculate threshold for whale activity based on order book statistics.
        
        Args:
            orderbook: Order book data with bids and asks
            
        Returns:
            Whale threshold (2 standard deviations above mean)
        """
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            all_sizes = []
            for order in bids[:50] + asks[:50]:  # Use top 50 levels for calculation
                if isinstance(order, list) and len(order) >= 2:
                    all_sizes.append(float(order[1]))
            
            if not all_sizes:
                return 0
                
            # Calculate whale threshold (2 standard deviations above mean)
            mean_size = float(np.mean(all_sizes))
            std_size = float(np.std(all_sizes))
            whale_threshold = mean_size + (2 * std_size)
            
            return whale_threshold
            
        except Exception as e:
            self.logger.error(f"Error calculating whale threshold: {str(e)}")
            return 0

    def _analyze_orderbook_whale_activity(
        self, 
        orderbook: Dict[str, Any], 
        whale_threshold: float, 
        current_price: float
    ) -> Dict[str, Any]:
        """
        Analyze orderbook for whale activity patterns.
        
        Args:
            orderbook: Order book data
            whale_threshold: Threshold for whale orders
            current_price: Current market price
            
        Returns:
            Dictionary with whale activity metrics
        """
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            # Find whale orders
            whale_bids = [order for order in bids if float(order[1]) >= whale_threshold]
            whale_asks = [order for order in asks if float(order[1]) >= whale_threshold]
            
            whale_bid_volume = sum(float(order[1]) for order in whale_bids)
            whale_ask_volume = sum(float(order[1]) for order in whale_asks)
            
            # Get total order book volumes for percentage calculation
            total_bid_volume = sum(float(order[1]) for order in bids)
            total_ask_volume = sum(float(order[1]) for order in asks)
            
            # Calculate USD values
            bid_usd_value = whale_bid_volume * current_price
            ask_usd_value = whale_ask_volume * current_price
            
            # Calculate net volume and imbalance metrics
            net_volume = whale_bid_volume - whale_ask_volume
            net_usd_value = net_volume * current_price
            
            # Calculate volume percentages
            bid_percentage = (whale_bid_volume / total_bid_volume) if total_bid_volume > 0 else 0
            ask_percentage = (whale_ask_volume / total_ask_volume) if total_ask_volume > 0 else 0
            
            # Calculate imbalance ratio
            total_whale_volume = whale_bid_volume + whale_ask_volume
            if total_whale_volume > 0:
                bid_ratio = whale_bid_volume / total_whale_volume
                ask_ratio = whale_ask_volume / total_whale_volume
                imbalance = abs(bid_ratio - ask_ratio)
            else:
                imbalance = 0
            
            return {
                'whale_bid_volume': whale_bid_volume,
                'whale_ask_volume': whale_ask_volume,
                'whale_bid_usd': bid_usd_value,
                'whale_ask_usd': ask_usd_value,
                'net_volume': net_volume,
                'net_usd_value': net_usd_value,
                'imbalance': imbalance,
                'bid_percentage': bid_percentage,
                'ask_percentage': ask_percentage,
                'whale_bid_orders': len(whale_bids),
                'whale_ask_orders': len(whale_asks)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing orderbook whale activity: {str(e)}")
            return {}

    def _analyze_trade_whale_activity(
        self, 
        trades: list, 
        whale_threshold: float, 
        current_time: float
    ) -> Dict[str, Any]:
        """
        Analyze trades for whale activity patterns.
        
        Args:
            trades: List of recent trades
            whale_threshold: Threshold for whale trades
            current_time: Current timestamp
            
        Returns:
            Dictionary with trade-based whale activity metrics
        """
        try:
            if not trades or not isinstance(trades, list):
                return {}
                
            # Define recent trades timeframe (last 30 minutes)
            recent_time_threshold = current_time - 1800
            
            # Identify large (whale) trades
            whale_trades = []
            buy_volume = 0
            sell_volume = 0
            
            for trade in trades:
                # Skip old trades
                trade_time = float(trade.get('timestamp', 0)) / 1000 if isinstance(trade.get('timestamp'), int) else 0
                if trade_time < recent_time_threshold:
                    continue
                    
                # Extract trade data
                side = trade.get('side', '').lower()
                size = float(trade.get('amount', trade.get('size', trade.get('quantity', 0))))
                price = float(trade.get('price', 0))
                value = size * price
                
                # Check if it's a whale trade (using lower threshold for trades than orders)
                if size >= whale_threshold / 2:
                    whale_trades.append({
                        'side': side,
                        'size': size,
                        'price': price,
                        'value': value,
                        'time': trade_time
                    })
                    
                    # Accumulate volumes
                    if side == 'buy':
                        buy_volume += size
                    elif side == 'sell':
                        sell_volume += size
            
            # Calculate trade-based metrics
            total_whale_trade_volume = buy_volume + sell_volume
            net_trade_volume = buy_volume - sell_volume
            trade_imbalance = 0
            
            if total_whale_trade_volume > 0:
                trade_imbalance = net_trade_volume / total_whale_trade_volume
            
            self.logger.debug(f"Trades analysis: " +
                            f"Whale trades: {len(whale_trades)}, " +
                            f"Buy volume: {buy_volume:.2f}, Sell volume: {sell_volume:.2f}, " +
                            f"Net volume: {net_trade_volume:.2f}, Imbalance: {trade_imbalance:.2f}")
            
            return {
                'whale_trades_count': len(whale_trades),
                'whale_buy_volume': buy_volume,
                'whale_sell_volume': sell_volume,
                'net_trade_volume': net_trade_volume,
                'trade_imbalance': trade_imbalance,
                'trade_confirmation': (trade_imbalance > 0 and net_trade_volume > 0) or 
                                     (trade_imbalance < 0 and net_trade_volume < 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing trade whale activity: {str(e)}")
            return {}

    async def _check_and_generate_alerts(
        self, 
        symbol: str, 
        current_activity: Dict[str, Any], 
        current_price: float
    ) -> None:
        """
        Check activity against thresholds and generate alerts if needed.
        
        Args:
            symbol: Trading pair symbol
            current_activity: Current whale activity data
            current_price: Current market price
        """
        try:
            # Get thresholds from config
            accumulation_threshold = self.whale_activity_config.get('accumulation_threshold', 1000000)
            distribution_threshold = self.whale_activity_config.get('distribution_threshold', 1000000)
            imbalance_threshold = self.whale_activity_config.get('imbalance_threshold', 0.2)
            min_order_count = self.whale_activity_config.get('min_order_count', 5)
            market_percentage = self.whale_activity_config.get('market_percentage', 0.02)
            
            net_usd_value = current_activity.get('net_usd_value', 0)
            net_volume = current_activity.get('net_volume', 0)
            imbalance = current_activity.get('imbalance', 0)
            bid_percentage = current_activity.get('bid_percentage', 0)
            ask_percentage = current_activity.get('ask_percentage', 0)
            whale_bid_orders = current_activity.get('whale_bid_orders', 0)
            whale_ask_orders = current_activity.get('whale_ask_orders', 0)
            
            # Detect significant accumulation
            significant_accumulation = (
                net_usd_value > accumulation_threshold and
                whale_bid_orders >= min_order_count and
                bid_percentage > market_percentage and
                imbalance > imbalance_threshold
            )
            
            # Detect significant distribution
            significant_distribution = (
                net_usd_value < -distribution_threshold and
                whale_ask_orders >= min_order_count and
                ask_percentage > market_percentage and
                imbalance > imbalance_threshold
            )
            
            # Generate alerts for significant activity
            if significant_accumulation:
                await self._generate_accumulation_alert(symbol, current_activity, current_price)
            elif significant_distribution:
                await self._generate_distribution_alert(symbol, current_activity, current_price)
                
        except Exception as e:
            self.logger.error(f"Error checking whale activity thresholds for {symbol}: {str(e)}")

    async def _generate_accumulation_alert(
        self, 
        symbol: str, 
        current_activity: Dict[str, Any], 
        current_price: float
    ) -> None:
        """Generate alert for whale accumulation."""
        try:
            net_volume = current_activity.get('net_volume', 0)
            net_usd_value = current_activity.get('net_usd_value', 0)
            whale_bid_orders = current_activity.get('whale_bid_orders', 0)
            bid_percentage = current_activity.get('bid_percentage', 0)
            imbalance = current_activity.get('imbalance', 0)
            
            # Format trade confirmation if available
            trade_confirmation = ""
            has_trade_data = 'whale_trades_count' in current_activity
            
            if has_trade_data:
                trades_count = current_activity.get('whale_trades_count', 0)
                buy_volume = current_activity.get('whale_buy_volume', 0)
                sell_volume = current_activity.get('whale_sell_volume', 0)
                net_trade_volume = current_activity.get('net_trade_volume', 0)
                
                if trades_count > 0:
                    if net_trade_volume > 0:
                        # Trades confirm accumulation
                        confirmation_strength = min(abs(current_activity.get('trade_imbalance', 0)) * 100, 100)
                        trade_confirmation = (
                            f"• **Trade confirmation**: {confirmation_strength:.0f}% confirmed\n"
                            f"• Recent whale buys: {buy_volume:.2f} units vs sells: {sell_volume:.2f} units\n"
                        )
                    else:
                        # Trades contradict orderbook signal (warning)
                        trade_confirmation = (
                            f"• **Warning**: Order book shows accumulation but recent trades show selling\n"
                            f"• Recent whale buys: {buy_volume:.2f} units vs sells: {sell_volume:.2f} units\n"
                        )
            
            message = (
                f"🐋 **Whale Accumulation Detected** for {symbol}\n"
                f"• Net accumulation: {net_volume:.2f} units (${abs(net_usd_value):,.2f})\n"
                f"• Whale bid orders: {whale_bid_orders}, {bid_percentage:.1%} of order book\n"
                f"{trade_confirmation}"
                f"• Imbalance ratio: {imbalance:.1%}\n"
                f"• Current price: ${current_price:,.2f}"
            )
            
            # Send alert through alert manager
            await self.alert_manager.send_alert(
                level="info",
                message=message,
                details={
                    "type": "whale_activity",
                    "subtype": "accumulation",
                    "symbol": symbol,
                    "data": current_activity
                }
            )
            
            # Update last alert time
            self._last_whale_alert[symbol] = time.time()
            self.logger.info(f"Sent whale accumulation alert for {symbol}: ${abs(net_usd_value):,.2f}")
            
        except Exception as e:
            self.logger.error(f"Error generating accumulation alert for {symbol}: {str(e)}")

    async def _generate_distribution_alert(
        self, 
        symbol: str, 
        current_activity: Dict[str, Any], 
        current_price: float
    ) -> None:
        """Generate alert for whale distribution."""
        try:
            net_volume = current_activity.get('net_volume', 0)
            net_usd_value = current_activity.get('net_usd_value', 0)
            whale_ask_orders = current_activity.get('whale_ask_orders', 0)
            ask_percentage = current_activity.get('ask_percentage', 0)
            imbalance = current_activity.get('imbalance', 0)
            
            # Format trade confirmation if available
            trade_confirmation = ""
            has_trade_data = 'whale_trades_count' in current_activity
            
            if has_trade_data:
                trades_count = current_activity.get('whale_trades_count', 0)
                buy_volume = current_activity.get('whale_buy_volume', 0)
                sell_volume = current_activity.get('whale_sell_volume', 0)
                net_trade_volume = current_activity.get('net_trade_volume', 0)
                
                if trades_count > 0:
                    if net_trade_volume < 0:
                        # Trades confirm distribution
                        confirmation_strength = min(abs(current_activity.get('trade_imbalance', 0)) * 100, 100)
                        trade_confirmation = (
                            f"• **Trade confirmation**: {confirmation_strength:.0f}% confirmed\n"
                            f"• Recent whale sells: {sell_volume:.2f} units vs buys: {buy_volume:.2f} units\n"
                        )
                    else:
                        # Trades contradict orderbook signal (warning)
                        trade_confirmation = (
                            f"• **Warning**: Order book shows distribution but recent trades show buying\n"
                            f"• Recent whale sells: {sell_volume:.2f} units vs buys: {buy_volume:.2f} units\n"
                        )
            
            message = (
                f"🐋 **Whale Distribution Detected** for {symbol}\n"
                f"• Net distribution: {abs(net_volume):.2f} units (${abs(net_usd_value):,.2f})\n"
                f"• Whale ask orders: {whale_ask_orders}, {ask_percentage:.1%} of order book\n"
                f"{trade_confirmation}"
                f"• Imbalance ratio: {imbalance:.1%}\n"
                f"• Current price: ${current_price:,.2f}"
            )
            
            # Send alert through alert manager
            await self.alert_manager.send_alert(
                level="info",
                message=message,
                details={
                    "type": "whale_activity",
                    "subtype": "distribution",
                    "symbol": symbol,
                    "data": current_activity
                }
            )
            
            # Update last alert time
            self._last_whale_alert[symbol] = time.time()
            self.logger.info(f"Sent whale distribution alert for {symbol}: ${abs(net_usd_value):,.2f}")
            
        except Exception as e:
            self.logger.error(f"Error generating distribution alert for {symbol}: {str(e)}")

    def get_whale_activity_history(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get whale activity history.
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            Dictionary containing whale activity history
        """
        if symbol:
            return self._last_whale_activity.get(symbol, {})
        return self._last_whale_activity.copy()

    def get_whale_activity_stats(self) -> Dict[str, Any]:
        """
        Get whale activity monitoring statistics.
        
        Returns:
            Dictionary containing whale activity statistics
        """
        return {
            'monitored_symbols': len(self._last_whale_activity),
            'symbols_with_recent_alerts': len(self._last_whale_alert),
            'config': self.whale_activity_config,
            'last_activity_timestamps': {
                symbol: data.get('timestamp', 0) 
                for symbol, data in self._last_whale_activity.items()
            }
        } 