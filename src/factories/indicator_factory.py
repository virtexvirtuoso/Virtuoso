"""
Indicator Factory

Factory pattern to instantiate proprietary indicators without exposing implementation.
"""

from typing import Dict, Any, Optional
import logging
from ..interfaces.confluence_interface import IConfluenceAnalyzer, IIndicatorBase


class IndicatorFactory:
    """Factory for creating indicator instances."""
    
    @staticmethod
    def create_confluence_analyzer(config: Dict[str, Any], 
                                   logger: Optional[logging.Logger] = None) -> IConfluenceAnalyzer:
        """
        Create confluence analyzer instance.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
            
        Returns:
            IConfluenceAnalyzer instance
        """
        # Import is done inside method to keep implementation private
        from ..core.analysis.confluence import ConfluenceAnalyzer
        return ConfluenceAnalyzer(config, logger)
    
    @staticmethod
    def create_technical_indicators(config: Dict[str, Any],
                                    logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create technical indicators instance."""
        from ..indicators.technical_indicators import TechnicalIndicators
        return TechnicalIndicators(config, logger)
    
    @staticmethod
    def create_volume_indicators(config: Dict[str, Any],
                                 logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create volume indicators instance."""
        from ..indicators.volume_indicators import VolumeIndicators
        return VolumeIndicators(config, logger)
    
    @staticmethod
    def create_orderbook_indicators(config: Dict[str, Any],
                                    logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create orderbook indicators instance."""
        from ..indicators.orderbook_indicators import OrderbookIndicators
        return OrderbookIndicators(config, logger)
    
    @staticmethod
    def create_orderflow_indicators(config: Dict[str, Any],
                                    logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create orderflow indicators instance."""
        from ..indicators.orderflow_indicators import OrderflowIndicators
        return OrderflowIndicators(config, logger)
    
    @staticmethod
    def create_price_structure_indicators(config: Dict[str, Any],
                                          logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create price structure indicators instance."""
        from ..indicators.price_structure_indicators import PriceStructureIndicators
        return PriceStructureIndicators(config, logger)
    
    @staticmethod
    def create_sentiment_indicators(config: Dict[str, Any],
                                    logger: Optional[logging.Logger] = None) -> IIndicatorBase:
        """Create sentiment indicators instance."""
        from ..indicators.sentiment_indicators import SentimentIndicators
        return SentimentIndicators(config, logger)