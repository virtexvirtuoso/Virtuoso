#!/usr/bin/env python3
"""
Test script to verify volume and orderflow validation fixes.

This script tests:
1. Correct timeframe mapping from exchange data to standard labels
2. Trade data availability for orderflow analysis
3. Confluence analysis with properly formatted data
"""

import asyncio
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta
import traceback

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import Logger
from src.config.manager import ConfigManager
from src.analysis.core.confluence import ConfluenceAnalyzer
from src.core.analysis.market_data_wrapper import MarketDataWrapper
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators

async def test_timeframe_mapping():
    """Test timeframe mapping logic."""
    logger = Logger('test_timeframe_mapping')
    
    logger.info("\n" + "="*60)
    logger.info("Testing Timeframe Mapping")
    logger.info("="*60)
    
    # Simulate market data with exchange timeframe labels
    test_data = {
        'ohlcv': {
            '1m': pd.DataFrame({
                'open': np.random.rand(100) * 100,
                'high': np.random.rand(100) * 100,
                'low': np.random.rand(100) * 100,
                'close': np.random.rand(100) * 100,
                'volume': np.random.rand(100) * 1000
            }),
            '15m': pd.DataFrame({
                'open': np.random.rand(50) * 100,
                'high': np.random.rand(50) * 100,
                'low': np.random.rand(50) * 100,
                'close': np.random.rand(50) * 100,
                'volume': np.random.rand(50) * 1000
            }),
            '1h': pd.DataFrame({
                'open': np.random.rand(30) * 100,
                'high': np.random.rand(30) * 100,
                'low': np.random.rand(30) * 100,
                'close': np.random.rand(30) * 100,
                'volume': np.random.rand(30) * 1000
            }),
            '4h': pd.DataFrame({
                'open': np.random.rand(20) * 100,
                'high': np.random.rand(20) * 100,
                'low': np.random.rand(20) * 100,
                'close': np.random.rand(20) * 100,
                'volume': np.random.rand(20) * 1000
            })
        }
    }
    
    logger.info("Input timeframes: " + str(list(test_data['ohlcv'].keys())))
    
    # Test the wrapper
    class MockExchange:
        async def fetch_trades(self, symbol, limit=1000):
            # Simulate trade data
            trades = []
            for i in range(limit):
                trades.append({
                    'id': str(i),
                    'timestamp': int((datetime.now() - timedelta(minutes=i)).timestamp() * 1000),
                    'datetime': (datetime.now() - timedelta(minutes=i)).isoformat(),
                    'symbol': symbol,
                    'type': 'limit',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'price': 100 + np.random.randn(),
                    'amount': 10 + np.random.rand() * 90,
                    'cost': 0,
                    'fee': None
                })
            return trades
    
    exchange = MockExchange()
    
    # Apply wrapper
    wrapped_data = await MarketDataWrapper.ensure_complete_market_data(
        exchange, 'BTC/USDT', test_data.copy()
    )
    
    logger.info("\nAfter wrapper:")
    logger.info("OHLCV timeframes: " + str(list(wrapped_data['ohlcv'].keys())))
    logger.info("Has trades: " + str('trades' in wrapped_data and len(wrapped_data['trades']) > 0))
    
    # Validate the wrapped data
    validation = MarketDataWrapper.validate_market_data(wrapped_data)
    logger.info("\nValidation results:")
    for key, value in validation.items():
        logger.info(f"  {key}: {value}")
    
    return validation['has_base_timeframe'] and validation['has_trades']

