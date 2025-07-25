"""
Confluence Analysis Interface

This module defines the public interface for the proprietary confluence engine.
The actual implementation is kept private.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd


class IConfluenceAnalyzer(ABC):
    """Interface for confluence analysis engine."""
    
    @abstractmethod
    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data using confluence methodology.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary with confluence analysis results
        """
        pass
    
    @abstractmethod
    def get_component_weights(self) -> Dict[str, float]:
        """Get current component weights."""
        pass
    
    @abstractmethod
    def validate_market_data(self, market_data: Dict[str, Any]) -> bool:
        """Validate market data structure."""
        pass


class IIndicatorBase(ABC):
    """Base interface for all indicators."""
    
    @abstractmethod
    async def calculate(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate indicator values."""
        pass
    
    @abstractmethod
    def required_data(self) -> List[str]:
        """Return list of required data fields."""
        pass
    
    @abstractmethod
    def validate_input(self, market_data: Dict[str, Any]) -> bool:
        """Validate input data."""
        pass