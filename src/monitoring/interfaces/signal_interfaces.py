"""
Signal Processing Interfaces for Monitoring System.

Clean interfaces for signal analysis and trade parameter calculation.
"""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


@runtime_checkable
class ISignalAnalyzer(Protocol):
    """
    Interface for analyzing market data and generating signals.
    
    Single Responsibility: Analyze market data and produce trading signals.
    """
    
    async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and generate signal analysis.
        
        Args:
            symbol: Trading pair symbol
            market_data: Market data to analyze
            
        Returns:
            Analysis result with structure:
            {
                'symbol': str,
                'confluence_score': float,
                'signal_strength': float,
                'analysis_components': Dict[str, Any],
                'timestamp': float
            }
        """
        ...
    
    async def calculate_confluence_score(self, analysis_data: Dict[str, Any]) -> float:
        """
        Calculate confluence score from analysis components.
        
        Args:
            analysis_data: Raw analysis data
            
        Returns:
            Confluence score (0-100)
        """
        ...


@runtime_checkable
class ITradeParameterCalculator(Protocol):
    """
    Interface for calculating trade parameters.
    
    Single Responsibility: Calculate trading parameters like stop loss, take profit, position size.
    """
    
    def calculate_trade_parameters(
        self, 
        signal_data: Dict[str, Any], 
        account_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate trade parameters for a signal.
        
        Args:
            signal_data: Signal data including entry price and signal type
            account_info: Optional account information for position sizing
            
        Returns:
            Trade parameters with structure:
            {
                'entry_price': float,
                'stop_loss': float,
                'take_profit': float,
                'position_size': float,
                'risk_amount': float,
                'reward_risk_ratio': float
            }
        """
        ...
    
    def calculate_position_size(
        self, 
        entry_price: float, 
        stop_loss: float, 
        risk_percent: float = 0.02,
        account_balance: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            risk_percent: Risk percentage (default 2%)
            account_balance: Account balance for calculation
            
        Returns:
            Position size
        """
        ...
    
    def calculate_stop_loss(self, entry_price: float, signal_type: str, atr: Optional[float] = None) -> float:
        """
        Calculate stop loss based on entry price and market volatility.
        
        Args:
            entry_price: Entry price
            signal_type: 'BUY' or 'SELL'
            atr: Average True Range for volatility-based stop loss
            
        Returns:
            Stop loss price
        """
        ...


# Abstract base classes for concrete implementations

class SignalAnalyzerBase(ABC):
    """Base class for signal analyzers with common functionality."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[Any] = None):
        self.config = config
        self.logger = logger
        
        # Default analysis settings
        self.confluence_weights = config.get('confluence_weights', {
            'technical': 0.3,
            'volume': 0.2,
            'orderbook': 0.2,
            'sentiment': 0.1,
            'momentum': 0.2
        })
        
        self.signal_thresholds = config.get('signal_thresholds', {
            'long_threshold': 60.0,
            'short_threshold': 40.0,
            'neutral_buffer': 5.0
        })
    
    @abstractmethod
    async def analyze_market_data(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Implement market data analysis."""
        pass
    
    async def _analyze_technical_indicators(self, ohlcv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Common technical analysis logic."""
        # Placeholder for technical analysis
        return {'technical_score': 50.0}
    
    async def _analyze_volume_profile(self, volume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Common volume analysis logic."""
        # Placeholder for volume analysis
        return {'volume_score': 50.0}


class TradeParameterCalculatorBase(ABC):
    """Base class for trade parameter calculators with common functionality."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[Any] = None):
        self.config = config
        self.logger = logger
        
        # Default risk management settings
        self.default_risk_percent = config.get('risk_percent', 0.02)  # 2%
        self.default_reward_risk_ratio = config.get('reward_risk_ratio', 2.0)
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% of account
    
    @abstractmethod
    def calculate_trade_parameters(
        self, 
        signal_data: Dict[str, Any], 
        account_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Implement trade parameter calculation."""
        pass
    
    def _calculate_risk_amount(self, entry_price: float, stop_loss: float, position_size: float) -> float:
        """Calculate risk amount for the trade."""
        return abs(entry_price - stop_loss) * position_size
    
    def _validate_trade_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate calculated trade parameters."""
        required_fields = ['entry_price', 'stop_loss', 'take_profit', 'position_size']
        return all(field in params and params[field] is not None for field in required_fields)