"""
Data Processing Interfaces for Monitoring System.

Clean interfaces for data fetching and validation with single responsibilities.
"""

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


@runtime_checkable
class IDataFetcher(Protocol):
    """
    Interface for fetching market data.
    
    Single Responsibility: Fetch market data from exchanges or data sources.
    """
    
    async def fetch_market_data(self, symbol: str, timeframes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch market data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            timeframes: Optional list of timeframes to fetch
            
        Returns:
            Dictionary containing market data with structure:
            {
                'symbol': str,
                'ohlcv': Dict[timeframe, List[candle_data]],
                'orderbook': Dict,
                'trades': List,
                'ticker': Dict,
                'timestamp': float
            }
        """
        ...
    
    async def fetch_multiple_symbols(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch market data for multiple symbols efficiently.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dictionary mapping symbol -> market data
        """
        ...


@runtime_checkable
class IDataValidator(Protocol):
    """
    Interface for validating data quality.
    
    Single Responsibility: Ensure data integrity and completeness.
    """
    
    async def validate_market_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate market data for completeness and integrity.
        
        Args:
            data: Market data dictionary to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        ...
    
    async def validate_ohlcv_data(self, ohlcv_data: Dict[str, Any]) -> bool:
        """
        Validate OHLCV data specifically.
        
        Args:
            ohlcv_data: OHLCV data to validate
            
        Returns:
            True if valid, False otherwise
        """
        ...
    
    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors from last validation.
        
        Returns:
            List of error messages
        """
        ...


# Abstract base classes for concrete implementations

class DataFetcherBase(ABC):
    """Base class for data fetchers with common functionality."""
    
    def __init__(self, exchange_manager, logger: Optional[Any] = None):
        self.exchange_manager = exchange_manager
        self.logger = logger
        
        # Common settings
        self.default_timeframes = ['1m', '5m', '30m', '4h']
        self.fetch_timeout = 30.0
    
    @abstractmethod
    async def fetch_market_data(self, symbol: str, timeframes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Implement symbol-specific data fetching."""
        pass
    
    async def _fetch_with_retry(self, fetch_func, max_retries: int = 3) -> Any:
        """Helper method for fetching with retry logic."""
        for attempt in range(max_retries):
            try:
                return await fetch_func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                if self.logger:
                    self.logger.warning(f"Fetch attempt {attempt + 1} failed: {e}")


class DataValidatorBase(ABC):
    """Base class for data validators with common functionality."""
    
    def __init__(self, logger: Optional[Any] = None):
        self.logger = logger
        self.validation_errors = []
        
        # Validation rules
        self.required_fields = ['symbol', 'timestamp']
        self.min_candles_required = 10
    
    @abstractmethod
    async def validate_market_data(self, data: Dict[str, Any]) -> bool:
        """Implement validation logic."""
        pass
    
    def _clear_errors(self):
        """Clear validation errors."""
        self.validation_errors = []
    
    def _add_error(self, error: str):
        """Add validation error."""
        self.validation_errors.append(error)
        if self.logger:
            self.logger.warning(f"Validation error: {error}")
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.validation_errors.copy()