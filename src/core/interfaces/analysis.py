"""
Analysis interfaces for dependency injection and type safety.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional, List, Union, runtime_checkable
from datetime import datetime
import pandas as pd

@runtime_checkable
class AnalysisInterface(Protocol):
    """Interface for analysis components."""
    
    @abstractmethod
    async def analyze(self, data: Union[pd.DataFrame, Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform analysis on data.
        
        Args:
            data: Data to analyze
            context: Optional analysis context
            
        Returns:
            Analysis results
        """
        pass
    
    @abstractmethod
    def get_required_data_columns(self) -> List[str]:
        """Get required data columns for analysis."""
        pass
    
    @abstractmethod
    def get_analysis_type(self) -> str:
        """Get the type of analysis performed."""
        pass

@runtime_checkable
class IndicatorInterface(Protocol):
    """Interface for technical indicators."""
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **params) -> Union[pd.Series, pd.DataFrame]:
        """
        Calculate indicator values.
        
        Args:
            data: Price/volume data
            **params: Indicator-specific parameters
            
        Returns:
            Calculated indicator values
        """
        pass
    
    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for the indicator."""
        pass
    
    @abstractmethod
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate if data is suitable for indicator calculation."""
        pass

@runtime_checkable
class ConfluenceAnalyzerInterface(Protocol):
    """Interface for confluence analysis."""
    
    @abstractmethod
    async def analyze_confluence(self, symbol: str, timeframe: str, data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Analyze signal confluence.
        
        Returns:
            Dict with keys:
            - score: Overall confluence score
            - signals: Individual signal contributions
            - recommendation: Trading recommendation
            - confidence: Confidence level
        """
        pass
    
    @abstractmethod
    def get_signal_weights(self) -> Dict[str, float]:
        """Get current signal weights."""
        pass
    
    @abstractmethod
    def update_signal_weights(self, weights: Dict[str, float]) -> None:
        """Update signal weights."""
        pass

@runtime_checkable
class BacktestInterface(Protocol):
    """Interface for backtesting engines."""
    
    @abstractmethod
    async def run_backtest(self, strategy: Any, data: pd.DataFrame, initial_capital: float = 10000) -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Returns:
            Dict with backtest results including:
            - total_return
            - sharpe_ratio
            - max_drawdown
            - trades
            - equity_curve
        """
        pass
    
    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics from last backtest."""
        pass

class AnalysisAdapter:
    """Adapter to make existing analyzers compatible with AnalysisInterface."""
    
    def __init__(self, analyzer: Any):
        self.analyzer = analyzer
        
    async def analyze(self, data: Union[pd.DataFrame, Dict[str, Any]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform analysis on data."""
        if hasattr(self.analyzer, 'analyze'):
            if context:
                return await self.analyzer.analyze(data, context)
            return await self.analyzer.analyze(data)
        elif hasattr(self.analyzer, 'process'):
            return await self.analyzer.process(data)
        else:
            raise NotImplementedError(f"Analyzer {type(self.analyzer)} has no analyze or process method")
            
    def get_required_data_columns(self) -> List[str]:
        """Get required data columns for analysis."""
        if hasattr(self.analyzer, 'get_required_data_columns'):
            return self.analyzer.get_required_data_columns()
        elif hasattr(self.analyzer, 'required_columns'):
            return self.analyzer.required_columns
        else:
            return ['open', 'high', 'low', 'close', 'volume']
            
    def get_analysis_type(self) -> str:
        """Get the type of analysis performed."""
        if hasattr(self.analyzer, 'get_analysis_type'):
            return self.analyzer.get_analysis_type()
        elif hasattr(self.analyzer, 'analysis_type'):
            return self.analyzer.analysis_type
        else:
            return type(self.analyzer).__name__