#!/usr/bin/env python3
"""
Advanced Features Test Runner
Tests HMM regime detection, SMC order block detection, and OU mean reversion analysis.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.indicators.base_indicator import BaseIndicator
from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators
from src.core.logger import Logger

class AdvancedFeaturesTestRunner:
    """Test runner for advanced features."""
    
    def __init__(self):
        """Initialize test runner."""
        self.logger = Logger("AdvancedFeaturesTest")
        self.config = {
            'timeframes': {
                'base': {'interval': '1m', 'weight': 0.4, 'validation': {'min_candles': 100}},
                'ltf': {'interval': '5m', 'weight': 0.3, 'validation': {'min_candles': 50}},
                'mtf': {'interval': '30m', 'weight': 0.2, 'validation': {'min_candles': 50}},
                'htf': {'interval': '4h', 'weight': 0.1, 'validation': {'min_candles': 50}}
            },
            'analysis': {
                'indicators': {
                    'technical': {},
                    'price_structure': {}
                }
            }
        }
        
    def create_test_data(self, num_points: int = 1000) -> pd.DataFrame:
        """Create realistic test data for advanced features testing."""
        np.random.seed(42)  # For reproducible results
        
        # Generate realistic price data with trends and volatility changes
        dates = pd.date_range(start='2024-01-01', periods=num_points, freq='1h')
        
        # Create price series with regime changes
        price_series = []
        base_price = 50000
        
        for i in range(num_points):
            # Create different regimes
            if i < 300:  # Trending up regime
                trend = 0.0005
                volatility = 0.01
            elif i < 600:  # High volatility ranging regime
                trend = 0.0001
                volatility = 0.025
            elif i < 900:  # Trending down regime
                trend = -0.0003
                volatility = 0.015
            else:  # Low volatility ranging regime
                trend = 0.0001
                volatility = 0.008
            
            # Generate price with trend and volatility
            if i == 0:
                price = base_price
            else:
                price_change = trend + np.random.normal(0, volatility)
                price = price_series[-1] * (1 + price_change)
            
            price_series.append(price)
        
        # Create OHLCV data
        data = []
        for i in range(num_points):
            price = price_series[i]
            
            # Generate realistic OHLC around the price
            volatility_factor = np.random.uniform(0.5, 1.5)
            daily_range = price * 0.02 * volatility_factor
            
            open_price = price + np.random.uniform(-daily_range/4, daily_range/4)
            high_price = max(open_price, price) + np.random.uniform(0, daily_range/2)
            low_price = min(open_price, price) - np.random.uniform(0, daily_range/2)
            close_price = price + np.random.uniform(-daily_range/4, daily_range/4)
            
            # Ensure OHLC logic
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            # Generate volume with some correlation to price movement
            volume_base = 1000000
            volume_multiplier = 1 + abs(close_price - open_price) / open_price * 10
            volume = volume_base * volume_multiplier * np.random.uniform(0.5, 2.0)
            
            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def test_hmm_regime_detection(self):
        """Test HMM regime detection."""
        print("🧠 Testing HMM Regime Detection")
        
        try:
            # Create test indicator
            indicator = TechnicalIndicators(self.config, self.logger)
            
            # Create test data
            test_data = self.create_test_data(1000)
            
            # Test HMM regime detection
            regime_info = indicator._hmm_regime_detection(test_data, n_regimes=3)
            
            print(f"  Current Regime: {regime_info['current_regime']}")
            print(f"  Confidence: {regime_info['confidence']:.3f}")
            print(f"  Available Regimes: {regime_info['regimes']}")
            print(f"  Regime Probabilities: {[f'{p:.3f}' for p in regime_info['regime_probabilities']]}")
            
            # Validate results
            assert 'current_regime' in regime_info
            assert 'confidence' in regime_info
            assert 'regimes' in regime_info
            assert 'regime_probabilities' in regime_info
            assert 'transition_matrix' in regime_info
            
            assert len(regime_info['regimes']) == 3
            assert len(regime_info['regime_probabilities']) == 3
            assert 0 <= regime_info['confidence'] <= 1
            
            print("  ✅ HMM Regime Detection: PASSED")
            return True
            
        except Exception as e:
            print(f"  ❌ HMM Regime Detection: FAILED - {str(e)}")
            return False
    
    def test_smc_order_block_detection(self):
        """Test SMC order block detection."""
        print("📦 Testing SMC Order Block Detection")
        
        try:
            # Create test indicator
            indicator = PriceStructureIndicators(self.config, self.logger)
            
            # Create test data with clear order blocks
            test_data = self.create_test_data(500)
            
            # Test SMC order block detection
            order_blocks = indicator._smc_order_block_detection(test_data)
            
            print(f"  Order Blocks Found: {len(order_blocks)}")
            
            if order_blocks:
                # Show details of first few blocks
                for i, block in enumerate(order_blocks[:3]):
                    print(f"    Block {i+1}: {block['type']} | Strength: {block['strength']:.3f} | Range: {block['low']:.2f}-{block['high']:.2f}")
            
            # Validate results
            assert isinstance(order_blocks, list)
            
            for block in order_blocks:
                assert 'type' in block
                assert 'strength' in block
                assert 'high' in block
                assert 'low' in block
                assert 'index' in block
                assert block['type'] in ['bullish', 'bearish']
                assert 0 <= block['strength'] <= 1
                assert block['high'] >= block['low']
            
            print("  ✅ SMC Order Block Detection: PASSED")
            return True
            
        except Exception as e:
            print(f"  ❌ SMC Order Block Detection: FAILED - {str(e)}")
            return False
    
    def test_ou_mean_reversion_analysis(self):
        """Test OU mean reversion analysis."""
        print("🔄 Testing OU Mean Reversion Analysis")
        
        try:
            # Create test indicator
            indicator = TechnicalIndicators(self.config, self.logger)
            
            # Create test data with mean reversion characteristics
            test_data = self.create_test_data(800)
            
            # Test OU mean reversion analysis
            ou_analysis = indicator._ou_mean_reversion_analysis(test_data)
            
            print(f"  Theta (Mean Reversion Speed): {ou_analysis['theta']:.6f}")
            print(f"  Half-life: {ou_analysis['half_life']:.2f} periods")
            print(f"  Z-score: {ou_analysis['z_score']:.3f}")
            print(f"  Mean Reversion Strength: {ou_analysis['mean_reversion_strength']:.3f}")
            print(f"  Signal: {ou_analysis['signal']}")
            print(f"  Signal Strength: {ou_analysis['signal_strength']:.3f}")
            print(f"  Fair Value: ${ou_analysis['fair_value']:.2f}")
            
            # Validate results
            assert 'theta' in ou_analysis
            assert 'mu' in ou_analysis
            assert 'sigma' in ou_analysis
            assert 'half_life' in ou_analysis
            assert 'z_score' in ou_analysis
            assert 'mean_reversion_strength' in ou_analysis
            assert 'signal' in ou_analysis
            assert 'signal_strength' in ou_analysis
            assert 'fair_value' in ou_analysis
            assert 'confidence' in ou_analysis
            
            assert ou_analysis['theta'] >= 0
            assert ou_analysis['sigma'] > 0
            assert ou_analysis['half_life'] > 0
            assert 0 <= ou_analysis['mean_reversion_strength'] <= 1
            assert 0 <= ou_analysis['signal_strength'] <= 1
            assert 0 <= ou_analysis['confidence'] <= 1
            assert ou_analysis['signal'] in ['STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL']
            
            print("  ✅ OU Mean Reversion Analysis: PASSED")
            return True
            
        except Exception as e:
            print(f"  ❌ OU Mean Reversion Analysis: FAILED - {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all advanced features tests."""
        print("🚀 Starting Advanced Features Test Suite")
        print("=" * 60)
        
        results = {}
        
        # Test HMM regime detection
        results['hmm_regime'] = self.test_hmm_regime_detection()
        
        # Test SMC order block detection
        results['smc_order_blocks'] = self.test_smc_order_block_detection()
        
        # Test OU mean reversion analysis
        results['ou_mean_reversion'] = self.test_ou_mean_reversion_analysis()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 ADVANCED FEATURES TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"🧠 HMM Regime Detection: {'✅ PASSED' if results['hmm_regime'] else '❌ FAILED'}")
        print(f"📦 SMC Order Block Detection: {'✅ PASSED' if results['smc_order_blocks'] else '❌ FAILED'}")
        print(f"🔄 OU Mean Reversion Analysis: {'✅ PASSED' if results['ou_mean_reversion'] else '❌ FAILED'}")
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {total_tests - passed_tests}")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 ALL ADVANCED FEATURES TESTS PASSED!")
        elif success_rate >= 80:
            print("✅ Most advanced features are working correctly!")
        else:
            print("⚠️  Some advanced features need attention.")
        
        return results

if __name__ == "__main__":
    runner = AdvancedFeaturesTestRunner()
    runner.run_all_tests() 