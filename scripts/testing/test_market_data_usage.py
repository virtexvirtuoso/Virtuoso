#!/usr/bin/env python3
"""
Test script to verify proper usage of market_data in orderflow indicators.

This script tests all data access patterns and ensures we're leveraging
all available data sources correctly.
"""

import sys
import os
import asyncio
import logging
import time
import pandas as pd
from typing import Dict, Any

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketDataUsageTest:
    """Test proper usage of market_data in orderflow indicators."""
    
    def __init__(self):
        """Initialize the test."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager._config
        
        # Initialize orderflow indicators
        self.orderflow = OrderflowIndicators(self.config, None)
        
    def create_comprehensive_market_data(self) -> Dict[str, Any]:
        """Create comprehensive market data with all possible data sources."""
        
        # Generate realistic trade data
        trades = []
        base_price = 109000.0
        for i in range(150):
            price = base_price + (i * 0.5) + ((-1)**i * 2.0)  # Slight upward trend with noise
            size = 0.1 + (i % 10) * 0.05  # Varying sizes
            side = 'buy' if i % 3 != 0 else 'sell'  # More buys than sells
            
            trades.append({
                'id': f'trade_{i}',
                'price': price,
                'size': size,
                'amount': size,  # Alternative column name
                'side': side,
                'time': int(time.time() * 1000) - (150 - i) * 1000,
                'timestamp': int(time.time() * 1000) - (150 - i) * 1000
            })
        
        # Generate OHLCV data for multiple timeframes
        ohlcv_data = {}
        timeframes = ['base', 'ltf', 'mtf', 'htf', '1', '5', '30', '240']
        
        for tf in timeframes:
            candles = []
            for i in range(100):
                timestamp = int(time.time() * 1000) - (100 - i) * 60000  # 1 minute intervals
                open_price = base_price + i * 0.1
                close_price = open_price + ((-1)**i * 0.5)
                high_price = max(open_price, close_price) + 0.2
                low_price = min(open_price, close_price) - 0.2
                volume = 100 + i * 2
                
                candles.append({
                    'timestamp': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            # Create DataFrame
            df = pd.DataFrame(candles)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            ohlcv_data[tf] = df
        
        # Create orderbook data
        orderbook = {
            'bids': [[108990.0, 1.5], [108985.0, 2.0], [108980.0, 1.8]],
            'asks': [[109010.0, 1.2], [109015.0, 1.8], [109020.0, 2.2]],
            'timestamp': int(time.time() * 1000)
        }
        
        # Create ticker data
        ticker = {
            'symbol': 'BTCUSDT',
            'last': 109005.0,
            'bid': 108995.0,
            'ask': 109010.0,
            'high': 109100.0,
            'low': 108900.0,
            'volume': 15000.0,
            'open': 108950.0,
            'close': 109005.0,
            'percentage': 0.05,  # 0.05% change
            'change': 55.0,
            'openInterest': 125000000.0,  # Open interest in ticker
            'timestamp': int(time.time() * 1000)
        }
        
        # Create sentiment data with multiple sources
        sentiment = {
            'long_short_ratio': {
                'symbol': 'BTCUSDT',
                'long': 0.65,
                'short': 0.35,
                'timestamp': int(time.time() * 1000)
            },
            'funding_rate': {
                'rate': 0.0001,
                'next_funding_time': int(time.time() * 1000) + 8 * 3600 * 1000
            },
            'liquidations': [
                {'side': 'long', 'size': 1.5, 'price': 108900.0},
                {'side': 'short', 'size': 0.8, 'price': 109100.0}
            ],
            'open_interest': {
                'current': 125500000.0,
                'previous': 124800000.0,
                'timestamp': int(time.time() * 1000)
            }
        }
        
        # Create comprehensive market data structure
        market_data = {
            'symbol': 'BTCUSDT',
            'exchange': 'bybit',
            'timestamp': int(time.time() * 1000),
            
            # Core data sources
            'trades': trades,
            'processed_trades': trades,  # Alternative source
            'ohlcv': ohlcv_data,
            'orderbook': orderbook,
            'ticker': ticker,
            'sentiment': sentiment,
            
            # Additional data sources
            'open_interest': {
                'current': 125500000.0,
                'previous': 124800000.0,
                'timestamp': int(time.time() * 1000)
            },
            
            # Alternative data structures for testing
            'trades_df': pd.DataFrame(trades),
            'price_data': {
                'last': 109005.0,
                'change_24h': 0.05,
                'volume': 15000.0,
                'high': 109100.0,
                'low': 108900.0
            }
        }
        
        return market_data
    
    def test_data_access_patterns(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test all data access patterns used in orderflow indicators."""
        
        results = {
            'trades_access': {},
            'ohlcv_access': {},
            'ticker_access': {},
            'sentiment_access': {},
            'open_interest_access': {},
            'orderbook_access': {}
        }
        
        logger.info("Testing data access patterns...")
        
        # Test trades data access
        logger.info("1. Testing trades data access patterns...")
        
        # Pattern 1: Direct trades list
        if 'trades' in market_data and isinstance(market_data['trades'], list):
            results['trades_access']['direct_list'] = {
                'available': True,
                'count': len(market_data['trades']),
                'sample': market_data['trades'][0] if market_data['trades'] else None
            }
        
        # Pattern 2: Processed trades
        if 'processed_trades' in market_data and isinstance(market_data['processed_trades'], list):
            results['trades_access']['processed_list'] = {
                'available': True,
                'count': len(market_data['processed_trades']),
                'sample': market_data['processed_trades'][0] if market_data['processed_trades'] else None
            }
        
        # Pattern 3: Trades DataFrame
        if 'trades_df' in market_data and isinstance(market_data['trades_df'], pd.DataFrame):
            results['trades_access']['dataframe'] = {
                'available': True,
                'shape': market_data['trades_df'].shape,
                'columns': list(market_data['trades_df'].columns)
            }
        
        # Test OHLCV data access
        logger.info("2. Testing OHLCV data access patterns...")
        
        if 'ohlcv' in market_data and isinstance(market_data['ohlcv'], dict):
            for tf, data in market_data['ohlcv'].items():
                if isinstance(data, pd.DataFrame) and not data.empty:
                    results['ohlcv_access'][tf] = {
                        'type': 'DataFrame',
                        'shape': data.shape,
                        'columns': list(data.columns),
                        'last_close': data['close'].iloc[-1] if 'close' in data.columns else None
                    }
                elif isinstance(data, dict) and 'data' in data:
                    results['ohlcv_access'][tf] = {
                        'type': 'dict_with_data',
                        'has_data': True,
                        'data_type': type(data['data']).__name__
                    }
        
        # Test ticker data access
        logger.info("3. Testing ticker data access patterns...")
        
        if 'ticker' in market_data and isinstance(market_data['ticker'], dict):
            ticker = market_data['ticker']
            results['ticker_access'] = {
                'available': True,
                'has_last': 'last' in ticker,
                'has_percentage': 'percentage' in ticker,
                'has_open': 'open' in ticker,
                'has_open_interest': 'openInterest' in ticker,
                'last_price': ticker.get('last'),
                'percentage_change': ticker.get('percentage')
            }
        
        # Test sentiment data access
        logger.info("4. Testing sentiment data access patterns...")
        
        if 'sentiment' in market_data and isinstance(market_data['sentiment'], dict):
            sentiment = market_data['sentiment']
            results['sentiment_access'] = {
                'available': True,
                'has_long_short_ratio': 'long_short_ratio' in sentiment,
                'has_funding_rate': 'funding_rate' in sentiment,
                'has_liquidations': 'liquidations' in sentiment,
                'has_open_interest': 'open_interest' in sentiment
            }
        
        # Test open interest access patterns
        logger.info("5. Testing open interest access patterns...")
        
        # Pattern 1: Top-level open_interest
        if 'open_interest' in market_data:
            results['open_interest_access']['top_level'] = {
                'available': True,
                'type': type(market_data['open_interest']).__name__,
                'data': market_data['open_interest']
            }
        
        # Pattern 2: Sentiment open_interest
        if 'sentiment' in market_data and 'open_interest' in market_data['sentiment']:
            results['open_interest_access']['sentiment_level'] = {
                'available': True,
                'type': type(market_data['sentiment']['open_interest']).__name__,
                'data': market_data['sentiment']['open_interest']
            }
        
        # Pattern 3: Ticker open_interest
        if 'ticker' in market_data and 'openInterest' in market_data['ticker']:
            results['open_interest_access']['ticker_level'] = {
                'available': True,
                'value': market_data['ticker']['openInterest']
            }
        
        # Test orderbook access
        logger.info("6. Testing orderbook data access...")
        
        if 'orderbook' in market_data and isinstance(market_data['orderbook'], dict):
            orderbook = market_data['orderbook']
            results['orderbook_access'] = {
                'available': True,
                'has_bids': 'bids' in orderbook and len(orderbook['bids']) > 0,
                'has_asks': 'asks' in orderbook and len(orderbook['asks']) > 0,
                'bid_levels': len(orderbook.get('bids', [])),
                'ask_levels': len(orderbook.get('asks', []))
            }
        
        return results
    
    def test_component_calculations(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test that all components can access their required data."""
        
        logger.info("Testing component calculations with comprehensive market data...")
        
        results = {}
        
        try:
            # Test CVD calculation
            logger.info("Testing CVD calculation...")
            cvd_score = self.orderflow._calculate_cvd(market_data)
            results['cvd'] = {
                'success': True,
                'score': cvd_score,
                'error': None
            }
        except Exception as e:
            results['cvd'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test open interest calculation
            logger.info("Testing open interest calculation...")
            oi_score = self.orderflow._calculate_open_interest_score(market_data)
            results['open_interest'] = {
                'success': True,
                'score': oi_score,
                'error': None
            }
        except Exception as e:
            results['open_interest'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test trade flow calculation
            logger.info("Testing trade flow calculation...")
            flow_score = self.orderflow._calculate_trade_flow_score(market_data)
            results['trade_flow'] = {
                'success': True,
                'score': flow_score,
                'error': None
            }
        except Exception as e:
            results['trade_flow'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test imbalance calculation
            logger.info("Testing imbalance calculation...")
            imbalance_score = self.orderflow._calculate_trades_imbalance_score(market_data)
            results['imbalance'] = {
                'success': True,
                'score': imbalance_score,
                'error': None
            }
        except Exception as e:
            results['imbalance'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test pressure calculation
            logger.info("Testing pressure calculation...")
            pressure_score = self.orderflow._calculate_trades_pressure_score(market_data)
            results['pressure'] = {
                'success': True,
                'score': pressure_score,
                'error': None
            }
        except Exception as e:
            results['pressure'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test liquidity calculation
            logger.info("Testing liquidity calculation...")
            liquidity_score = self.orderflow._calculate_liquidity_score(market_data)
            results['liquidity'] = {
                'success': True,
                'score': liquidity_score,
                'error': None
            }
        except Exception as e:
            results['liquidity'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        try:
            # Test liquidity zones calculation
            logger.info("Testing liquidity zones calculation...")
            zones_score = self.orderflow._calculate_liquidity_zones_score(market_data)
            results['liquidity_zones'] = {
                'success': True,
                'score': zones_score,
                'error': None
            }
        except Exception as e:
            results['liquidity_zones'] = {
                'success': False,
                'score': None,
                'error': str(e)
            }
        
        return results
    
    def test_full_calculation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test the full orderflow calculation."""
        
        logger.info("Testing full orderflow calculation...")
        
        try:
            result = self.orderflow.calculate(market_data)
            return {
                'success': True,
                'result': result,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def run_comprehensive_test(self):
        """Run comprehensive test of market data usage."""
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE MARKET DATA USAGE TEST")
        logger.info("=" * 80)
        
        # Create comprehensive market data
        market_data = self.create_comprehensive_market_data()
        
        logger.info(f"Created market data with keys: {list(market_data.keys())}")
        logger.info(f"Trades count: {len(market_data.get('trades', []))}")
        logger.info(f"OHLCV timeframes: {list(market_data.get('ohlcv', {}).keys())}")
        
        # Test data access patterns
        access_results = self.test_data_access_patterns(market_data)
        
        # Test component calculations
        component_results = self.test_component_calculations(market_data)
        
        # Test full calculation
        full_result = self.test_full_calculation(market_data)
        
        # Print comprehensive results
        logger.info("\n" + "=" * 80)
        logger.info("DATA ACCESS PATTERNS TEST RESULTS")
        logger.info("=" * 80)
        
        for category, results in access_results.items():
            logger.info(f"\n{category.upper()}:")
            if isinstance(results, dict):
                for key, value in results.items():
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {results}")
        
        logger.info("\n" + "=" * 80)
        logger.info("COMPONENT CALCULATIONS TEST RESULTS")
        logger.info("=" * 80)
        
        for component, result in component_results.items():
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            logger.info(f"{component.upper()}: {status}")
            if result['success']:
                logger.info(f"  Score: {result['score']:.2f}")
            else:
                logger.info(f"  Error: {result['error']}")
        
        logger.info("\n" + "=" * 80)
        logger.info("FULL CALCULATION TEST RESULTS")
        logger.info("=" * 80)
        
        if full_result['success']:
            logger.info("✓ FULL CALCULATION SUCCESS")
            result = full_result['result']
            logger.info(f"Final Score: {result.get('score', 'N/A')}")
            logger.info(f"Signal: {result.get('signal', 'N/A')}")
            logger.info(f"Confidence: {result.get('confidence', 'N/A')}")
            
            if 'component_scores' in result:
                logger.info("\nComponent Scores:")
                for component, score in result['component_scores'].items():
                    logger.info(f"  {component}: {score:.2f}")
        else:
            logger.info("✗ FULL CALCULATION FAILED")
            logger.info(f"Error: {full_result['error']}")
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        successful_components = sum(1 for r in component_results.values() if r['success'])
        total_components = len(component_results)
        
        logger.info(f"Component Success Rate: {successful_components}/{total_components}")
        logger.info(f"Full Calculation: {'SUCCESS' if full_result['success'] else 'FAILED'}")
        
        # Recommendations
        logger.info("\n" + "=" * 80)
        logger.info("RECOMMENDATIONS")
        logger.info("=" * 80)
        
        failed_components = [comp for comp, result in component_results.items() if not result['success']]
        if failed_components:
            logger.info(f"Failed components need attention: {', '.join(failed_components)}")
        else:
            logger.info("✓ All components successfully accessing market data")
        
        if not full_result['success']:
            logger.info("✗ Full calculation needs debugging")
        else:
            logger.info("✓ Full calculation working properly")
        
        return {
            'access_results': access_results,
            'component_results': component_results,
            'full_result': full_result
        }

async def main():
    """Main test function."""
    
    test = MarketDataUsageTest()
    results = test.run_comprehensive_test()
    
    return results

if __name__ == "__main__":
    asyncio.run(main()) 