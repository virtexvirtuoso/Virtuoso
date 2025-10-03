from src.utils.task_tracker import create_tracked_task
"""
Momentum Trading Strategy for Bybit

This module implements a momentum-based trading strategy that:
1. Uses RSI and MACD indicators for signal generation
2. Handles real-time WebSocket data for BTC/USDT and ETH/USDT
3. Manages position sizing with 2% risk per trade
4. Integrates with the existing Virtuoso trading infrastructure

Key Features:
- Real-time momentum analysis using RSI and MACD
- Adaptive position sizing based on account risk tolerance
- WebSocket integration for low-latency data processing
- Comprehensive error handling and logging
- Integration with existing alert and risk management systems

Author: Virtuoso Trading System
Version: 1.0.0
"""

import asyncio
import logging
import time
import talib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.core.exchanges.bybit import BybitExchange
from src.data_acquisition.websocket_handler import WebSocketHandler
from src.signal_generation.signal_generator import SignalGenerator
from src.core.base_component import BaseComponent
from src.core.error.models import ErrorContext, ErrorSeverity
from src.utils.data_utils import resolve_price
from src.models.schema import SignalType

logger = logging.getLogger(__name__)

class MomentumSignal(Enum):
    """Momentum signal types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

@dataclass
class MomentumIndicators:
    """Container for momentum indicators"""
    rsi: float
    rsi_signal: str
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_signal_line: str
    price: float
    volume: float
    timestamp: datetime

@dataclass
class PositionSizing:
    """Position sizing calculation results"""
    account_balance: float
    risk_amount: float
    position_size: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float

@dataclass
class TradeSignal:
    """Complete trade signal with all necessary information"""
    symbol: str
    signal: MomentumSignal
    confidence: float
    indicators: MomentumIndicators
    position_sizing: PositionSizing
    entry_price: float
    timestamp: datetime
    metadata: Dict[str, Any]

class MomentumStrategy(BaseComponent):
    """
    Momentum Trading Strategy Implementation
    
    This strategy combines RSI and MACD indicators to identify momentum
    opportunities in BTC/USDT and ETH/USDT pairs on Bybit.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        exchange: Optional[BybitExchange] = None,
        websocket_handler: Optional[WebSocketHandler] = None,
        signal_generator: Optional[SignalGenerator] = None,
        error_handler: Optional[Any] = None
    ):
        """Initialize the momentum strategy.
        
        Args:
            config: Configuration dictionary
            exchange: Optional Bybit exchange instance
            websocket_handler: Optional WebSocket handler
            signal_generator: Optional signal generator
            error_handler: Optional error handler
        """
        super().__init__()
        self.config = config
        self.error_handler = error_handler
        
        # Strategy configuration
        self.strategy_config = config.get('momentum_strategy', {})
        self.symbols = self.strategy_config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        self.timeframe = self.strategy_config.get('timeframe', '5m')
        self.lookback_periods = self.strategy_config.get('lookback_periods', 200)
        
        # Risk management configuration
        self.risk_config = self.strategy_config.get('risk_management', {})
        self.risk_per_trade = self.risk_config.get('risk_per_trade', 0.02)  # 2%
        self.max_positions = self.risk_config.get('max_positions', 2)
        self.stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.015)  # 1.5%
        self.take_profit_pct = self.risk_config.get('take_profit_pct', 0.03)  # 3%
        
        # Indicator configuration
        self.indicator_config = self.strategy_config.get('indicators', {})
        self.rsi_period = self.indicator_config.get('rsi_period', 14)
        self.rsi_oversold = self.indicator_config.get('rsi_oversold', 30)
        self.rsi_overbought = self.indicator_config.get('rsi_overbought', 70)
        self.macd_fast = self.indicator_config.get('macd_fast', 12)
        self.macd_slow = self.indicator_config.get('macd_slow', 26)
        self.macd_signal = self.indicator_config.get('macd_signal', 9)
        
        # Components
        self.exchange = exchange
        self.websocket_handler = websocket_handler  
        self.signal_generator = signal_generator
        
        # Strategy state
        self.is_running = False
        self.market_data = {}  # {symbol: DataFrame}
        self.current_positions = {}  # {symbol: position_data}
        self.last_signals = {}  # {symbol: TradeSignal}
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        
        # Data buffers for real-time processing
        self.price_buffers = {symbol: [] for symbol in self.symbols}
        self.volume_buffers = {symbol: [] for symbol in self.symbols}
        
        logger.info(f"MomentumStrategy initialized for symbols: {self.symbols}")
        
    async def initialize(self) -> bool:
        """Initialize the momentum strategy components.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing MomentumStrategy...")
            
            # Initialize exchange if not provided
            if not self.exchange:
                self.exchange = await BybitExchange.get_instance(self.config, self.error_handler)
            
            # Initialize WebSocket handler if not provided
            if not self.websocket_handler:
                self.websocket_handler = WebSocketHandler(
                    self.config, 
                    self.error_handler
                )
                if not await self.websocket_handler.initialize():
                    logger.error("Failed to initialize WebSocket handler")
                    return False
            
            # Initialize signal generator if not provided
            if not self.signal_generator:
                self.signal_generator = SignalGenerator(self.config)
            
            # Load initial historical data
            for symbol in self.symbols:
                if not await self._load_historical_data(symbol):
                    logger.error(f"Failed to load historical data for {symbol}")
                    return False
            
            # Subscribe to real-time data
            await self._subscribe_to_websocket_data()
            
            logger.info("MomentumStrategy initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MomentumStrategy: {str(e)}")
            if self.error_handler:
                await self.error_handler.handle_error(
                    ErrorContext(
                        operation="momentum_strategy_init",
                        details={"error": str(e)},
                        component="MomentumStrategy"
                    ),
                    e
                )
            return False
    
    async def _load_historical_data(self, symbol: str) -> bool:
        """Load historical OHLCV data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            bool: True if data loaded successfully
        """
        try:
            logger.info(f"Loading historical data for {symbol}")
            
            # Get historical klines from exchange
            klines = await self.exchange.get_klines(
                symbol=symbol,
                interval=self.timeframe,
                limit=self.lookback_periods
            )
            
            if not klines or len(klines) < self.lookback_periods:
                logger.warning(f"Insufficient historical data for {symbol}: got {len(klines) if klines else 0} candles")
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convert to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Calculate indicators
            df = self._calculate_indicators(df)
            
            # Store in market data
            self.market_data[symbol] = df
            
            # Initialize price and volume buffers
            self.price_buffers[symbol] = df['close'].tolist()[-50:]  # Keep last 50 prices
            self.volume_buffers[symbol] = df['volume'].tolist()[-50:]  # Keep last 50 volumes
            
            logger.info(f"Loaded {len(df)} historical candles for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load historical data for {symbol}: {str(e)}")
            return False
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and MACD indicators.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with calculated indicators
        """
        try:
            # Calculate RSI
            df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
            
            # Calculate MACD
            df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
                df['close'].values,
                fastperiod=self.macd_fast,
                slowperiod=self.macd_slow,
                signalperiod=self.macd_signal
            )
            
            # Fill NaN values
            df.fillna(method='ffill', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return df
    
    async def _subscribe_to_websocket_data(self):
        """Subscribe to real-time WebSocket data for all symbols."""
        try:
            for symbol in self.symbols:
                # Subscribe to kline data
                await self.websocket_handler.subscribe_klines(
                    symbol, 
                    self.timeframe,
                    callback=lambda data, s=symbol: create_tracked_task(self._handle_kline_update, name="_handle_kline_update_task")
                )
                
                # Subscribe to ticker data for real-time price updates
                await self.websocket_handler.subscribe_ticker(
                    symbol,
                    callback=lambda data, s=symbol: create_tracked_task(self._handle_ticker_update, name="_handle_ticker_update_task")
                )
            
            logger.info(f"Subscribed to WebSocket data for symbols: {self.symbols}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to WebSocket data: {str(e)}")
    
    async def _handle_kline_update(self, symbol: str, kline_data: Dict[str, Any]):
        """Handle incoming kline (candlestick) updates.
        
        Args:
            symbol: Trading pair symbol
            kline_data: Kline data from WebSocket
        """
        try:
            # Extract kline information
            kline = kline_data.get('k', {})
            if not kline:
                return
            
            # Check if kline is closed (complete)
            if not kline.get('x', False):
                return  # Skip incomplete klines
            
            timestamp = pd.to_datetime(kline.get('t'), unit='ms')
            open_price = float(kline.get('o', 0))
            high_price = float(kline.get('h', 0))
            low_price = float(kline.get('l', 0))
            close_price = float(kline.get('c', 0))
            volume = float(kline.get('v', 0))
            
            # Update market data
            if symbol in self.market_data:
                new_row = pd.Series({
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                }, name=timestamp)
                
                # Add new row to DataFrame
                self.market_data[symbol] = pd.concat([self.market_data[symbol], new_row.to_frame().T])
                
                # Keep only recent data to manage memory
                if len(self.market_data[symbol]) > self.lookback_periods * 2:
                    self.market_data[symbol] = self.market_data[symbol].tail(self.lookback_periods)
                
                # Recalculate indicators
                self.market_data[symbol] = self._calculate_indicators(self.market_data[symbol])
                
                # Update price buffers
                self.price_buffers[symbol].append(close_price)
                self.volume_buffers[symbol].append(volume)
                if len(self.price_buffers[symbol]) > 50:
                    self.price_buffers[symbol].pop(0)
                    self.volume_buffers[symbol].pop(0)
                
                # Analyze momentum and generate signals
                await self._analyze_momentum(symbol, timestamp)
            
        except Exception as e:
            logger.error(f"Error handling kline update for {symbol}: {str(e)}")
    
    async def _handle_ticker_update(self, symbol: str, ticker_data: Dict[str, Any]):
        """Handle incoming ticker updates for real-time price monitoring.
        
        Args:
            symbol: Trading pair symbol  
            ticker_data: Ticker data from WebSocket
        """
        try:
            # Extract ticker information
            price = float(ticker_data.get('c', 0))  # Last price
            volume_24h = float(ticker_data.get('v', 0))  # 24h volume
            
            # Update latest price for position management
            if symbol not in self.current_positions:
                return
                
            position = self.current_positions[symbol]
            if position and 'entry_price' in position:
                # Calculate unrealized PnL
                entry_price = position['entry_price']
                side = position['side']
                size = position['size']
                
                if side == 'long':
                    unrealized_pnl = (price - entry_price) * size
                else:
                    unrealized_pnl = (entry_price - price) * size
                
                position['unrealized_pnl'] = unrealized_pnl
                position['current_price'] = price
                
                # Check stop loss and take profit
                await self._check_exit_conditions(symbol, price, position)
            
        except Exception as e:
            logger.error(f"Error handling ticker update for {symbol}: {str(e)}")
    
    async def _analyze_momentum(self, symbol: str, timestamp: datetime):
        """Analyze momentum indicators and generate trading signals.
        
        Args:
            symbol: Trading pair symbol
            timestamp: Current timestamp
        """
        try:
            if symbol not in self.market_data:
                return
            
            df = self.market_data[symbol]
            if len(df) < self.rsi_period:
                return
            
            # Get latest indicator values
            latest_data = df.iloc[-1]
            rsi = latest_data['rsi']
            macd = latest_data['macd']
            macd_signal = latest_data['macd_signal']
            macd_hist = latest_data['macd_hist']
            close_price = latest_data['close']
            volume = latest_data['volume']
            
            # Create momentum indicators object
            indicators = MomentumIndicators(
                rsi=rsi,
                rsi_signal=self._get_rsi_signal(rsi),
                macd=macd,
                macd_signal=macd_signal,
                macd_histogram=macd_hist,
                macd_signal_line=self._get_macd_signal(macd, macd_signal, macd_hist),
                price=close_price,
                volume=volume,
                timestamp=timestamp
            )
            
            # Generate momentum signal
            momentum_signal, confidence = self._generate_momentum_signal(indicators, df)
            
            # Calculate position sizing
            position_sizing = await self._calculate_position_sizing(symbol, close_price, momentum_signal)
            
            # Create trade signal
            trade_signal = TradeSignal(
                symbol=symbol,
                signal=momentum_signal,
                confidence=confidence,
                indicators=indicators,
                position_sizing=position_sizing,
                entry_price=close_price,
                timestamp=timestamp,
                metadata={
                    'strategy': 'momentum',
                    'timeframe': self.timeframe,
                    'rsi_period': self.rsi_period,
                    'macd_params': [self.macd_fast, self.macd_slow, self.macd_signal]
                }
            )
            
            # Store latest signal
            self.last_signals[symbol] = trade_signal
            
            # Process signal if strong enough
            if confidence >= 0.7 and momentum_signal in [MomentumSignal.STRONG_BUY, MomentumSignal.STRONG_SELL]:
                await self._process_trading_signal(trade_signal)
            
            # Log signal information
            logger.info(
                f"Momentum signal for {symbol}: {momentum_signal.value} "
                f"(confidence: {confidence:.2f}, RSI: {rsi:.1f}, MACD: {macd:.4f})"
            )
            
        except Exception as e:
            logger.error(f"Error analyzing momentum for {symbol}: {str(e)}")
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Get RSI signal interpretation.
        
        Args:
            rsi: RSI value
            
        Returns:
            str: RSI signal interpretation
        """
        if rsi <= self.rsi_oversold:
            return "oversold"
        elif rsi >= self.rsi_overbought:
            return "overbought"
        elif rsi < 45:
            return "bearish"
        elif rsi > 55:
            return "bullish"
        else:
            return "neutral"
    
    def _get_macd_signal(self, macd: float, macd_signal: float, macd_hist: float) -> str:
        """Get MACD signal interpretation.
        
        Args:
            macd: MACD line value
            macd_signal: MACD signal line value
            macd_hist: MACD histogram value
            
        Returns:
            str: MACD signal interpretation
        """
        if macd > macd_signal and macd_hist > 0:
            return "bullish_crossover"
        elif macd < macd_signal and macd_hist < 0:
            return "bearish_crossover"
        elif macd > macd_signal:
            return "bullish"
        elif macd < macd_signal:
            return "bearish"
        else:
            return "neutral"
    
    def _generate_momentum_signal(
        self, 
        indicators: MomentumIndicators, 
        df: pd.DataFrame
    ) -> Tuple[MomentumSignal, float]:
        """Generate momentum trading signal based on indicators.
        
        Args:
            indicators: Current momentum indicators
            df: Historical data DataFrame
            
        Returns:
            Tuple of (MomentumSignal, confidence_score)
        """
        try:
            signal_score = 0
            confidence_factors = []
            
            # RSI Analysis
            rsi_score = 0
            if indicators.rsi <= self.rsi_oversold:
                rsi_score = 2  # Strong buy signal
                confidence_factors.append(0.8)
            elif indicators.rsi >= self.rsi_overbought:
                rsi_score = -2  # Strong sell signal
                confidence_factors.append(0.8)
            elif indicators.rsi < 45:
                rsi_score = -1  # Bearish
                confidence_factors.append(0.5)
            elif indicators.rsi > 55:
                rsi_score = 1  # Bullish
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.2)
            
            signal_score += rsi_score
            
            # MACD Analysis
            macd_score = 0
            if indicators.macd_signal_line == "bullish_crossover":
                macd_score = 2
                confidence_factors.append(0.9)
            elif indicators.macd_signal_line == "bearish_crossover":
                macd_score = -2
                confidence_factors.append(0.9)
            elif indicators.macd_signal_line == "bullish":
                macd_score = 1
                confidence_factors.append(0.6)
            elif indicators.macd_signal_line == "bearish":
                macd_score = -1
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.3)
            
            signal_score += macd_score
            
            # Trend Analysis (using short-term moving average)
            if len(df) >= 20:
                sma_20 = df['close'].tail(20).mean()
                trend_score = 0
                if indicators.price > sma_20 * 1.01:  # Above SMA by 1%
                    trend_score = 1
                    confidence_factors.append(0.4)
                elif indicators.price < sma_20 * 0.99:  # Below SMA by 1%
                    trend_score = -1
                    confidence_factors.append(0.4)
                else:
                    confidence_factors.append(0.2)
                
                signal_score += trend_score
            
            # Volume Analysis
            volume_score = 0
            if len(df) >= 10:
                avg_volume = df['volume'].tail(10).mean()
                if indicators.volume > avg_volume * 1.5:  # High volume
                    volume_score = 0.5
                    confidence_factors.append(0.3)
                elif indicators.volume < avg_volume * 0.5:  # Low volume
                    volume_score = -0.5
                    confidence_factors.append(0.1)
                else:
                    confidence_factors.append(0.2)
            
            signal_score += volume_score
            
            # Determine signal type based on score
            if signal_score >= 3:
                momentum_signal = MomentumSignal.STRONG_BUY
            elif signal_score >= 1:
                momentum_signal = MomentumSignal.BUY
            elif signal_score <= -3:
                momentum_signal = MomentumSignal.STRONG_SELL
            elif signal_score <= -1:
                momentum_signal = MomentumSignal.SELL
            else:
                momentum_signal = MomentumSignal.NEUTRAL
            
            # Calculate confidence score
            confidence = np.mean(confidence_factors) if confidence_factors else 0.0
            
            return momentum_signal, confidence
            
        except Exception as e:
            logger.error(f"Error generating momentum signal: {str(e)}")
            return MomentumSignal.NEUTRAL, 0.0
    
    async def _calculate_position_sizing(
        self, 
        symbol: str, 
        entry_price: float, 
        signal: MomentumSignal
    ) -> PositionSizing:
        """Calculate position sizing based on risk management rules.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price for the position
            signal: Momentum signal type
            
        Returns:
            PositionSizing: Position sizing calculation results
        """
        try:
            # Get account balance
            account_balance = await self._get_account_balance()
            if not account_balance:
                account_balance = 10000.0  # Default for demo/testing
            
            # Calculate risk amount per trade
            risk_amount = account_balance * self.risk_per_trade
            
            # Calculate stop loss and take profit levels
            if signal in [MomentumSignal.STRONG_BUY, MomentumSignal.BUY]:
                stop_loss = entry_price * (1 - self.stop_loss_pct)
                take_profit = entry_price * (1 + self.take_profit_pct)
                risk_per_unit = entry_price - stop_loss
            else:
                stop_loss = entry_price * (1 + self.stop_loss_pct)
                take_profit = entry_price * (1 - self.take_profit_pct)
                risk_per_unit = stop_loss - entry_price
            
            # Calculate position size
            if risk_per_unit > 0:
                position_size = risk_amount / risk_per_unit
            else:
                position_size = 0
            
            # Apply maximum position size limits
            max_position_value = account_balance * 0.1  # Max 10% of account per position
            max_position_size = max_position_value / entry_price
            position_size = min(position_size, max_position_size)
            
            # Calculate risk-reward ratio
            if risk_per_unit > 0:
                reward_per_unit = abs(take_profit - entry_price)
                risk_reward_ratio = reward_per_unit / risk_per_unit
            else:
                risk_reward_ratio = 0
            
            return PositionSizing(
                account_balance=account_balance,
                risk_amount=risk_amount,
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio
            )
            
        except Exception as e:
            logger.error(f"Error calculating position sizing for {symbol}: {str(e)}")
            return PositionSizing(0, 0, 0, 0, 0, 0)
    
    async def _get_account_balance(self) -> float:
        """Get current account balance from exchange.
        
        Returns:
            float: Account balance in USDT
        """
        try:
            if not self.exchange:
                return 0.0
            
            balance_info = await self.exchange.get_balance()
            if balance_info and 'USDT' in balance_info:
                return float(balance_info['USDT']['free'])
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return 0.0
    
    async def _process_trading_signal(self, signal: TradeSignal):
        """Process a trading signal and potentially execute trades.
        
        Args:
            signal: Trade signal to process
        """
        try:
            # Check if we already have a position in this symbol
            if signal.symbol in self.current_positions:
                current_position = self.current_positions[signal.symbol]
                if current_position and current_position.get('status') == 'open':
                    logger.info(f"Already have open position in {signal.symbol}, skipping signal")
                    return
            
            # Check maximum positions limit
            open_positions = sum(1 for pos in self.current_positions.values() 
                               if pos and pos.get('status') == 'open')
            if open_positions >= self.max_positions:
                logger.info(f"Maximum positions ({self.max_positions}) reached, skipping signal")
                return
            
            # Validate signal strength
            if signal.confidence < 0.7:
                logger.info(f"Signal confidence {signal.confidence:.2f} too low, skipping")
                return
            
            # Validate position sizing
            if signal.position_sizing.position_size <= 0:
                logger.warning(f"Invalid position size for {signal.symbol}, skipping")
                return
            
            # Log the trading signal
            logger.info(
                f"Processing trading signal: {signal.symbol} {signal.signal.value} "
                f"Size: {signal.position_sizing.position_size:.4f} "
                f"Entry: {signal.entry_price:.4f} "
                f"SL: {signal.position_sizing.stop_loss:.4f} "
                f"TP: {signal.position_sizing.take_profit:.4f}"
            )
            
            # Here you would normally execute the actual trade
            # For now, we'll simulate the trade execution
            await self._simulate_trade_execution(signal)
            
            # Send signal to the broader system
            if self.signal_generator:
                signal_data = {
                    'symbol': signal.symbol,
                    'type': signal.signal.value,
                    'confidence': signal.confidence,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.position_sizing.stop_loss,
                    'take_profit': signal.position_sizing.take_profit,
                    'position_size': signal.position_sizing.position_size,
                    'strategy': 'momentum',
                    'timestamp': signal.timestamp
                }
                
                # Generate signal through existing system
                await self.signal_generator.process_signal(signal_data)
            
        except Exception as e:
            logger.error(f"Error processing trading signal: {str(e)}")
    
    async def _simulate_trade_execution(self, signal: TradeSignal):
        """Simulate trade execution for testing purposes.
        
        Args:
            signal: Trade signal to execute
        """
        try:
            # Determine side
            side = 'long' if signal.signal in [MomentumSignal.STRONG_BUY, MomentumSignal.BUY] else 'short'
            
            # Create position record
            position = {
                'symbol': signal.symbol,
                'side': side,
                'size': signal.position_sizing.position_size,
                'entry_price': signal.entry_price,
                'stop_loss': signal.position_sizing.stop_loss,
                'take_profit': signal.position_sizing.take_profit,
                'status': 'open',
                'entry_time': signal.timestamp,
                'unrealized_pnl': 0.0,
                'current_price': signal.entry_price
            }
            
            # Store position
            self.current_positions[signal.symbol] = position
            
            # Update performance metrics
            self.performance_metrics['total_trades'] += 1
            
            logger.info(
                f"Simulated trade execution: {signal.symbol} {side.upper()} "
                f"{signal.position_sizing.position_size:.4f} @ {signal.entry_price:.4f}"
            )
            
        except Exception as e:
            logger.error(f"Error simulating trade execution: {str(e)}")
    
    async def _check_exit_conditions(self, symbol: str, current_price: float, position: Dict[str, Any]):
        """Check if position should be closed based on stop loss or take profit.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            position: Position data
        """
        try:
            side = position['side']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            should_close = False
            exit_reason = ""
            
            if side == 'long':
                if current_price <= stop_loss:
                    should_close = True
                    exit_reason = "stop_loss"
                elif current_price >= take_profit:
                    should_close = True
                    exit_reason = "take_profit"
            else:  # short
                if current_price >= stop_loss:
                    should_close = True
                    exit_reason = "stop_loss"
                elif current_price <= take_profit:
                    should_close = True
                    exit_reason = "take_profit"
            
            if should_close:
                await self._close_position(symbol, current_price, exit_reason)
            
        except Exception as e:
            logger.error(f"Error checking exit conditions for {symbol}: {str(e)}")
    
    async def _close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position and update performance metrics.
        
        Args:
            symbol: Trading pair symbol
            exit_price: Exit price
            reason: Reason for closing position
        """
        try:
            if symbol not in self.current_positions:
                return
            
            position = self.current_positions[symbol]
            if not position or position.get('status') != 'open':
                return
            
            # Calculate PnL
            entry_price = position['entry_price']
            side = position['side']
            size = position['size']
            
            if side == 'long':
                pnl = (exit_price - entry_price) * size
            else:
                pnl = (entry_price - exit_price) * size
            
            # Update position
            position['status'] = 'closed'
            position['exit_price'] = exit_price
            position['exit_time'] = datetime.now()
            position['exit_reason'] = reason
            position['realized_pnl'] = pnl
            
            # Update performance metrics
            if pnl > 0:
                self.performance_metrics['winning_trades'] += 1
            else:
                self.performance_metrics['losing_trades'] += 1
            
            self.performance_metrics['total_pnl'] += pnl
            
            logger.info(
                f"Closed position: {symbol} {side.upper()} @ {exit_price:.4f} "
                f"PnL: {pnl:.4f} Reason: {reason}"
            )
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
    
    async def start(self):
        """Start the momentum strategy."""
        try:
            if not await self.initialize():
                logger.error("Failed to initialize MomentumStrategy")
                return False
            
            self.is_running = True
            logger.info("MomentumStrategy started successfully")
            
            # Start background tasks
            create_tracked_task(self._performance_reporting_loop(), name="auto_tracked_task")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start MomentumStrategy: {str(e)}")
            return False
    
    async def stop(self):
        """Stop the momentum strategy."""
        try:
            self.is_running = False
            
            # Close all open positions
            for symbol in list(self.current_positions.keys()):
                position = self.current_positions[symbol]
                if position and position.get('status') == 'open':
                    current_price = position.get('current_price', position.get('entry_price', 0))
                    await self._close_position(symbol, current_price, 'strategy_stop')
            
            logger.info("MomentumStrategy stopped")
            
        except Exception as e:
            logger.error(f"Error stopping MomentumStrategy: {str(e)}")
    
    async def _performance_reporting_loop(self):
        """Background task for performance reporting."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Report every 5 minutes
                
                if self.performance_metrics['total_trades'] > 0:
                    win_rate = (self.performance_metrics['winning_trades'] / 
                               self.performance_metrics['total_trades']) * 100
                    
                    logger.info(
                        f"Performance Summary - "
                        f"Total Trades: {self.performance_metrics['total_trades']} "
                        f"Win Rate: {win_rate:.1f}% "
                        f"Total PnL: {self.performance_metrics['total_pnl']:.4f} USDT"
                    )
                
            except Exception as e:
                logger.error(f"Error in performance reporting: {str(e)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics.
        
        Returns:
            Dict with performance statistics
        """
        try:
            metrics = self.performance_metrics.copy()
            
            if metrics['total_trades'] > 0:
                metrics['win_rate'] = (metrics['winning_trades'] / metrics['total_trades']) * 100
                metrics['average_pnl'] = metrics['total_pnl'] / metrics['total_trades']
            else:
                metrics['win_rate'] = 0.0
                metrics['average_pnl'] = 0.0
            
            # Add current positions info
            open_positions = {k: v for k, v in self.current_positions.items() 
                            if v and v.get('status') == 'open'}
            metrics['open_positions'] = len(open_positions)
            metrics['current_positions'] = open_positions
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return self.performance_metrics.copy()
    
    def get_latest_signals(self) -> Dict[str, TradeSignal]:
        """Get latest signals for all symbols.
        
        Returns:
            Dict mapping symbols to their latest signals
        """
        return self.last_signals.copy()