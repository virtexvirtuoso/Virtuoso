#!/usr/bin/env python3
"""
Test script to verify proper usage of market_data in orderbook indicators.

This script tests all data access patterns and ensures we're leveraging
all available data sources correctly for orderbook analysis.
"""

import sys
import os
import asyncio
import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.indicators.orderbook_indicators import OrderbookIndicators
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class OrderbookMarketDataUsageTest:
    """Test class for verifying orderbook indicators market data usage."""
    
    def __init__(self):
        """Initialize the test."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager._config
        
        # Initialize orderbook indicators
        self.orderbook = OrderbookIndicators(self.config, None)
        
    def create_comprehensive_market_data(self) -> Dict[str, Any]:
        """Create comprehensive market data with all possible sources."""
        
        # Generate realistic orderbook data
        base_price = 109000.0
        spread = 0.5  # $0.50 spread
        
        # Create bid levels (below mid price)
        bids = []
        for i in range(25):
            price = base_price - spread/2 - (i * 0.1)
            size = np.random.uniform(0.1, 5.0) * (1.0 - i * 0.05)  # Decreasing size with depth
            bids.append([price, size])
        
        # Create ask levels (above mid price)
        asks = []
        for i in range(25):
            price = base_price + spread/2 + (i * 0.1)
            size = np.random.uniform(0.1, 5.0) * (1.0 - i * 0.05)  # Decreasing size with depth
            asks.append([price, size])
        
        # Generate trade data for context
        trades = []
        current_time = int(time.time() * 1000)
        for i in range(100):
            trade_time = current_time - (i * 1000)  # 1 second intervals
            price = base_price + np.random.uniform(-2.0, 2.0)
            size = np.random.uniform(0.01, 1.0)
            side = np.random.choice(['buy', 'sell'])
            
            trades.append({
                'id': f'trade_{i}',
                'price': price,
                'size': size,
                'amount': size,
                'side': side,
                'time': trade_time,
                'timestamp': trade_time
            })
        
        # Generate OHLCV data for context
        ohlcv_data = []
        start_time = datetime.now(timezone.utc) - timedelta(hours=2)
        for i in range(100):
            timestamp = start_time + timedelta(minutes=i)
            open_price = base_price + np.random.uniform(-5, 5)
            high_price = open_price + np.random.uniform(0, 3)
            low_price = open_price - np.random.uniform(0, 3)
            close_price = open_price + np.random.uniform(-2, 2)
            volume = np.random.uniform(50, 500)
            
            ohlcv_data.append([
                timestamp.timestamp() * 1000,
                open_price, high_price, low_price, close_price, volume
            ])
        
        # Create DataFrame
        ohlcv_df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'], unit='ms')
        ohlcv_df.set_index('timestamp', inplace=True)
        
        return {
            'symbol': 'BTCUSDT',
            'exchange': 'bybit',
            'timestamp': current_time,
            
            # Primary orderbook data
            'orderbook': {
                'bids': bids,
                'asks': asks,
                'timestamp': current_time,
                'datetime': datetime.now(timezone.utc).isoformat(),
                'nonce': current_time
            },
            
            # Trade data for context
            'trades': trades,
            'processed_trades': trades,
            'trades_df': pd.DataFrame(trades),
            
            # OHLCV data for timeframe analysis
            'ohlcv': {
                'base': ohlcv_df.copy(),
                'ltf': ohlcv_df.copy(),
                'mtf': ohlcv_df.copy(),
                'htf': ohlcv_df.copy(),
                '1': ohlcv_df.copy(),
                '5': ohlcv_df.copy(),
                '30': ohlcv_df.copy(),
                '240': ohlcv_df.copy()
            },
            
            # Ticker data
            'ticker': {
                'symbol': 'BTCUSDT',
                'last': base_price,
                'bid': bids[0][0],
                'ask': asks[0][0],
                'percentage': 0.05,
                'open': base_price - 10,
                'high': base_price + 15,
                'low': base_price - 20,
                'close': base_price,
                'baseVolume': 1500.0,
                'quoteVolume': 163500000.0,
                'openInterest': 125000000.0,
                'timestamp': current_time,
                'datetime': datetime.now(timezone.utc).isoformat()
            },
            
            # Sentiment data
            'sentiment': {
                'long_short_ratio': 1.2,
                'funding_rate': 0.0001,
                'liquidations': [
                    {'side': 'long', 'size': 1000000, 'price': base_price - 50},
                    {'side': 'short', 'size': 500000, 'price': base_price + 30}
                ],
                'open_interest': {
                    'current': 125500000.0,
                    'previous': 124800000.0,
                    'timestamp': current_time
                }
            },
            
            # Open interest data (multiple sources)
            'open_interest': {
                'current': 125500000.0,
                'previous': 124800000.0,
                'timestamp': current_time
            },
            
            # Price data for analysis
            'price_data': {
                'current': base_price,
                'previous': base_price - 1.0,
                'change_24h': 0.05,
                'volume_24h': 163500000.0
            }
        }
    
    def test_data_access_patterns(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test all data access patterns used by orderbook indicators."""
        
        results = {
            'ORDERBOOK_ACCESS': {},
            'TRADES_ACCESS': {},
            'TICKER_ACCESS': {},
            'OHLCV_ACCESS': {},
            'SENTIMENT_ACCESS': {}
        }
        
        # Test orderbook access
        orderbook = market_data.get('orderbook', {})
        results['ORDERBOOK_ACCESS'] = {
            'available': bool(orderbook),
            'has_bids': bool(orderbook.get('bids', [])),
            'has_asks': bool(orderbook.get('asks', [])),
            'bid_levels': len(orderbook.get('bids', [])),
            'ask_levels': len(orderbook.get('asks', [])),
            'has_timestamp': 'timestamp' in orderbook,
            'best_bid': orderbook.get('bids', [[0]])[0][0] if orderbook.get('bids') else None,
            'best_ask': orderbook.get('asks', [[0]])[0][0] if orderbook.get('asks') else None,
            'spread': (orderbook.get('asks', [[0]])[0][0] - orderbook.get('bids', [[0]])[0][0]) if orderbook.get('bids') and orderbook.get('asks') else None
        }
        
        # Test trades access
        trades = market_data.get('trades', [])
        processed_trades = market_data.get('processed_trades', [])
        trades_df = market_data.get('trades_df')
        
        results['TRADES_ACCESS'] = {
            'direct_list': {
                'available': bool(trades),
                'count': len(trades),
                'sample': trades[0] if trades else None
            },
            'processed_list': {
                'available': bool(processed_trades),
                'count': len(processed_trades),
                'sample': processed_trades[0] if processed_trades else None
            },
            'dataframe': {
                'available': trades_df is not None,
                'shape': trades_df.shape if trades_df is not None else None,
                'columns': list(trades_df.columns) if trades_df is not None else None
            }
        }
        
        # Test ticker access
        ticker = market_data.get('ticker', {})
        results['TICKER_ACCESS'] = {
            'available': bool(ticker),
            'has_bid': 'bid' in ticker,
            'has_ask': 'ask' in ticker,
            'has_last': 'last' in ticker,
            'has_volume': 'baseVolume' in ticker,
            'has_percentage': 'percentage' in ticker,
            'bid_price': ticker.get('bid'),
            'ask_price': ticker.get('ask'),
            'last_price': ticker.get('last'),
            'spread_from_ticker': (ticker.get('ask', 0) - ticker.get('bid', 0)) if ticker.get('ask') and ticker.get('bid') else None
        }
        
        # Test OHLCV access
        ohlcv = market_data.get('ohlcv', {})
        results['OHLCV_ACCESS'] = {}
        
        for timeframe in ['base', 'ltf', 'mtf', 'htf', '1', '5', '30', '240']:
            tf_data = ohlcv.get(timeframe)
            if tf_data is not None:
                results['OHLCV_ACCESS'][timeframe] = {
                    'type': type(tf_data).__name__,
                    'shape': tf_data.shape if hasattr(tf_data, 'shape') else None,
                    'columns': list(tf_data.columns) if hasattr(tf_data, 'columns') else None,
                    'last_close': tf_data['close'].iloc[-1] if hasattr(tf_data, 'columns') and 'close' in tf_data.columns else None
                }
            else:
                results['OHLCV_ACCESS'][timeframe] = {'available': False}
        
        # Test sentiment access
        sentiment = market_data.get('sentiment', {})
        results['SENTIMENT_ACCESS'] = {
            'available': bool(sentiment),
            'has_long_short_ratio': 'long_short_ratio' in sentiment,
            'has_funding_rate': 'funding_rate' in sentiment,
            'has_liquidations': 'liquidations' in sentiment,
            'has_open_interest': 'open_interest' in sentiment,
            'long_short_ratio': sentiment.get('long_short_ratio'),
            'funding_rate': sentiment.get('funding_rate')
        }
        
        return results
    
    async def test_component_calculations(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test individual component calculations."""
        
        results = {}
        
        # Test each component individually
        components_to_test = [
            ('IMBALANCE', '_calculate_orderbook_imbalance'),
            ('LIQUIDITY', '_calculate_liquidity_score'),
            ('DEPTH', '_calculate_depth_score'),
            ('PRICE_IMPACT', '_calculate_price_impact_score'),
            ('SR_FROM_ORDERBOOK', '_calculate_sr_from_orderbook')
        ]
        
        for component_name, method_name in components_to_test:
            try:
                if hasattr(self.orderbook, method_name):
                    method = getattr(self.orderbook, method_name)
                    score = method(market_data)
                    results[component_name] = {
                        'status': '✓ SUCCESS',
                        'score': score
                    }
                else:
                    results[component_name] = {
                        'status': '✗ METHOD NOT FOUND',
                        'score': None
                    }
            except Exception as e:
                results[component_name] = {
                    'status': f'✗ ERROR: {str(e)}',
                    'score': None
                }
        
        # Test orderbook-specific calculations that require numpy arrays
        try:
            orderbook = market_data.get('orderbook', {})
            bids = np.array(orderbook.get('bids', []))
            asks = np.array(orderbook.get('asks', []))
            
            if len(bids) > 0 and len(asks) > 0:
                # Test spread calculation
                spread_result = self.orderbook.calculate_spread_score(bids, asks)
                results['SPREAD'] = {
                    'status': '✓ SUCCESS',
                    'score': spread_result.get('score', 0)
                }
                
                # Test absorption/exhaustion
                absorption_result = self.orderbook.calculate_absorption_exhaustion(bids, asks)
                results['ABSORPTION_EXHAUSTION'] = {
                    'status': '✓ SUCCESS',
                    'score': absorption_result.get('combined_score', 0)
                }
                
                # Test pressure calculation
                pressure_result = self.orderbook.calculate_pressure(orderbook)
                results['PRESSURE'] = {
                    'status': '✓ SUCCESS',
                    'score': pressure_result.get('score', 0)
                }
                
                # Test DOM momentum
                dom_result = self.orderbook.calculate_dom_momentum(bids, asks)
                results['DOM_MOMENTUM'] = {
                    'status': '✓ SUCCESS',
                    'score': dom_result.get('score', 0)
                }
                
                # Test OBPS
                obps_result = self.orderbook.calculate_obps(bids, asks)
                results['OBPS'] = {
                    'status': '✓ SUCCESS',
                    'score': obps_result.get('score', 0)
                }
            else:
                for component in ['SPREAD', 'ABSORPTION_EXHAUSTION', 'PRESSURE', 'DOM_MOMENTUM', 'OBPS']:
                    results[component] = {
                        'status': '✗ EMPTY ORDERBOOK',
                        'score': None
                    }
                    
        except Exception as e:
            for component in ['SPREAD', 'ABSORPTION_EXHAUSTION', 'PRESSURE', 'DOM_MOMENTUM', 'OBPS']:
                results[component] = {
                    'status': f'✗ ERROR: {str(e)}',
                    'score': None
                }
        
        return results
    
    async def test_full_calculation(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test the full orderbook calculation."""
        
        try:
            result = await self.orderbook.calculate(market_data)
            
            return {
                'status': '✓ FULL CALCULATION SUCCESS',
                'score': result.get('score'),
                'components': result.get('components', {}),
                'signals': result.get('signals', {}),
                'interpretation': result.get('interpretation', 'N/A'),
                'metadata': result.get('metadata', {})
            }
        except Exception as e:
            return {
                'status': f'✗ FULL CALCULATION ERROR: {str(e)}',
                'score': None,
                'components': {},
                'signals': {},
                'interpretation': 'N/A',
                'metadata': {}
            }
    
    def print_results(self, data_access_results: Dict[str, Any], 
                     component_results: Dict[str, Any], 
                     full_calc_results: Dict[str, Any]):
        """Print comprehensive test results."""
        
        print("\n" + "="*80)
        print("DATA ACCESS PATTERNS TEST RESULTS")
        print("="*80)
        
        # Orderbook access results
        print("\nORDERBOOK_ACCESS:")
        ob_access = data_access_results['ORDERBOOK_ACCESS']
        for key, value in ob_access.items():
            print(f"  {key}: {value}")
        
        # Trades access results
        print("\nTRADES_ACCESS:")
        trades_access = data_access_results['TRADES_ACCESS']
        for access_type, data in trades_access.items():
            print(f"  {access_type}: {data}")
        
        # Ticker access results
        print("\nTICKER_ACCESS:")
        ticker_access = data_access_results['TICKER_ACCESS']
        for key, value in ticker_access.items():
            print(f"  {key}: {value}")
        
        # OHLCV access results
        print("\nOHLCV_ACCESS:")
        ohlcv_access = data_access_results['OHLCV_ACCESS']
        for timeframe, data in ohlcv_access.items():
            print(f"  {timeframe}: {data}")
        
        # Sentiment access results
        print("\nSENTIMENT_ACCESS:")
        sentiment_access = data_access_results['SENTIMENT_ACCESS']
        for key, value in sentiment_access.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*80)
        print("COMPONENT CALCULATIONS TEST RESULTS")
        print("="*80)
        
        success_count = 0
        total_count = len(component_results)
        
        for component, result in component_results.items():
            status = result['status']
            score = result['score']
            print(f"{component}: {status}")
            if score is not None:
                print(f"  Score: {score}")
                if '✓ SUCCESS' in status:
                    success_count += 1
        
        print("\n" + "="*80)
        print("FULL CALCULATION TEST RESULTS")
        print("="*80)
        
        full_status = full_calc_results['status']
        print(f"{full_status}")
        if full_calc_results['score'] is not None:
            print(f"Final Score: {full_calc_results['score']}")
            print(f"Components: {full_calc_results['components']}")
            print(f"Signals: {full_calc_results['signals']}")
            print(f"Interpretation: {full_calc_results['interpretation']}")
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Component Success Rate: {success_count}/{total_count}")
        print(f"Full Calculation: {'SUCCESS' if '✓' in full_status else 'FAILED'}")
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        if success_count == total_count and '✓' in full_status:
            print("✓ All components successfully accessing market data")
            print("✓ Full calculation working properly")
        else:
            print("⚠ Some components may need attention:")
            for component, result in component_results.items():
                if '✗' in result['status']:
                    print(f"  - {component}: {result['status']}")

async def main():
    """Main test execution."""
    print("Starting Orderbook Indicators Market Data Usage Test...")
    
    # Initialize test
    test = OrderbookMarketDataUsageTest()
    
    # Create comprehensive market data
    market_data = test.create_comprehensive_market_data()
    
    # Test data access patterns
    data_access_results = test.test_data_access_patterns(market_data)
    
    # Test component calculations
    component_results = await test.test_component_calculations(market_data)
    
    # Test full calculation
    full_calc_results = await test.test_full_calculation(market_data)
    
    # Print results
    test.print_results(data_access_results, component_results, full_calc_results)

if __name__ == "__main__":
    asyncio.run(main()) 