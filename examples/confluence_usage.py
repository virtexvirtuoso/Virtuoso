"""
Confluence Engine Usage Example

This example demonstrates how to use the confluence analysis engine
without exposing the proprietary implementation.
"""

import asyncio
from typing import Dict, Any
import logging

from src.factories.indicator_factory import IndicatorFactory
from src.config.config_manager import ConfigManager


async def analyze_market_confluence(symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    """
    Example of using the confluence engine.
    
    Args:
        symbol: Trading symbol to analyze
        
    Returns:
        Confluence analysis results
    """
    # Setup logging
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.config
    
    # Create confluence analyzer using factory
    confluence = IndicatorFactory.create_confluence_analyzer(config, logger)
    
    # Prepare market data (example structure)
    market_data = {
        'symbol': symbol,
        'ohlcv_data': {
            'base': None,  # Would contain actual OHLCV data
            'ltf': None,   # Lower timeframe data
            'mtf': None,   # Medium timeframe data
            'htf': None    # Higher timeframe data
        },
        'orderbook': None,  # Would contain orderbook data
        'trades': None,     # Would contain recent trades
        'sentiment_data': None  # Would contain sentiment metrics
    }
    
    # Validate data
    if not confluence.validate_market_data(market_data):
        logger.error("Invalid market data structure")
        return {}
    
    # Perform analysis
    try:
        result = await confluence.analyze(market_data)
        
        # Access results
        confluence_score = result.get('confluence_score', 0)
        component_scores = result.get('component_scores', {})
        reliability = result.get('reliability', 0)
        signals = result.get('signals', [])
        
        logger.info(f"Confluence Score: {confluence_score:.2f}")
        logger.info(f"Reliability: {reliability:.2f}")
        logger.info(f"Signals: {signals}")
        
        return result
        
    except Exception as e:
        logger.error(f"Confluence analysis failed: {e}")
        return {}


async def analyze_individual_indicators(symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    """
    Example of using individual indicators.
    
    Args:
        symbol: Trading symbol to analyze
        
    Returns:
        Individual indicator results
    """
    logger = logging.getLogger(__name__)
    config_manager = ConfigManager()
    config = config_manager.config
    
    # Create indicators using factory
    technical = IndicatorFactory.create_technical_indicators(config, logger)
    volume = IndicatorFactory.create_volume_indicators(config, logger)
    orderbook = IndicatorFactory.create_orderbook_indicators(config, logger)
    
    # Prepare market data
    market_data = {
        'symbol': symbol,
        'ohlcv_data': None,  # Would contain actual data
        'orderbook': None,
        'trades': None
    }
    
    results = {}
    
    # Calculate each indicator
    try:
        results['technical'] = await technical.calculate(market_data)
        results['volume'] = await volume.calculate(market_data)
        results['orderbook'] = await orderbook.calculate(market_data)
        
        return results
        
    except Exception as e:
        logger.error(f"Indicator calculation failed: {e}")
        return {}


def main():
    """Main example function."""
    # Run confluence analysis
    confluence_result = asyncio.run(analyze_market_confluence('BTCUSDT'))
    
    # Run individual indicators
    indicator_results = asyncio.run(analyze_individual_indicators('BTCUSDT'))
    
    print("Analysis complete!")


if __name__ == "__main__":
    main()