def test_volume_indicator_validation():
    """Test volume indicator with fixed data."""
    logger = Logger('test_volume_validation')
    
    logger.info("\n" + "="*60)
    logger.info("Testing Volume Indicator Validation")
    logger.info("="*60)
    
    config = ConfigManager().config
    volume_indicator = VolumeIndicators(config, logger)
    
    # Test with properly formatted data
    test_data = {
        'ohlcv': {
            'base': pd.DataFrame({
                'open': np.random.rand(100) * 100,
                'high': np.random.rand(100) * 100,
                'low': np.random.rand(100) * 100,
                'close': np.random.rand(100) * 100,
                'volume': np.random.rand(100) * 1000
            }),
            'ltf': pd.DataFrame({
                'open': np.random.rand(50) * 100,
                'high': np.random.rand(50) * 100,
                'low': np.random.rand(50) * 100,
                'close': np.random.rand(50) * 100,
                'volume': np.random.rand(50) * 1000
            }),
            'mtf': pd.DataFrame({
                'open': np.random.rand(30) * 100,
                'high': np.random.rand(30) * 100,
                'low': np.random.rand(30) * 100,
                'close': np.random.rand(30) * 100,
                'volume': np.random.rand(30) * 1000
            }),
            'htf': pd.DataFrame({
                'open': np.random.rand(20) * 100,
                'high': np.random.rand(20) * 100,
                'low': np.random.rand(20) * 100,
                'close': np.random.rand(20) * 100,
                'volume': np.random.rand(20) * 1000
            })
        }
    }
    
    # Validate input
    is_valid = volume_indicator.validate_input(test_data)
    logger.info(f"Validation result: {is_valid}")
    
    if is_valid:
        # Try to calculate
        try:
            result = volume_indicator.calculate(test_data, 'TEST/USDT')
            logger.info(f"Volume score: {result['score']}")
            logger.info("✅ Volume indicator working correctly")
            return True
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            return False
    else:
        logger.error("❌ Volume indicator validation failed")
        return False

def test_orderflow_indicator_validation():
    """Test orderflow indicator with fixed data."""
    logger = Logger('test_orderflow_validation')
    
    logger.info("\n" + "="*60)
    logger.info("Testing Orderflow Indicator Validation")
    logger.info("="*60)
    
    config = ConfigManager().config
    orderflow_indicator = OrderflowIndicators(config, logger)
    
    # Test with properly formatted data including trades
    test_data = {
        'ohlcv': {
            'base': pd.DataFrame({
                'open': np.random.rand(100) * 100,
                'high': np.random.rand(100) * 100,
                'low': np.random.rand(100) * 100,
                'close': np.random.rand(100) * 100,
                'volume': np.random.rand(100) * 1000
            })
        },
        'orderbook': {
            'bids': [[99.5, 100], [99.4, 200], [99.3, 300]],
            'asks': [[100.5, 100], [100.6, 200], [100.7, 300]],
            'timestamp': int(datetime.now().timestamp() * 1000)
        },
        'trades': []
    }
    
    # Generate trade data
    for i in range(1000):
        test_data['trades'].append({
            'id': str(i),
            'timestamp': int((datetime.now() - timedelta(minutes=i)).timestamp() * 1000),
            'datetime': (datetime.now() - timedelta(minutes=i)).isoformat(),
            'symbol': 'TEST/USDT',
            'type': 'limit',
            'side': 'buy' if i % 2 == 0 else 'sell',
            'price': 100 + np.random.randn(),
            'amount': 10 + np.random.rand() * 90,
            'cost': 0,
            'fee': None
        })
    
    logger.info(f"Trade data: {len(test_data['trades'])} trades")
    
    # Validate input
    is_valid = orderflow_indicator.validate_input(test_data)
    logger.info(f"Validation result: {is_valid}")
    
    if is_valid:
        # Try to calculate
        try:
            result = orderflow_indicator.calculate(test_data, 'TEST/USDT')
            logger.info(f"Orderflow score: {result['score']}")
            logger.info("✅ Orderflow indicator working correctly")
            return True
        except Exception as e:
            logger.error(f"Calculation failed: {e}")
            logger.error(traceback.format_exc())
            return False
    else:
        logger.error("❌ Orderflow indicator validation failed")
        return False

