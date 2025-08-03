#!/usr/bin/env python3
"""Test confluence breakdown logging."""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.analysis.confluence import ConfluenceAnalyzer

# Setup basic logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_confluence_breakdown():
    """Test that confluence breakdown is properly logged."""
    
    # Mock config
    config = {
        'confluence': {
            'component_weights': {
                'orderflow': 0.25,
                'orderbook': 0.25,
                'volume': 0.16,
                'price_structure': 0.16,
                'technical': 0.11,
                'sentiment': 0.07
            }
        }
    }
    
    # Create analyzer
    analyzer = ConfluenceAnalyzer(config)
    
    # Mock market data
    market_data = {
        'symbol': 'BTCUSDT',
        'exchange': 'test',
        'timestamp': 1234567890,
        'ohlcv': {
            '1': [[1234567890, 50000, 50100, 49900, 50050, 1000]],
            '5': [[1234567890, 50000, 50100, 49900, 50050, 1000]],
            '15': [[1234567890, 50000, 50100, 49900, 50050, 1000]],
            '30': [[1234567890, 50000, 50100, 49900, 50050, 1000]],
            '60': [[1234567890, 50000, 50100, 49900, 50050, 1000]],
            '240': [[1234567890, 50000, 50100, 49900, 50050, 1000]]
        },
        'ticker': {
            'last': 50000,
            'bid': 49999,
            'ask': 50001,
            'volume': 10000
        },
        'orderbook': {
            'bids': [[49999, 10], [49998, 20]],
            'asks': [[50001, 10], [50002, 20]]
        },
        'trades': [],
        'sentiment': {
            'funding_rate': 0.0001,
            'long_short_ratio': 1.2
        }
    }
    
    logger.info("Starting confluence analysis test...")
    
    try:
        result = await analyzer.analyze(market_data)
        logger.info(f"Analysis complete. Score: {result.get('confluence_score', 'N/A')}")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_confluence_breakdown())