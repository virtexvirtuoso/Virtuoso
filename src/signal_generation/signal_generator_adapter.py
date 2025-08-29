"""
Signal Generator Adapter for Breaking Circular Dependencies.

This adapter wraps the existing SignalGenerator to implement the new interfaces
and eliminate circular dependencies by using the service coordinator.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from ..core.interfaces.signal_processing import ISignalGenerator, IEventSubscriber
from ..core.coordination import ServiceCoordinator, Event, EventType

if TYPE_CHECKING:
    from .signal_generator import SignalGenerator


class SignalGeneratorAdapter(ISignalGenerator, IEventSubscriber):
    """
    Adapter that wraps SignalGenerator to eliminate circular dependencies.
    
    This adapter:
    1. Implements ISignalGenerator interface
    2. Subscribes to analysis completion events
    3. Publishes signal generation events
    4. Eliminates direct dependency on AlertManager
    """
    
    def __init__(
        self,
        signal_generator: 'SignalGenerator',
        coordinator: ServiceCoordinator,
        logger: Optional[logging.Logger] = None
    ):
        self.signal_generator = signal_generator
        self.coordinator = coordinator
        self.logger = logger or logging.getLogger(__name__)
        
        # Remove alert_manager dependency from SignalGenerator
        # The coordinator will handle alert communication
        if hasattr(self.signal_generator, 'alert_manager'):
            self.signal_generator.alert_manager = None
    
    # ISignalGenerator implementation
    
    async def generate_signal(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a trading signal based on market data and analysis."""
        try:
            # Use the existing SignalGenerator logic but without direct AlertManager calls
            signal_data = await self._generate_signal_internal(symbol, market_data, analysis_result)
            
            # If signal is valid, publish event instead of directly calling AlertManager
            if signal_data and signal_data.get('signal_type') != 'NEUTRAL':
                await self._publish_signal_generated(symbol, signal_data)
            
            return signal_data
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}")
            return {}
    
    async def calculate_confluence_score(self, analysis_data: Dict[str, Any]) -> float:
        """Calculate confluence score from analysis data."""
        if hasattr(self.signal_generator, 'calculate_confluence_score'):
            return await self.signal_generator.calculate_confluence_score(analysis_data)
        return 0.0
    
    def get_signal_thresholds(self) -> Dict[str, float]:
        """Get current signal generation thresholds."""
        if hasattr(self.signal_generator, 'get_thresholds'):
            return self.signal_generator.get_thresholds()
        
        # Return default thresholds
        return {
            'buy_threshold': 60.0,
            'sell_threshold': 40.0,
            'neutral_buffer': 5.0
        }
    
    # IEventSubscriber implementation
    
    def get_subscribed_events(self) -> List[str]:
        """Get list of event types this subscriber handles."""
        return [
            EventType.ANALYSIS_COMPLETED.value,
            EventType.MARKET_DATA_UPDATED.value
        ]
    
    async def handle_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        source_service: str
    ) -> None:
        """Handle incoming events."""
        try:
            if event_type == EventType.ANALYSIS_COMPLETED.value:
                await self._handle_analysis_completed(event_data, source_service)
            elif event_type == EventType.MARKET_DATA_UPDATED.value:
                await self._handle_market_data_updated(event_data, source_service)
        except Exception as e:
            self.logger.error(f"Error handling event {event_type}: {e}")
    
    # Internal methods
    
    async def _generate_signal_internal(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Internal signal generation logic without AlertManager dependency."""
        
        # Extract confluence score
        confluence_score = analysis_result.get('confluence_score', 0)
        
        # Get thresholds
        thresholds = self.get_signal_thresholds()
        buy_threshold = thresholds.get('buy_threshold', 60)
        sell_threshold = thresholds.get('sell_threshold', 40)
        
        # Determine signal type
        if confluence_score >= buy_threshold:
            signal_type = 'BUY'
        elif confluence_score <= sell_threshold:
            signal_type = 'SELL'
        else:
            signal_type = 'NEUTRAL'
        
        # Create signal data
        signal_data = {
            'symbol': symbol,
            'signal_type': signal_type,
            'confluence_score': confluence_score,
            'confidence': min(abs(confluence_score - 50) / 50, 1.0),
            'timestamp': datetime.now().isoformat(),
            'analysis_id': analysis_result.get('analysis_id'),
            'market_data': market_data,
            'analysis_result': analysis_result
        }
        
        # Add trade parameters if it's a trading signal
        if signal_type in ['BUY', 'SELL']:
            signal_data.update(self._calculate_trade_parameters(symbol, market_data, signal_type))
        
        self.logger.info(f"Generated {signal_type} signal for {symbol} (score: {confluence_score:.2f})")
        
        return signal_data
    
    def _calculate_trade_parameters(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        signal_type: str
    ) -> Dict[str, Any]:
        """Calculate trade parameters for the signal."""
        
        # Get current price from market data
        current_price = None
        ohlcv_data = market_data.get('ohlcv', {})
        
        # Try to get price from different timeframes
        for timeframe in ['base', 'ltf', 'mtf', 'htf']:
            if timeframe in ohlcv_data and ohlcv_data[timeframe]:
                current_price = ohlcv_data[timeframe][-1][4]  # Close price
                break
        
        if not current_price:
            return {}
        
        # Calculate basic trade parameters
        risk_percent = 0.02  # 2% risk
        reward_risk_ratio = 2.0
        
        if signal_type == 'BUY':
            stop_loss = current_price * 0.98  # 2% below entry
            take_profit = current_price * (1 + risk_percent * reward_risk_ratio)
        else:  # SELL
            stop_loss = current_price * 1.02  # 2% above entry
            take_profit = current_price * (1 - risk_percent * reward_risk_ratio)
        
        return {
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_percent': risk_percent,
            'reward_risk_ratio': reward_risk_ratio
        }
    
    async def _publish_signal_generated(self, symbol: str, signal_data: Dict[str, Any]) -> None:
        """Publish signal generated event instead of directly calling AlertManager."""
        await self.coordinator.publish_event(Event(
            event_type=EventType.SIGNAL_GENERATED,
            source_service="signal_generator",
            target_services=["alert_manager"],
            data={
                "symbol": symbol,
                "signal_data": signal_data,
                "timestamp": datetime.now().isoformat()
            }
        ))
        
        self.logger.debug(f"Published signal generated event for {symbol}")
    
    async def _handle_analysis_completed(self, event_data: Dict[str, Any], source_service: str) -> None:
        """Handle analysis completed event."""
        symbol = event_data.get('symbol')
        analysis_result = event_data.get('analysis_result')
        market_data = event_data.get('market_data', {})
        
        if not symbol or not analysis_result:
            self.logger.warning("Invalid analysis completed event data")
            return
        
        # Generate signal based on analysis
        await self.generate_signal(symbol, market_data, analysis_result)
    
    async def _handle_market_data_updated(self, event_data: Dict[str, Any], source_service: str) -> None:
        """Handle market data updated event."""
        # For now, just log. Could be used for real-time signal updates
        symbol = event_data.get('symbol')
        self.logger.debug(f"Market data updated for {symbol} from {source_service}")