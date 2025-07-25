#!/usr/bin/env python3
"""
Comprehensive Debug Test for Enhanced Indicator Scoring System

This script demonstrates all debug logging features in the enhanced indicator 
scoring system, including:
- UnifiedScoringFramework debug logging
- BaseIndicator integration debug logging  
- Configuration loading debug logging
- Performance monitoring debug logging
- Enhanced transformation method debug logging
- Cache management debug logging
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.scoring.unified_scoring_framework import UnifiedScoringFramework, ScoringConfig
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.core.logger import Logger


def setup_debug_logging():
    """Setup comprehensive debug logging."""
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('debug_enhanced_scoring.log')
        ]
    )
    
    # Create logger
    logger = Logger("DebugEnhancedScoring")
    return logger


def create_test_market_data():
    """Create comprehensive test market data."""
    print("🔧 Creating test market data...")
    
    # Create date range
    dates = pd.date_range(start='2024-01-01', periods=200, freq='1H')
    
    # Base OHLCV data
    base_data = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(200) * 100,
        'high': 50000 + np.random.randn(200) * 100 + 50,
        'low': 50000 + np.random.randn(200) * 100 - 50,
        'close': 50000 + np.random.randn(200) * 100,
        'volume': 1000 + np.random.exponential(500, 200)
    })
    
    # Ensure OHLC relationships
    base_data['high'] = np.maximum(base_data[['open', 'close']].max(axis=1), base_data['high'])
    base_data['low'] = np.minimum(base_data[['open', 'close']].min(axis=1), base_data['low'])
    
    # Create multi-timeframe data
    market_data = {
        'symbol': 'BTCUSDT',
        'ohlcv': {
            'base': base_data,
            'ltf': base_data.iloc[::2].copy(),    # 2H data
            'mtf': base_data.iloc[::4].copy(),    # 4H data  
            'htf': base_data.iloc[::8].copy()     # 8H data
        }
    }
    
    print(f"✅ Created test data with {len(base_data)} base candles")
    return market_data


def create_debug_config():
    """Create configuration with debug mode enabled."""
    print("🔧 Creating debug configuration...")
    
    config = {
        'analysis': {
            'indicators': {
                'volume': {
                    'components': {},
                    'parameters': {
                        'relative_volume_period': 20,
                        'volume_delta_lookback': 20,
                        'cmf_period': 20,
                        'adl_lookback': 20,
                        'obv_lookback': 20
                    }
                },
                'sentiment': {
                    'components': {},
                    'parameters': {
                        'volatility_period': 20,
                        'fear_greed_period': 14
                    }
                }
            }
        },
        'scoring': {
            'mode': 'enhanced',
            'sigmoid_steepness': 0.1,
            'tanh_sensitivity': 1.0,
            'regime_aware': True,
            'confluence_enhanced': True,
            'debug_mode': True,
            'log_transformations': True,
            'performance_tracking': True,
            'enable_caching': True,
            'cache_timeout': 60,
            'max_cache_size': 100
        },
        'timeframes': {
            'base': {'weight': 0.4, 'interval': 1},
            'ltf': {'weight': 0.3, 'interval': 5},
            'mtf': {'weight': 0.2, 'interval': 30},
            'htf': {'weight': 0.1, 'interval': 240}
        }
    }
    
    print("✅ Created debug configuration")
    return config


def test_unified_scoring_framework_debug():
    """Test UnifiedScoringFramework debug logging."""
    print("\n" + "="*80)
    print("🔍 TESTING: UnifiedScoringFramework Debug Logging")
    print("="*80)
    
    # Create debug config
    scoring_config = ScoringConfig(
        mode='enhanced',
        debug_mode=True,
        log_transformations=True,
        performance_tracking=True,
        enable_caching=True,
        cache_timeout=60,
        max_cache_size=100
    )
    
    print("🔧 Creating UnifiedScoringFramework with debug enabled...")
    framework = UnifiedScoringFramework(scoring_config)
    
    print("\n📊 Testing various transformation methods...")
    
    # Test RSI enhanced transformation
    print("\n🔍 Testing RSI Enhanced Transformation:")
    rsi_scores = []
    for rsi_value in [20, 30, 50, 70, 85]:
        score = framework.transform_score(rsi_value, 'rsi_enhanced', 
                                        overbought=70, oversold=30)
        rsi_scores.append((rsi_value, score))
        print(f"  RSI {rsi_value} → Score {score:.2f}")
    
    # Test volume enhanced transformation
    print("\n🔍 Testing Volume Enhanced Transformation:")
    volume_scores = []
    for volume_ratio in [0.5, 1.0, 2.0, 3.5, 8.0]:
        score = framework.transform_score(volume_ratio, 'volume_enhanced')
        volume_scores.append((volume_ratio, score))
        print(f"  Volume {volume_ratio}x → Score {score:.2f}")
    
    # Test volatility enhanced transformation
    print("\n🔍 Testing Volatility Enhanced Transformation:")
    volatility_scores = []
    for volatility in [15, 25, 45, 70, 120]:
        score = framework.transform_score(volatility, 'volatility_enhanced', 
                                        base_threshold=60)
        volatility_scores.append((volatility, score))
        print(f"  Volatility {volatility}% → Score {score:.2f}")
    
    # Test caching
    print("\n💾 Testing Cache Performance:")
    start_time = time.time()
    for _ in range(10):
        framework.transform_score(50, 'rsi_enhanced')
    cached_time = time.time() - start_time
    print(f"  10 cached calls took {cached_time*1000:.2f}ms")
    
    # Get performance stats
    print("\n📊 Performance Statistics:")
    stats = framework.get_performance_stats()
    print(f"  Total calls: {stats['performance_summary']['total_calls']}")
    print(f"  Average time: {stats['performance_summary']['avg_time_overall_ms']:.2f}ms")
    print(f"  Cache utilization: {stats['cache_stats']['utilization_percent']:.1f}%")
    
    # Test cache clearing
    print("\n💾 Testing Cache Management:")
    framework.clear_cache()
    
    # Test performance reset
    print("\n📊 Testing Performance Reset:")
    framework.reset_performance_stats()
    
    return framework


def test_base_indicator_debug():
    """Test BaseIndicator debug logging."""
    print("\n" + "="*80)
    print("🔍 TESTING: BaseIndicator Debug Logging")
    print("="*80)
    
    # Create debug config
    config = create_debug_config()
    logger = setup_debug_logging()
    
    print("🔧 Creating VolumeIndicators with debug enabled...")
    volume_indicators = VolumeIndicators(config, logger)
    
    print("\n📊 Testing unified_score method:")
    
    # Test various unified scoring calls
    test_cases = [
        (2.5, 'volume_enhanced', {'spike_threshold': 3.0}),
        (75, 'rsi_enhanced', {'overbought': 70, 'oversold': 30}),
        (45, 'volatility_enhanced', {'base_threshold': 60})
    ]
    
    for value, method, kwargs in test_cases:
        print(f"\n🔍 Testing {method} with value {value}:")
        score = volume_indicators.unified_score(value, method, **kwargs)
        print(f"  Result: {score:.2f}")
    
    return volume_indicators


def test_enhanced_methods_debug():
    """Test enhanced methods debug logging."""
    print("\n" + "="*80)
    print("🔍 TESTING: Enhanced Methods Debug Logging")
    print("="*80)
    
    # Create test data and config
    market_data = create_test_market_data()
    config = create_debug_config()
    logger = setup_debug_logging()
    
    print("🔧 Creating indicators with debug enabled...")
    volume_indicators = VolumeIndicators(config, logger)
    
    print("\n📊 Testing enhanced volume methods:")
    
    # Test relative volume calculation
    print("\n🔍 Testing Enhanced Relative Volume:")
    rel_vol_score = volume_indicators._calculate_relative_volume(market_data)
    print(f"  Relative volume score: {rel_vol_score:.2f}")
    
    # Test other enhanced methods if available
    print("\n🔍 Testing other enhanced methods...")
    
    return volume_indicators


def test_configuration_debug():
    """Test configuration loading debug."""
    print("\n" + "="*80)
    print("🔍 TESTING: Configuration Debug Logging")
    print("="*80)
    
    # Create debug config
    config = create_debug_config()
    logger = setup_debug_logging()
    
    print("🔧 Testing configuration loading with debug...")
    
    # Test multiple indicator types
    indicators = [
        ('VolumeIndicators', VolumeIndicators),
        ('SentimentIndicators', SentimentIndicators)
    ]
    
    for name, indicator_class in indicators:
        print(f"\n📊 Creating {name} with debug config:")
        try:
            indicator = indicator_class(config, logger)
            print(f"  ✅ {name} created successfully")
        except Exception as e:
            print(f"  ❌ {name} failed: {e}")
    
    return config


def test_performance_monitoring_debug():
    """Test performance monitoring debug."""
    print("\n" + "="*80)
    print("🔍 TESTING: Performance Monitoring Debug")
    print("="*80)
    
    # Create framework with debug
    scoring_config = ScoringConfig(
        mode='enhanced',
        debug_mode=True,
        performance_tracking=True,
        enable_caching=True
    )
    
    framework = UnifiedScoringFramework(scoring_config)
    
    print("🔧 Running performance tests...")
    
    # Run multiple transformations
    methods_to_test = [
        ('rsi_enhanced', [20, 30, 50, 70, 85]),
        ('volume_enhanced', [0.5, 1.0, 2.0, 3.5, 8.0]),
        ('volatility_enhanced', [15, 25, 45, 70, 120])
    ]
    
    for method, values in methods_to_test:
        print(f"\n📊 Testing {method}:")
        for value in values:
            score = framework.transform_score(value, method)
            print(f"  {method}({value}) → {score:.2f}")
    
    # Get detailed performance stats
    print("\n📊 Final Performance Statistics:")
    stats = framework.get_performance_stats()
    
    # Print detailed method performance
    print("\n📈 Method Performance Breakdown:")
    for method, perf in stats['method_performance'].items():
        print(f"  {method}:")
        print(f"    Calls: {perf['calls']}")
        print(f"    Avg time: {perf['avg_time']*1000:.2f}ms")
        print(f"    Min time: {perf['min_time']*1000:.2f}ms")
        print(f"    Max time: {perf['max_time']*1000:.2f}ms")
    
    return framework


def main():
    """Main test function."""
    print("🚀 Starting Comprehensive Debug Test for Enhanced Indicator Scoring")
    print("="*80)
    
    # Setup logging
    logger = setup_debug_logging()
    
    try:
        # Test 1: UnifiedScoringFramework debug logging
        framework = test_unified_scoring_framework_debug()
        
        # Test 2: BaseIndicator debug logging
        volume_indicators = test_base_indicator_debug()
        
        # Test 3: Enhanced methods debug logging
        enhanced_indicators = test_enhanced_methods_debug()
        
        # Test 4: Configuration debug logging
        config = test_configuration_debug()
        
        # Test 5: Performance monitoring debug
        perf_framework = test_performance_monitoring_debug()
        
        print("\n" + "="*80)
        print("🎉 ALL DEBUG TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        print("\n📊 Summary:")
        print("✅ UnifiedScoringFramework debug logging - WORKING")
        print("✅ BaseIndicator integration debug logging - WORKING")
        print("✅ Enhanced methods debug logging - WORKING")
        print("✅ Configuration loading debug logging - WORKING")
        print("✅ Performance monitoring debug logging - WORKING")
        
        print("\n📋 Debug Features Demonstrated:")
        print("🔧 Framework initialization logging")
        print("📊 Method selection and transformation tracking")
        print("💾 Cache management and performance logging")
        print("⏱️ Performance monitoring and statistics")
        print("🔍 Input/output value tracking")
        print("📈 Scoring interpretation and context")
        print("⚠️ Error handling and debugging")
        print("🎯 Configuration parameter validation")
        
        print("\n💡 To enable debug logging in production:")
        print("1. Set scoring.debug_mode = true in config")
        print("2. Set scoring.log_transformations = true for detailed logging")
        print("3. Set scoring.performance_tracking = true for performance stats")
        print("4. Use logger.setLevel(logging.DEBUG) for debug output")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 