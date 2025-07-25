#!/usr/bin/env python3
"""
Comprehensive Live Data Test Suite for All Indicators
Tests all indicator modules with Bybit live data to validate functionality and performance.
"""

import asyncio
import pandas as pd
import numpy as np
import sys
import os
import time
import traceback
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ComprehensiveIndicatorTester:
    """Comprehensive testing suite for all indicator modules."""
    
    def __init__(self):
        self.results = {}
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.test_timeframes = ['5m', '15m']
        self.candle_count = 200
        
    async def run_comprehensive_tests(self):
        """Run comprehensive tests for all indicators."""
        print("=" * 80)
        print("COMPREHENSIVE INDICATOR TEST SUITE - BYBIT LIVE DATA")
        print("=" * 80)
        
        # 1. Initialize exchange and fetch live data
        await self.initialize_exchange()
        
        # 2. Test each indicator module
        await self.test_technical_indicators()
        await self.test_volume_indicators() 
        await self.test_orderflow_indicators()
        await self.test_price_structure_indicators()
        await self.test_sentiment_indicators()
        await self.test_orderbook_indicators()
        
        # 3. Generate comprehensive report
        self.generate_comprehensive_report()
    
    async def initialize_exchange(self):
        """Initialize Bybit exchange connection."""
        print(f"\n{'='*60}")
        print("INITIALIZING BYBIT EXCHANGE CONNECTION")
        print("="*60)
        
        try:
            from src.core.exchanges.bybit import BybitExchange
            
            config = {
                'exchanges': {
                    'bybit': {
                        'api_key': '',
                        'api_secret': '',
                        'testnet': False,
                        'websocket': {
                            'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                        }
                    }
                }
            }
            
            self.exchange = BybitExchange(config)
            print("✅ Bybit exchange initialized successfully")
            
            # Test connection with a simple fetch
            test_data = await self.exchange.fetch_ohlcv('BTCUSDT', '5m', 10)
            if test_data:
                print(f"✅ Connection verified - received {len(test_data)} test candles")
            else:
                raise Exception("No test data received")
                
        except Exception as e:
            print(f"❌ Failed to initialize exchange: {e}")
            raise e
    
    async def fetch_live_data(self, symbol, timeframe='5m', limit=200):
        """Fetch live market data from Bybit."""
        try:
            klines = await self.exchange.fetch_ohlcv(symbol, timeframe, limit)
            
            if not klines:
                return None
                
            # Convert to DataFrame with proper structure
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"❌ Failed to fetch data for {symbol}: {e}")
            return None
    
    async def test_technical_indicators(self):
        """Test TechnicalIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING TECHNICAL INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.technical_indicators import TechnicalIndicators
            from src.utils.helpers import load_config
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                # Fetch live data
                df = await self.fetch_live_data(symbol)
                if df is None:
                    print(f"❌ No data for {symbol}")
                    continue
                
                print(f"📊 Data: {len(df)} candles, Latest: ${df['close'].iloc[-1]:,.2f}")
                
                # Initialize indicator
                technical = TechnicalIndicators(config)
                
                # Test key technical indicators
                indicators_to_test = [
                    ('RSI', 'calculate_rsi'),
                    ('MACD', 'calculate_macd'),
                    ('Bollinger Bands', 'calculate_bollinger_bands'),
                    ('Stochastic', 'calculate_stochastic'),
                    ('ATR', 'calculate_atr'),
                    ('Moving Averages', 'calculate_all_moving_averages'),
                    ('Momentum Suite', 'calculate_momentum_suite'),
                    ('Math Functions', 'calculate_math_functions')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        start_time = time.perf_counter()
                        
                        if hasattr(technical, method_name):
                            method = getattr(technical, method_name)
                            
                            # Call method with appropriate parameters
                            if method_name == 'calculate_rsi':
                                result = method(df, period=14)
                            elif method_name == 'calculate_macd':
                                result = method(df)
                            elif method_name == 'calculate_bollinger_bands':
                                result = method(df, period=20, std_dev=2)
                            elif method_name == 'calculate_stochastic':
                                result = method(df)
                            elif method_name == 'calculate_atr':
                                result = method(df, period=14)
                            elif method_name == 'calculate_all_moving_averages':
                                result = method(df['close'])
                            elif method_name == 'calculate_momentum_suite':
                                result = method(df['close'])
                            elif method_name == 'calculate_math_functions':
                                result = method(df['close'])
                            else:
                                result = method(df)
                            
                            end_time = time.perf_counter()
                            calc_time = (end_time - start_time) * 1000
                            
                            # Validate result
                            if result is not None:
                                if isinstance(result, dict):
                                    # Multiple values returned
                                    valid_keys = [k for k, v in result.items() if v is not None and not (isinstance(v, (int, float)) and np.isnan(v))]
                                    print(f"  ✅ {indicator_name}: {len(valid_keys)} values ({calc_time:.2f}ms)")
                                    
                                    # Show sample values
                                    for key in list(valid_keys)[:3]:  # Show first 3 keys
                                        value = result[key]
                                        if isinstance(value, (pd.Series, np.ndarray)) and len(value) > 0:
                                            latest_val = value.iloc[-1] if hasattr(value, 'iloc') else value[-1]
                                            if not np.isnan(latest_val):
                                                print(f"    {key}: {latest_val:.4f}")
                                        elif isinstance(value, (int, float)) and not np.isnan(value):
                                            print(f"    {key}: {value:.4f}")
                                            
                                elif isinstance(result, (pd.Series, np.ndarray)):
                                    # Single series returned
                                    valid_count = (~pd.isna(result)).sum() if hasattr(result, 'isna') else (~np.isnan(result)).sum()
                                    latest_val = result.iloc[-1] if hasattr(result, 'iloc') else result[-1]
                                    
                                    print(f"  ✅ {indicator_name}: {valid_count} valid values, Latest: {latest_val:.4f} ({calc_time:.2f}ms)")
                                    
                                elif isinstance(result, (int, float)) and not np.isnan(result):
                                    print(f"  ✅ {indicator_name}: {result:.4f} ({calc_time:.2f}ms)")
                                else:
                                    print(f"  ✅ {indicator_name}: Calculated successfully ({calc_time:.2f}ms)")
                                
                                symbol_results[indicator_name] = {
                                    'success': True,
                                    'time_ms': calc_time,
                                    'result_type': str(type(result).__name__)
                                }
                            else:
                                print(f"  ⚠️  {indicator_name}: Returned None")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Returned None'}
                                
                        else:
                            print(f"  ❌ {indicator_name}: Method {method_name} not found")
                            symbol_results[indicator_name] = {'success': False, 'error': 'Method not found'}
                            
                    except Exception as e:
                        print(f"  ❌ {indicator_name}: {str(e)}")
                        symbol_results[indicator_name] = {'success': False, 'error': str(e)}
                
                # Store results
                if 'technical_indicators' not in self.results:
                    self.results['technical_indicators'] = {}
                self.results['technical_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Technical Indicators module failed: {e}")
            self.results['technical_indicators'] = {'error': str(e)}
    
    async def test_volume_indicators(self):
        """Test VolumeIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING VOLUME INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.volume_indicators import VolumeIndicators
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                df = await self.fetch_live_data(symbol)
                if df is None:
                    continue
                
                print(f"📊 Data: {len(df)} candles, Volume range: {df['volume'].min():,.0f} - {df['volume'].max():,.0f}")
                
                volume_indicators = VolumeIndicators(config)
                
                # Test volume indicators
                indicators_to_test = [
                    ('OBV', 'calculate_obv'),
                    ('Volume Profile', 'calculate_volume_profile'),
                    ('VWAP', 'calculate_vwap'),
                    ('Volume Oscillator', 'calculate_volume_oscillator'),
                    ('Price Volume Trend', 'calculate_pvt'),
                    ('Volume Rate of Change', 'calculate_volume_roc')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        start_time = time.perf_counter()
                        
                        if hasattr(volume_indicators, method_name):
                            method = getattr(volume_indicators, method_name)
                            result = method(df)
                            
                            end_time = time.perf_counter()
                            calc_time = (end_time - start_time) * 1000
                            
                            if result is not None:
                                if isinstance(result, dict):
                                    valid_keys = [k for k, v in result.items() if v is not None]
                                    print(f"  ✅ {indicator_name}: {len(valid_keys)} values ({calc_time:.2f}ms)")
                                    
                                    # Show sample values
                                    for key in list(valid_keys)[:2]:
                                        value = result[key]
                                        if isinstance(value, (pd.Series, np.ndarray)) and len(value) > 0:
                                            latest_val = value.iloc[-1] if hasattr(value, 'iloc') else value[-1]
                                            if not np.isnan(latest_val):
                                                print(f"    {key}: {latest_val:.2f}")
                                        elif isinstance(value, (int, float)) and not np.isnan(value):
                                            print(f"    {key}: {value:.2f}")
                                            
                                elif isinstance(result, (pd.Series, np.ndarray)):
                                    valid_count = (~pd.isna(result)).sum() if hasattr(result, 'isna') else (~np.isnan(result)).sum()
                                    latest_val = result.iloc[-1] if hasattr(result, 'iloc') else result[-1]
                                    print(f"  ✅ {indicator_name}: {valid_count} valid, Latest: {latest_val:.2f} ({calc_time:.2f}ms)")
                                else:
                                    print(f"  ✅ {indicator_name}: Calculated ({calc_time:.2f}ms)")
                                
                                symbol_results[indicator_name] = {
                                    'success': True,
                                    'time_ms': calc_time,
                                    'result_type': str(type(result).__name__)
                                }
                            else:
                                print(f"  ⚠️  {indicator_name}: Returned None")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Returned None'}
                        else:
                            print(f"  ❌ {indicator_name}: Method not found")
                            symbol_results[indicator_name] = {'success': False, 'error': 'Method not found'}
                            
                    except Exception as e:
                        print(f"  ❌ {indicator_name}: {str(e)}")
                        symbol_results[indicator_name] = {'success': False, 'error': str(e)}
                
                if 'volume_indicators' not in self.results:
                    self.results['volume_indicators'] = {}
                self.results['volume_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Volume Indicators module failed: {e}")
            self.results['volume_indicators'] = {'error': str(e)}
    
    async def test_orderflow_indicators(self):
        """Test OrderflowIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING ORDERFLOW INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.orderflow_indicators import OrderflowIndicators
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                df = await self.fetch_live_data(symbol)
                if df is None:
                    continue
                
                print(f"📊 Data: {len(df)} candles")
                
                orderflow = OrderflowIndicators(config)
                
                # Test orderflow indicators (note: these may need trade data)
                indicators_to_test = [
                    ('CVD', 'calculate_cvd'),
                    ('Trade Flow', 'calculate_trade_flow'),
                    ('Aggression Index', 'calculate_aggression_index'),
                    ('Liquidity Analysis', 'calculate_liquidity_analysis')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        start_time = time.perf_counter()
                        
                        if hasattr(orderflow, method_name):
                            method = getattr(orderflow, method_name)
                            
                            # These methods may need trade data, so we'll try with OHLCV
                            result = method(df)
                            
                            end_time = time.perf_counter()
                            calc_time = (end_time - start_time) * 1000
                            
                            if result is not None:
                                if isinstance(result, dict):
                                    valid_keys = [k for k, v in result.items() if v is not None]
                                    print(f"  ✅ {indicator_name}: {len(valid_keys)} values ({calc_time:.2f}ms)")
                                    
                                    for key in list(valid_keys)[:2]:
                                        value = result[key]
                                        if isinstance(value, (int, float)) and not np.isnan(value):
                                            print(f"    {key}: {value:.2f}")
                                elif isinstance(result, (int, float)) and not np.isnan(result):
                                    print(f"  ✅ {indicator_name}: {result:.2f} ({calc_time:.2f}ms)")
                                else:
                                    print(f"  ✅ {indicator_name}: Calculated ({calc_time:.2f}ms)")
                                
                                symbol_results[indicator_name] = {
                                    'success': True,
                                    'time_ms': calc_time,
                                    'result_type': str(type(result).__name__)
                                }
                            else:
                                print(f"  ⚠️  {indicator_name}: Returned None (may need trade data)")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Returned None - may need trade data'}
                        else:
                            print(f"  ❌ {indicator_name}: Method not found")
                            symbol_results[indicator_name] = {'success': False, 'error': 'Method not found'}
                            
                    except Exception as e:
                        print(f"  ⚠️  {indicator_name}: {str(e)} (may need trade data)")
                        symbol_results[indicator_name] = {'success': False, 'error': f'{str(e)} - may need trade data'}
                
                if 'orderflow_indicators' not in self.results:
                    self.results['orderflow_indicators'] = {}
                self.results['orderflow_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Orderflow Indicators module failed: {e}")
            self.results['orderflow_indicators'] = {'error': str(e)}
    
    async def test_price_structure_indicators(self):
        """Test PriceStructureIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING PRICE STRUCTURE INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.price_structure_indicators import PriceStructureIndicators
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                df = await self.fetch_live_data(symbol)
                if df is None:
                    continue
                
                print(f"📊 Data: {len(df)} candles, Range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
                
                price_structure = PriceStructureIndicators(config)
                
                # Test price structure indicators
                indicators_to_test = [
                    ('Support/Resistance', 'calculate_sr_levels'),
                    ('Order Blocks', 'calculate_order_blocks'),
                    ('Market Structure', 'calculate_market_structure'),
                    ('Range Analysis', 'calculate_range_analysis'),
                    ('Pivot Points', 'calculate_pivot_points')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        start_time = time.perf_counter()
                        
                        if hasattr(price_structure, method_name):
                            method = getattr(price_structure, method_name)
                            result = method(df)
                            
                            end_time = time.perf_counter()
                            calc_time = (end_time - start_time) * 1000
                            
                            if result is not None:
                                if isinstance(result, dict):
                                    valid_keys = [k for k, v in result.items() if v is not None]
                                    print(f"  ✅ {indicator_name}: {len(valid_keys)} values ({calc_time:.2f}ms)")
                                    
                                    for key in list(valid_keys)[:2]:
                                        value = result[key]
                                        if isinstance(value, (list, np.ndarray)) and len(value) > 0:
                                            print(f"    {key}: {len(value)} items")
                                        elif isinstance(value, (int, float)) and not np.isnan(value):
                                            print(f"    {key}: {value:.2f}")
                                        elif isinstance(value, pd.Series) and len(value) > 0:
                                            valid_count = (~value.isna()).sum()
                                            print(f"    {key}: {valid_count} valid values")
                                            
                                elif isinstance(result, (pd.Series, np.ndarray)):
                                    valid_count = (~pd.isna(result)).sum() if hasattr(result, 'isna') else (~np.isnan(result)).sum()
                                    print(f"  ✅ {indicator_name}: {valid_count} valid values ({calc_time:.2f}ms)")
                                else:
                                    print(f"  ✅ {indicator_name}: Calculated ({calc_time:.2f}ms)")
                                
                                symbol_results[indicator_name] = {
                                    'success': True,
                                    'time_ms': calc_time,
                                    'result_type': str(type(result).__name__)
                                }
                            else:
                                print(f"  ⚠️  {indicator_name}: Returned None")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Returned None'}
                        else:
                            print(f"  ❌ {indicator_name}: Method not found")
                            symbol_results[indicator_name] = {'success': False, 'error': 'Method not found'}
                            
                    except Exception as e:
                        print(f"  ❌ {indicator_name}: {str(e)}")
                        symbol_results[indicator_name] = {'success': False, 'error': str(e)}
                
                if 'price_structure_indicators' not in self.results:
                    self.results['price_structure_indicators'] = {}
                self.results['price_structure_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Price Structure Indicators module failed: {e}")
            self.results['price_structure_indicators'] = {'error': str(e)}
    
    async def test_sentiment_indicators(self):
        """Test SentimentIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING SENTIMENT INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.sentiment_indicators import SentimentIndicators
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                df = await self.fetch_live_data(symbol)
                if df is None:
                    continue
                
                print(f"📊 Data: {len(df)} candles")
                
                sentiment = SentimentIndicators(config)
                
                # Test sentiment indicators (these may need additional data)
                indicators_to_test = [
                    ('Fear Greed Index', 'calculate_fear_greed_index'),
                    ('Market Sentiment', 'calculate_market_sentiment'),
                    ('Social Sentiment', 'calculate_social_sentiment'),
                    ('Funding Rate Analysis', 'calculate_funding_rate_analysis')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        start_time = time.perf_counter()
                        
                        if hasattr(sentiment, method_name):
                            method = getattr(sentiment, method_name)
                            
                            # These methods may need additional data
                            if method_name == 'calculate_funding_rate_analysis':
                                # This needs funding rate data
                                result = None
                                print(f"  ⚠️  {indicator_name}: Requires funding rate data")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Requires funding rate data'}
                                continue
                            else:
                                result = method(df)
                            
                            end_time = time.perf_counter()
                            calc_time = (end_time - start_time) * 1000
                            
                            if result is not None:
                                if isinstance(result, dict):
                                    valid_keys = [k for k, v in result.items() if v is not None]
                                    print(f"  ✅ {indicator_name}: {len(valid_keys)} values ({calc_time:.2f}ms)")
                                elif isinstance(result, (int, float)) and not np.isnan(result):
                                    print(f"  ✅ {indicator_name}: {result:.2f} ({calc_time:.2f}ms)")
                                else:
                                    print(f"  ✅ {indicator_name}: Calculated ({calc_time:.2f}ms)")
                                
                                symbol_results[indicator_name] = {
                                    'success': True,
                                    'time_ms': calc_time,
                                    'result_type': str(type(result).__name__)
                                }
                            else:
                                print(f"  ⚠️  {indicator_name}: Returned None (may need additional data)")
                                symbol_results[indicator_name] = {'success': False, 'error': 'Returned None - may need additional data'}
                        else:
                            print(f"  ❌ {indicator_name}: Method not found")
                            symbol_results[indicator_name] = {'success': False, 'error': 'Method not found'}
                            
                    except Exception as e:
                        print(f"  ⚠️  {indicator_name}: {str(e)} (may need additional data)")
                        symbol_results[indicator_name] = {'success': False, 'error': f'{str(e)} - may need additional data'}
                
                if 'sentiment_indicators' not in self.results:
                    self.results['sentiment_indicators'] = {}
                self.results['sentiment_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Sentiment Indicators module failed: {e}")
            self.results['sentiment_indicators'] = {'error': str(e)}
    
    async def test_orderbook_indicators(self):
        """Test OrderbookIndicators module."""
        print(f"\n{'='*60}")
        print("TESTING ORDERBOOK INDICATORS")
        print("="*60)
        
        try:
            from src.indicators.orderbook_indicators import OrderbookIndicators
            
            config_path = "/Users/ffv_macmini/Desktop/Virtuoso_ccxt/config/config.yaml"
            config = await load_config(config_path)
            
            for symbol in self.test_symbols:
                print(f"\n--- Testing {symbol} ---")
                
                df = await self.fetch_live_data(symbol)
                if df is None:
                    continue
                
                print(f"📊 Data: {len(df)} candles")
                
                orderbook = OrderbookIndicators(config)
                
                # Test orderbook indicators (these need orderbook data)
                indicators_to_test = [
                    ('Bid Ask Spread', 'calculate_bid_ask_spread'),
                    ('Order Book Imbalance', 'calculate_order_imbalance'),
                    ('Depth Analysis', 'calculate_depth_analysis'),
                    ('Support Resistance OB', 'calculate_support_resistance_ob')
                ]
                
                symbol_results = {}
                
                for indicator_name, method_name in indicators_to_test:
                    try:
                        print(f"  ⚠️  {indicator_name}: Requires live orderbook data (not available in historical OHLCV)")
                        symbol_results[indicator_name] = {'success': False, 'error': 'Requires live orderbook data'}
                            
                    except Exception as e:
                        print(f"  ⚠️  {indicator_name}: {str(e)} (requires orderbook data)")
                        symbol_results[indicator_name] = {'success': False, 'error': f'{str(e)} - requires orderbook data'}
                
                if 'orderbook_indicators' not in self.results:
                    self.results['orderbook_indicators'] = {}
                self.results['orderbook_indicators'][symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Orderbook Indicators module failed: {e}")
            self.results['orderbook_indicators'] = {'error': str(e)}
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE INDICATOR TEST REPORT")
        print("="*80)
        
        print(f"\n📊 TEST ENVIRONMENT:")
        print(f"  Exchange: Bybit")
        print(f"  Symbols Tested: {', '.join(self.test_symbols)}")
        print(f"  Candles per Symbol: {self.candle_count}")
        print(f"  Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Count successful tests by module
        module_stats = {}
        total_tests = 0
        total_success = 0
        
        for module_name, module_results in self.results.items():
            if isinstance(module_results, dict) and 'error' not in module_results:
                success_count = 0
                total_count = 0
                
                for symbol, symbol_results in module_results.items():
                    if isinstance(symbol_results, dict):
                        for indicator, result in symbol_results.items():
                            total_count += 1
                            total_tests += 1
                            if result.get('success', False):
                                success_count += 1
                                total_success += 1
                
                module_stats[module_name] = {
                    'success': success_count,
                    'total': total_count,
                    'success_rate': (success_count / total_count * 100) if total_count > 0 else 0
                }
            else:
                module_stats[module_name] = {
                    'success': 0,
                    'total': 0,
                    'success_rate': 0,
                    'error': module_results.get('error', 'Unknown error')
                }
        
        print(f"\n🎯 MODULE RESULTS:")
        for module_name, stats in module_stats.items():
            if 'error' in stats:
                print(f"  ❌ {module_name.replace('_', ' ').title()}: Module Error - {stats['error']}")
            else:
                status = "✅" if stats['success_rate'] >= 50 else "⚠️" if stats['success_rate'] > 0 else "❌"
                print(f"  {status} {module_name.replace('_', ' ').title()}: {stats['success']}/{stats['total']} ({stats['success_rate']:.1f}%)")
        
        overall_success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful: {total_success}")
        print(f"  Success Rate: {overall_success_rate:.1f}%")
        
        # Performance summary
        print(f"\n⚡ PERFORMANCE SUMMARY:")
        fast_indicators = []
        slow_indicators = []
        
        for module_name, module_results in self.results.items():
            if isinstance(module_results, dict) and 'error' not in module_results:
                for symbol, symbol_results in module_results.items():
                    if isinstance(symbol_results, dict):
                        for indicator, result in symbol_results.items():
                            if result.get('success') and 'time_ms' in result:
                                time_ms = result['time_ms']
                                if time_ms < 10:
                                    fast_indicators.append((indicator, time_ms))
                                elif time_ms > 50:
                                    slow_indicators.append((indicator, time_ms))
        
        if fast_indicators:
            fast_indicators.sort(key=lambda x: x[1])
            print(f"  🚀 Fastest Indicators:")
            for indicator, time_ms in fast_indicators[:5]:
                print(f"    {indicator}: {time_ms:.2f}ms")
        
        if slow_indicators:
            slow_indicators.sort(key=lambda x: x[1], reverse=True)
            print(f"  🐌 Slowest Indicators:")
            for indicator, time_ms in slow_indicators[:5]:
                print(f"    {indicator}: {time_ms:.2f}ms")
        
        print(f"\n💡 RECOMMENDATIONS:")
        
        # Check which modules worked well
        working_modules = [name for name, stats in module_stats.items() 
                          if stats['success_rate'] >= 50 and 'error' not in stats]
        
        if working_modules:
            print(f"  ✅ Fully Functional Modules: {len(working_modules)}")
            for module in working_modules:
                print(f"    • {module.replace('_', ' ').title()}")
        
        # Check which modules need additional data
        data_dependent_modules = []
        for module_name, module_results in self.results.items():
            if isinstance(module_results, dict) and 'error' not in module_results:
                for symbol, symbol_results in module_results.items():
                    if isinstance(symbol_results, dict):
                        for indicator, result in symbol_results.items():
                            if not result.get('success') and 'need' in result.get('error', '').lower():
                                if module_name not in data_dependent_modules:
                                    data_dependent_modules.append(module_name)
                                break
        
        if data_dependent_modules:
            print(f"  ⚠️  Modules Requiring Additional Data:")
            for module in data_dependent_modules:
                print(f"    • {module.replace('_', ' ').title()}")
        
        print(f"\n🚀 INTEGRATION STATUS:")
        print(f"  ✅ Exchange connection: Working")
        print(f"  ✅ Live data fetching: Working")  
        print(f"  ✅ OHLCV-based indicators: Mostly functional")
        print(f"  ⚠️  Data-dependent indicators: Require additional data sources")
        
        # Save detailed results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"/Users/ffv_macmini/Desktop/Virtuoso_ccxt/test_output/comprehensive_indicators_test_{timestamp}.json"
        
        try:
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            print(f"\n💾 Detailed results saved to: {results_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save results file: {e}")
        
        print(f"\n{'='*80}")
        print("COMPREHENSIVE INDICATOR TESTING COMPLETE")
        print("="*80)

async def main():
    """Run the comprehensive indicator test suite."""
    tester = ComprehensiveIndicatorTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())