async def test_confluence_analysis():
    """Test complete confluence analysis with fixed data."""
    logger = Logger('test_confluence')
    
    logger.info("\n" + "="*60)
    logger.info("Testing Confluence Analysis")
    logger.info("="*60)
    
    config = ConfigManager().config
    analyzer = ConfluenceAnalyzer(config, logger)
    
    # Create complete test data
    test_data = {
        'ohlcv': {
            '1m': pd.DataFrame({
                'open': np.random.rand(100) * 100,
                'high': np.random.rand(100) * 100,
                'low': np.random.rand(100) * 100,
                'close': np.random.rand(100) * 100,
                'volume': np.random.rand(100) * 1000
            }),
            '15m': pd.DataFrame({
                'open': np.random.rand(50) * 100,
                'high': np.random.rand(50) * 100,
                'low': np.random.rand(50) * 100,
                'close': np.random.rand(50) * 100,
                'volume': np.random.rand(50) * 1000
            }),
            '1h': pd.DataFrame({
                'open': np.random.rand(30) * 100,
                'high': np.random.rand(30) * 100,
                'low': np.random.rand(30) * 100,
                'close': np.random.rand(30) * 100,
                'volume': np.random.rand(30) * 1000
            }),
            '4h': pd.DataFrame({
                'open': np.random.rand(20) * 100,
                'high': np.random.rand(20) * 100,
                'low': np.random.rand(20) * 100,
                'close': np.random.rand(20) * 100,
                'volume': np.random.rand(20) * 1000
            })
        },
        'orderbook': {
            'bids': [[99.5, 100], [99.4, 200], [99.3, 300]],
            'asks': [[100.5, 100], [100.6, 200], [100.7, 300]],
            'timestamp': int(datetime.now().timestamp() * 1000)
        },
        'trades': [],
        'sentiment': {
            'fear_greed_index': 50,
            'social_sentiment': 0.5
        }
    }
    
    # Mock exchange for trade fetching
    class MockExchange:
        async def fetch_trades(self, symbol, limit=1000):
            trades = []
            for i in range(limit):
                trades.append({
                    'id': str(i),
                    'timestamp': int((datetime.now() - timedelta(minutes=i)).timestamp() * 1000),
                    'datetime': (datetime.now() - timedelta(minutes=i)).isoformat(),
                    'symbol': symbol,
                    'type': 'limit',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'price': 100 + np.random.randn(),
                    'amount': 10 + np.random.rand() * 90,
                    'cost': 0,
                    'fee': None
                })
            return trades
    
    exchange = MockExchange()
    
    # Apply wrapper to ensure complete data
    wrapped_data = await MarketDataWrapper.ensure_complete_market_data(
        exchange, 'TEST/USDT', test_data
    )
    
    logger.info("Data validation:")
    validation = MarketDataWrapper.validate_market_data(wrapped_data)
    for key, value in validation.items():
        logger.info(f"  {key}: {value}")
    
    # Run confluence analysis
    try:
        result = await analyzer.analyze(wrapped_data, 'TEST/USDT')
        
        logger.info(f"\nConfluence score: {result['confluence_score']}")
        logger.info(f"Status: {result['metadata']['status']}")
        
        if result['metadata']['status'] == 'SUCCESS':
            logger.info("\n✅ Confluence analysis completed successfully!")
            logger.info("\nComponent scores:")
            for component, score in result['components'].items():
                logger.info(f"  {component}: {score:.2f}")
            return True
        else:
            logger.error(f"\n❌ Confluence analysis failed: {result['metadata'].get('error', 'Unknown error')}")
            if 'failed_indicators' in result['metadata']:
                logger.error(f"Failed indicators: {result['metadata']['failed_indicators']}")
            return False
            
    except Exception as e:
        logger.error(f"Error in confluence analysis: {e}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all tests."""
    logger = Logger('validation_test')
    
    logger.info("="*60)
    logger.info("Volume and Orderflow Validation Test Suite")
    logger.info("="*60)
    
    results = {
        'timeframe_mapping': False,
        'volume_validation': False,
        'orderflow_validation': False,
        'confluence_analysis': False
    }
    
    try:
        # Test 1: Timeframe mapping
        results['timeframe_mapping'] = await test_timeframe_mapping()
        
        # Test 2: Volume indicator
        results['volume_validation'] = test_volume_indicator_validation()
        
        # Test 3: Orderflow indicator
        results['orderflow_validation'] = test_orderflow_indicator_validation()
        
        # Test 4: Complete confluence analysis
        results['confluence_analysis'] = await test_confluence_analysis()
        
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        logger.error(traceback.format_exc())
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Test Results Summary")
    logger.info("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED - Validation issues are fixed!")
    else:
        logger.error("❌ SOME TESTS FAILED - Further investigation needed")
    logger.info("="*60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))