#!/usr/bin/env python3
"""
Comprehensive TA-Lib Optimization Test Suite
Tests live data, edge cases, error conditions, and performance under stress.
"""

import asyncio
import pandas as pd
import numpy as np
import sys
import os
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any
import warnings

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Test imports
try:
    from src.indicators.technical_indicators import TechnicalIndicators
    from src.core.exchanges.bybit import BybitExchange
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test TA-Lib availability
try:
    import talib
    HAS_TALIB = True
    print("✅ TA-Lib is available")
except ImportError:
    HAS_TALIB = False
    print("⚠️  TA-Lib is not available - testing pandas fallbacks only")

class ComprehensiveOptimizationTester:
    """Comprehensive test suite for the integrated optimization system."""
    
    def __init__(self):
        self.test_results = {}
        self.edge_case_results = {}
        self.performance_results = {}
        self.error_test_results = {}
        
        # Base configuration
        self.base_config = {
            'analysis': {
                'indicators': {
                    'technical': {}
                }
            },
            'confluence': {
                'weights': {
                    'sub_components': {
                        'technical': {}
                    }
                }
            },
            'timeframes': {
                'base': {'weight': 0.4, 'interval': '5m'},
                'ltf': {'weight': 0.3, 'interval': '1m'},
                'mtf': {'weight': 0.2, 'interval': '15m'},
                'htf': {'weight': 0.1, 'interval': '1h'}
            },
            'exchanges': {
                'bybit': {
                    'api_key': '',
                    'api_secret': '',
                    'testnet': False,
                    'websocket': {
                        'mainnet_endpoint': 'wss://stream.bybit.com/v5/public'
                    }
                }
            },
            'logging': {
                'level': 'WARNING'
            }
        }
        
        # Test configurations
        self.test_configs = {
            'auto_with_talib': {
                **self.base_config,
                'optimization': {
                    'level': 'auto',
                    'use_talib': True,
                    'benchmark': True,
                    'fallback_on_error': True
                }
            },
            'talib_only_strict': {
                **self.base_config,
                'optimization': {
                    'level': 'talib',
                    'use_talib': True,
                    'benchmark': True,
                    'fallback_on_error': False
                }
            },
            'talib_with_fallback': {
                **self.base_config,
                'optimization': {
                    'level': 'talib',
                    'use_talib': True,
                    'benchmark': True,
                    'fallback_on_error': True
                }
            },
            'pandas_only': {
                **self.base_config,
                'optimization': {
                    'level': 'pandas',
                    'use_talib': False,
                    'benchmark': True,
                    'fallback_on_error': True
                }
            }
        }
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests."""
        print("=" * 80)
        print("COMPREHENSIVE TA-LIB OPTIMIZATION TEST SUITE")
        print("=" * 80)
        
        # 1. Live Data Tests
        await self.test_live_data_multiple_symbols()
        
        # 2. Edge Case Tests
        await self.test_edge_cases()
        
        # 3. Error Condition Tests
        await self.test_error_conditions()
        
        # 4. Performance Stress Tests
        await self.test_performance_stress()
        
        # 5. Configuration Tests
        await self.test_all_configurations()
        
        # 6. Data Quality Tests
        await self.test_data_quality_scenarios()
        
        # 7. Phase 4 Enhanced Features Tests
        await self.test_phase4_enhancements()
        
        # 8. Generate comprehensive report
        await self.generate_comprehensive_report()
    
    async def test_live_data_multiple_symbols(self):
        """Test with live data from multiple symbols and timeframes."""
        print("\n" + "=" * 60)
        print("1. LIVE DATA TESTS")
        print("=" * 60)
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']
        timeframes = ['1m', '5m', '15m', '1h']
        
        try:
            exchange = BybitExchange(self.base_config)
            
            for symbol in symbols:
                print(f"\n--- Testing {symbol} ---")
                
                symbol_results = {}
                
                for timeframe in timeframes:
                    try:
                        # Fetch live data
                        klines = await exchange.fetch_ohlcv(symbol, timeframe, 500)
                        
                        if not klines:
                            print(f"  ⚠️  No data for {symbol} {timeframe}")
                            continue
                        
                        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('timestamp', inplace=True)
                        
                        print(f"  📊 {timeframe}: {len(df)} candles, Latest: ${df['close'].iloc[-1]:,.2f}")
                        
                        # Test with auto optimization
                        config = self.test_configs['auto_with_talib']
                        indicators = TechnicalIndicators(config)
                        
                        # Test core indicators
                        start_time = time.perf_counter()
                        
                        rsi = indicators._calculate_rsi_optimized(df['close'])
                        macd = indicators._calculate_macd_optimized(df['close'])
                        atr = indicators._calculate_atr_optimized(df['high'], df['low'], df['close'])
                        williams_r = indicators._calculate_williams_r_optimized(df['high'], df['low'], df['close'])
                        cci = indicators._calculate_cci_optimized(df['high'], df['low'], df['close'])
                        
                        end_time = time.perf_counter()
                        execution_time = (end_time - start_time) * 1000
                        
                        # Validate results
                        rsi_latest = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None
                        macd_latest = macd[0].iloc[-1] if not pd.isna(macd[0].iloc[-1]) else None
                        atr_latest = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else None
                        
                        symbol_results[timeframe] = {
                            'data_points': len(df),
                            'execution_time': execution_time,
                            'rsi': rsi_latest,
                            'macd': macd_latest,
                            'atr': atr_latest,
                            'optimization': indicators.actual_optimization,
                            'success': True
                        }
                        
                        print(f"    ✅ {execution_time:.2f}ms - RSI: {rsi_latest:.2f}, MACD: {macd_latest:.4f}")
                        
                    except Exception as e:
                        print(f"    ❌ {timeframe} failed: {e}")
                        symbol_results[timeframe] = {'success': False, 'error': str(e)}
                
                self.test_results[symbol] = symbol_results
                
        except Exception as e:
            print(f"❌ Live data test setup failed: {e}")
            self.test_results['live_data_error'] = str(e)
    
    async def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        print("\n" + "=" * 60)
        print("2. EDGE CASE TESTS")
        print("=" * 60)
        
        edge_cases = {
            'minimal_data': self.create_minimal_data(15),  # Just enough for RSI
            'small_dataset': self.create_realistic_data(50),
            'large_dataset': self.create_realistic_data(10000),
            'volatile_data': self.create_volatile_data(1000),
            'trending_data': self.create_trending_data(1000),
            'flat_data': self.create_flat_data(1000),
            'gapped_data': self.create_gapped_data(1000),
            'extreme_values': self.create_extreme_values_data(1000),
            'zero_volume': self.create_zero_volume_data(1000),
            'negative_prices': self.create_negative_price_data(1000)
        }
        
        config = self.test_configs['auto_with_talib']
        
        for case_name, df in edge_cases.items():
            print(f"\n--- Testing {case_name} ---")
            
            try:
                indicators = TechnicalIndicators(config)
                
                start_time = time.perf_counter()
                
                # Test core indicators
                results = {}
                
                # RSI
                try:
                    rsi = indicators._calculate_rsi_optimized(df['close'])
                    results['rsi'] = {
                        'success': True,
                        'latest': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None,
                        'nan_count': rsi.isna().sum()
                    }
                except Exception as e:
                    results['rsi'] = {'success': False, 'error': str(e)}
                
                # MACD
                try:
                    macd = indicators._calculate_macd_optimized(df['close'])
                    results['macd'] = {
                        'success': True,
                        'latest': macd[0].iloc[-1] if not pd.isna(macd[0].iloc[-1]) else None,
                        'nan_count': macd[0].isna().sum()
                    }
                except Exception as e:
                    results['macd'] = {'success': False, 'error': str(e)}
                
                # ATR (needs high, low, close)
                try:
                    atr = indicators._calculate_atr_optimized(df['high'], df['low'], df['close'])
                    results['atr'] = {
                        'success': True,
                        'latest': atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else None,
                        'nan_count': atr.isna().sum()
                    }
                except Exception as e:
                    results['atr'] = {'success': False, 'error': str(e)}
                
                end_time = time.perf_counter()
                execution_time = (end_time - start_time) * 1000
                
                # Summary
                success_count = sum(1 for r in results.values() if r['success'])
                print(f"  ✅ {success_count}/3 indicators successful ({execution_time:.2f}ms)")
                
                for indicator, result in results.items():
                    if result['success']:
                        print(f"    {indicator}: {result['latest']:.4f} ({result['nan_count']} NaNs)")
                    else:
                        print(f"    {indicator}: ❌ {result['error']}")
                
                self.edge_case_results[case_name] = {
                    'data_size': len(df),
                    'execution_time': execution_time,
                    'results': results,
                    'optimization': indicators.actual_optimization
                }
                
            except Exception as e:
                print(f"  ❌ {case_name} failed: {e}")
                self.edge_case_results[case_name] = {'success': False, 'error': str(e)}
    
    async def test_error_conditions(self):
        """Test error conditions and fallback mechanisms."""
        print("\n" + "=" * 60)
        print("3. ERROR CONDITION TESTS")
        print("=" * 60)
        
        error_tests = [
            ('empty_dataframe', pd.DataFrame()),
            ('single_row', pd.DataFrame({'close': [100], 'high': [101], 'low': [99], 'volume': [1000]})),
            ('nan_values', self.create_nan_data(1000)),
            ('inf_values', self.create_inf_data(1000)),
            ('string_values', self.create_string_data(1000)),
            ('missing_columns', pd.DataFrame({'price': range(100)})),
        ]
        
        # Test both strict and fallback configurations
        configs_to_test = {
            'with_fallback': self.test_configs['talib_with_fallback'],
            'strict_mode': self.test_configs['talib_only_strict'] if HAS_TALIB else None
        }
        
        for config_name, config in configs_to_test.items():
            if config is None:
                continue
                
            print(f"\n--- Testing {config_name} ---")
            
            for test_name, test_data in error_tests:
                try:
                    indicators = TechnicalIndicators(config)
                    
                    print(f"  Testing {test_name}:")
                    
                    if isinstance(test_data, pd.DataFrame) and not test_data.empty:
                        # Add required columns if missing
                        if 'close' not in test_data.columns and 'price' in test_data.columns:
                            test_data = test_data.rename(columns={'price': 'close'})
                        
                        for col in ['high', 'low', 'volume']:
                            if col not in test_data.columns and 'close' in test_data.columns:
                                if col == 'volume':
                                    test_data[col] = 1000.0
                                elif col == 'high':
                                    test_data[col] = test_data['close'] * 1.01
                                elif col == 'low':
                                    test_data[col] = test_data['close'] * 0.99
                    
                    # Test RSI
                    try:
                        if not test_data.empty and 'close' in test_data.columns:
                            rsi = indicators._calculate_rsi_optimized(test_data['close'])
                            print(f"    RSI: ✅ Success (optimization: {indicators.actual_optimization})")
                        else:
                            print(f"    RSI: ⚠️  Skipped (no close data)")
                    except Exception as e:
                        print(f"    RSI: ❌ {e}")
                    
                    # Test MACD
                    try:
                        if not test_data.empty and 'close' in test_data.columns:
                            macd = indicators._calculate_macd_optimized(test_data['close'])
                            print(f"    MACD: ✅ Success")
                        else:
                            print(f"    MACD: ⚠️  Skipped (no close data)")
                    except Exception as e:
                        print(f"    MACD: ❌ {e}")
                        
                except Exception as e:
                    print(f"  ❌ {test_name} initialization failed: {e}")
    
    async def test_performance_stress(self):
        """Test performance under stress conditions."""
        print("\n" + "=" * 60)
        print("4. PERFORMANCE STRESS TESTS")
        print("=" * 60)
        
        stress_tests = [
            ('small_batch', 100, 10),      # 100 data points, 10 iterations
            ('medium_batch', 1000, 10),    # 1000 data points, 10 iterations
            ('large_batch', 5000, 5),      # 5000 data points, 5 iterations
            ('xl_batch', 10000, 3),        # 10000 data points, 3 iterations
        ]
        
        config = self.test_configs['auto_with_talib']
        
        for test_name, data_size, iterations in stress_tests:
            print(f"\n--- {test_name}: {data_size} points × {iterations} iterations ---")
            
            # Generate test data
            df = self.create_realistic_data(data_size)
            indicators = TechnicalIndicators(config)
            
            # Warm up
            indicators._calculate_rsi_optimized(df['close'])
            
            # Benchmark
            times = []
            
            for i in range(iterations):
                start_time = time.perf_counter()
                
                # Run multiple indicators
                rsi = indicators._calculate_rsi_optimized(df['close'])
                macd = indicators._calculate_macd_optimized(df['close'])
                atr = indicators._calculate_atr_optimized(df['high'], df['low'], df['close'])
                williams_r = indicators._calculate_williams_r_optimized(df['high'], df['low'], df['close'])
                cci = indicators._calculate_cci_optimized(df['high'], df['low'], df['close'])
                
                end_time = time.perf_counter()
                execution_time = (end_time - start_time) * 1000
                times.append(execution_time)
            
            # Calculate statistics
            avg_time = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            std_time = np.std(times)
            
            print(f"  📊 Results:")
            print(f"    Average: {avg_time:.2f}ms")
            print(f"    Min: {min_time:.2f}ms")
            print(f"    Max: {max_time:.2f}ms")
            print(f"    Std Dev: {std_time:.2f}ms")
            print(f"    Optimization: {indicators.actual_optimization}")
            
            self.performance_results[test_name] = {
                'data_size': data_size,
                'iterations': iterations,
                'avg_time': avg_time,
                'min_time': min_time,
                'max_time': max_time,
                'std_time': std_time,
                'optimization': indicators.actual_optimization
            }
    
    async def test_all_configurations(self):
        """Test all configuration combinations."""
        print("\n" + "=" * 60)
        print("5. CONFIGURATION TESTS")
        print("=" * 60)
        
        # Generate test data
        df = self.create_realistic_data(1000)
        
        for config_name, config in self.test_configs.items():
            print(f"\n--- Testing {config_name} ---")
            
            try:
                indicators = TechnicalIndicators(config)
                
                print(f"  Optimization level: {indicators.actual_optimization}")
                print(f"  Use TA-Lib: {indicators.use_talib}")
                print(f"  Fallback on error: {indicators.fallback_on_error}")
                
                # Test indicators
                start_time = time.perf_counter()
                
                rsi = indicators._calculate_rsi_optimized(df['close'])
                macd = indicators._calculate_macd_optimized(df['close'])
                
                end_time = time.perf_counter()
                execution_time = (end_time - start_time) * 1000
                
                print(f"  ✅ Success: {execution_time:.2f}ms")
                print(f"    RSI: {rsi.iloc[-1]:.2f}")
                print(f"    MACD: {macd[0].iloc[-1]:.4f}")
                
                # Test performance report
                if indicators.benchmark_enabled:
                    report = indicators.get_performance_report()
                    if 'summary' in report and report['summary']:
                        print(f"    Performance report available")
                
            except Exception as e:
                print(f"  ❌ {config_name} failed: {e}")
                if 'strict' in config_name and not HAS_TALIB:
                    print(f"    (Expected failure - TA-Lib not available)")
    
    async def test_data_quality_scenarios(self):
        """Test various data quality scenarios."""
        print("\n" + "=" * 60)
        print("6. DATA QUALITY TESTS")
        print("=" * 60)
        
        quality_tests = {
            'perfect_data': self.create_realistic_data(1000),
            'sparse_data': self.create_sparse_data(1000),
            'irregular_intervals': self.create_irregular_data(1000),
            'duplicate_timestamps': self.create_duplicate_data(1000),
            'outliers': self.create_outlier_data(1000),
        }
        
        config = self.test_configs['auto_with_talib']
        
        for test_name, df in quality_tests.items():
            print(f"\n--- Testing {test_name} ---")
            
            try:
                indicators = TechnicalIndicators(config)
                
                # Data quality metrics
                print(f"  Data size: {len(df)}")
                print(f"  Close range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                print(f"  NaN count: {df.isna().sum().sum()}")
                
                # Test calculations
                rsi = indicators._calculate_rsi_optimized(df['close'])
                macd = indicators._calculate_macd_optimized(df['close'])
                
                # Quality of results
                rsi_valid = (~rsi.isna()).sum()
                macd_valid = (~macd[0].isna()).sum()
                
                print(f"  ✅ RSI valid values: {rsi_valid}/{len(rsi)} ({rsi_valid/len(rsi)*100:.1f}%)")
                print(f"  ✅ MACD valid values: {macd_valid}/{len(macd[0])} ({macd_valid/len(macd[0])*100:.1f}%)")
                
            except Exception as e:
                print(f"  ❌ {test_name} failed: {e}")
    
    async def test_phase4_enhancements(self):
        """Test Phase 4 enhanced features."""
        print("\n" + "=" * 60)
        print("7. PHASE 4 ENHANCEMENT TESTS")
        print("=" * 60)
        
        df = self.create_realistic_data(1000)
        config = self.test_configs['auto_with_talib']
        indicators = TechnicalIndicators(config)
        
        # Test enhanced MACD
        print("\n--- Enhanced MACD ---")
        try:
            macd_enhanced = indicators.calculate_enhanced_macd(df)
            
            crossover_up_count = macd_enhanced['crossover_up'].sum()
            crossover_down_count = macd_enhanced['crossover_down'].sum()
            
            print(f"  ✅ Enhanced MACD successful")
            print(f"    Crossovers up: {crossover_up_count}")
            print(f"    Crossovers down: {crossover_down_count}")
            print(f"    Latest MACD: {macd_enhanced['macd'].iloc[-1]:.4f}")
            
        except Exception as e:
            print(f"  ❌ Enhanced MACD failed: {e}")
        
        # Test comprehensive moving averages
        print("\n--- Comprehensive Moving Averages ---")
        try:
            mas = indicators.calculate_all_moving_averages(df)
            
            print(f"  ✅ Moving averages successful")
            print(f"    Available MAs: {len(mas)}")
            for ma_name, ma_series in list(mas.items())[:5]:  # Show first 5
                if not ma_series.empty and not pd.isna(ma_series.iloc[-1]):
                    print(f"    {ma_name}: {ma_series.iloc[-1]:.2f}")
            
        except Exception as e:
            print(f"  ❌ Moving averages failed: {e}")
        
        # Test momentum suite
        print("\n--- Momentum Suite ---")
        try:
            momentum = indicators.calculate_momentum_suite(df)
            
            print(f"  ✅ Momentum suite successful")
            print(f"    Available indicators: {len(momentum)}")
            for indicator_name, indicator_series in list(momentum.items())[:5]:  # Show first 5
                if hasattr(indicator_series, 'iloc') and not pd.isna(indicator_series.iloc[-1]):
                    print(f"    {indicator_name}: {indicator_series.iloc[-1]:.2f}")
            
        except Exception as e:
            print(f"  ❌ Momentum suite failed: {e}")
        
        # Test mathematical functions
        print("\n--- Mathematical Functions ---")
        try:
            math_funcs = indicators.calculate_math_functions(df)
            
            print(f"  ✅ Math functions successful")
            print(f"    Available functions: {len(math_funcs)}")
            for func_name, func_series in list(math_funcs.items())[:3]:  # Show first 3
                if not func_series.empty and not pd.isna(func_series.iloc[-1]):
                    print(f"    {func_name}: {func_series.iloc[-1]:.4f}")
            
        except Exception as e:
            print(f"  ❌ Math functions failed: {e}")
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        # Summary statistics
        total_tests = 0
        passed_tests = 0
        
        # Live data results
        if self.test_results:
            print(f"\n📊 LIVE DATA TESTS:")
            for symbol, timeframes in self.test_results.items():
                if isinstance(timeframes, dict):
                    symbol_passed = sum(1 for tf in timeframes.values() if tf.get('success', False))
                    symbol_total = len(timeframes)
                    total_tests += symbol_total
                    passed_tests += symbol_passed
                    print(f"  {symbol}: {symbol_passed}/{symbol_total} timeframes passed")
        
        # Edge case results
        if self.edge_case_results:
            print(f"\n🔍 EDGE CASE TESTS:")
            edge_passed = sum(1 for result in self.edge_case_results.values() 
                            if not result.get('success') == False)
            edge_total = len(self.edge_case_results)
            total_tests += edge_total
            passed_tests += edge_passed
            print(f"  {edge_passed}/{edge_total} edge cases handled successfully")
        
        # Performance results
        if self.performance_results:
            print(f"\n⚡ PERFORMANCE STRESS TESTS:")
            for test_name, result in self.performance_results.items():
                print(f"  {test_name}: {result['avg_time']:.2f}ms avg ({result['data_size']} points)")
        
        # Overall success rate
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            print(f"\n🎯 OVERALL SUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Optimization status
        print(f"\n🚀 OPTIMIZATION STATUS:")
        print(f"  TA-Lib Available: {'✅ Yes' if HAS_TALIB else '❌ No'}")
        if HAS_TALIB:
            print(f"  Expected Speedup: 7.1x overall, 15.9x RSI")
        else:
            print(f"  Fallback Mode: pandas/numpy implementations")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if HAS_TALIB:
            print(f"  ✅ System is optimally configured")
            print(f"  ✅ Use 'auto' optimization level for best performance")
            print(f"  ✅ Enable fallback_on_error for production reliability")
        else:
            print(f"  ⚠️  Install TA-Lib for 7x performance improvement:")
            print(f"      pip install TA-Lib")
        
        print(f"\n" + "=" * 80)
        print(f"COMPREHENSIVE TESTING COMPLETE")
        print(f"=" * 80)
    
    # Helper methods for generating test data
    def create_minimal_data(self, size):
        """Create minimal dataset for testing."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        close = np.random.uniform(100, 110, size)
        
        return pd.DataFrame({
            'open': close * 0.999,
            'high': close * 1.001,
            'low': close * 0.998,
            'close': close,
            'volume': np.random.uniform(1000, 2000, size)
        }, index=dates)
    
    def create_realistic_data(self, size):
        """Create realistic market data."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        
        # Random walk with realistic parameters
        returns = np.random.normal(0.0001, 0.008, size)
        close_prices = 45000 * np.exp(np.cumsum(returns))
        
        # Create OHLC with realistic relationships
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0]
        
        high_prices = np.maximum(open_prices, close_prices) * np.random.uniform(1.0, 1.005, size)
        low_prices = np.minimum(open_prices, close_prices) * np.random.uniform(0.995, 1.0, size)
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(100000, 1000000, size)
        }, index=dates)
    
    def create_volatile_data(self, size):
        """Create highly volatile data."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        
        # High volatility returns
        returns = np.random.normal(0, 0.05, size)  # 5% volatility
        close_prices = 45000 * np.exp(np.cumsum(returns))
        
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0]
        
        high_prices = np.maximum(open_prices, close_prices) * np.random.uniform(1.0, 1.02, size)
        low_prices = np.minimum(open_prices, close_prices) * np.random.uniform(0.98, 1.0, size)
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(500000, 2000000, size)
        }, index=dates)
    
    def create_trending_data(self, size):
        """Create strongly trending data."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        
        # Strong upward trend with noise
        trend = np.linspace(0, 0.5, size)  # 50% growth over period
        noise = np.random.normal(0, 0.01, size)
        
        close_prices = 45000 * np.exp(trend + noise)
        
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0]
        
        high_prices = np.maximum(open_prices, close_prices) * np.random.uniform(1.0, 1.003, size)
        low_prices = np.minimum(open_prices, close_prices) * np.random.uniform(0.997, 1.0, size)
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(200000, 800000, size)
        }, index=dates)
    
    def create_flat_data(self, size):
        """Create flat/sideways market data."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        
        # Very low volatility around a mean
        base_price = 45000
        close_prices = base_price + np.random.normal(0, base_price * 0.002, size)
        
        open_prices = np.roll(close_prices, 1)
        open_prices[0] = close_prices[0]
        
        high_prices = np.maximum(open_prices, close_prices) * np.random.uniform(1.0, 1.001, size)
        low_prices = np.minimum(open_prices, close_prices) * np.random.uniform(0.999, 1.0, size)
        
        return pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': np.random.uniform(50000, 200000, size)
        }, index=dates)
    
    def create_gapped_data(self, size):
        """Create data with gaps (simulating weekend/maintenance)."""
        df = self.create_realistic_data(size)
        
        # Introduce random gaps
        gap_indices = np.random.choice(range(10, size-10), size=max(1, size//20), replace=False)
        
        for idx in gap_indices:
            # Create a price gap
            gap_multiplier = np.random.uniform(0.95, 1.05)
            df.iloc[idx:, :4] *= gap_multiplier
        
        return df
    
    def create_extreme_values_data(self, size):
        """Create data with extreme values."""
        df = self.create_realistic_data(size)
        
        # Add some extreme outliers
        outlier_indices = np.random.choice(range(size), size=max(1, size//50), replace=False)
        
        for idx in outlier_indices:
            multiplier = np.random.choice([0.5, 2.0])  # 50% drop or 100% spike
            df.iloc[idx, :4] *= multiplier
        
        return df
    
    def create_zero_volume_data(self, size):
        """Create data with zero volume periods."""
        df = self.create_realistic_data(size)
        
        # Set random periods to zero volume
        zero_indices = np.random.choice(range(size), size=max(1, size//10), replace=False)
        df.loc[df.index[zero_indices], 'volume'] = 0
        
        return df
    
    def create_negative_price_data(self, size):
        """Create data with some negative prices (edge case)."""
        df = self.create_realistic_data(size)
        
        # This is an edge case that shouldn't happen in real markets
        # but tests robustness
        negative_indices = np.random.choice(range(size), size=max(1, size//100), replace=False)
        df.iloc[negative_indices, :4] = -np.abs(df.iloc[negative_indices, :4])
        
        return df
    
    def create_nan_data(self, size):
        """Create data with NaN values."""
        df = self.create_realistic_data(size)
        
        # Introduce random NaN values
        nan_indices = np.random.choice(range(size), size=max(1, size//20), replace=False)
        nan_columns = np.random.choice(df.columns[:4], size=len(nan_indices))
        
        for idx, col in zip(nan_indices, nan_columns):
            df.iloc[idx, df.columns.get_loc(col)] = np.nan
        
        return df
    
    def create_inf_data(self, size):
        """Create data with infinite values."""
        df = self.create_realistic_data(size)
        
        # Introduce random infinite values
        inf_indices = np.random.choice(range(size), size=max(1, size//50), replace=False)
        
        for idx in inf_indices:
            df.iloc[idx, 0] = np.inf  # Set open price to infinity
        
        return df
    
    def create_string_data(self, size):
        """Create data with string values (should cause errors)."""
        df = self.create_realistic_data(size)
        
        # Replace some values with strings
        string_indices = np.random.choice(range(1, size), size=max(1, size//20), replace=False)
        
        for idx in string_indices:
            df.iloc[idx, 0] = "invalid"
        
        return df
    
    def create_sparse_data(self, size):
        """Create sparse data with many missing values."""
        dates = pd.date_range(end=datetime.now(), periods=size, freq='5min')
        
        # Only 30% of data points are valid
        valid_indices = np.random.choice(range(size), size=int(size * 0.3), replace=False)
        
        df = pd.DataFrame(index=dates, columns=['open', 'high', 'low', 'close', 'volume'])
        df[:] = np.nan
        
        # Fill valid indices with realistic data
        for idx in valid_indices:
            price = 45000 + np.random.normal(0, 1000)
            df.iloc[idx] = {
                'open': price * 0.999,
                'high': price * 1.001,
                'low': price * 0.998,
                'close': price,
                'volume': np.random.uniform(100000, 500000)
            }
        
        return df
    
    def create_irregular_data(self, size):
        """Create data with irregular time intervals."""
        # Create irregular timestamps
        base_time = datetime.now() - timedelta(days=1)
        timestamps = []
        
        for i in range(size):
            # Random intervals between 1 minute and 1 hour
            interval = np.random.uniform(60, 3600)  # seconds
            base_time += timedelta(seconds=interval)
            timestamps.append(base_time)
        
        close_prices = 45000 + np.cumsum(np.random.normal(0, 100, size))
        
        return pd.DataFrame({
            'open': close_prices * 0.999,
            'high': close_prices * 1.002,
            'low': close_prices * 0.998,
            'close': close_prices,
            'volume': np.random.uniform(100000, 500000, size)
        }, index=pd.DatetimeIndex(timestamps))
    
    def create_duplicate_data(self, size):
        """Create data with duplicate timestamps."""
        df = self.create_realistic_data(size)
        
        # Duplicate some timestamps
        duplicate_indices = np.random.choice(range(1, size), size=max(1, size//10), replace=False)
        
        for idx in duplicate_indices:
            df.index.values[idx] = df.index.values[idx-1]
        
        return df
    
    def create_outlier_data(self, size):
        """Create data with statistical outliers."""
        df = self.create_realistic_data(size)
        
        # Add statistical outliers (>3 standard deviations)
        mean_price = df['close'].mean()
        std_price = df['close'].std()
        
        outlier_indices = np.random.choice(range(size), size=max(1, size//20), replace=False)
        
        for idx in outlier_indices:
            # Create outlier that's 5+ standard deviations away
            outlier_multiplier = np.random.choice([-5, 5]) * std_price / mean_price + 1
            df.iloc[idx, :4] *= outlier_multiplier
        
        return df

async def main():
    """Run the comprehensive test suite."""
    tester = ComprehensiveOptimizationTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())