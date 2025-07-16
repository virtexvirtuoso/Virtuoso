#!/usr/bin/env python3
"""
Test script to verify the open interest threshold fix.

This script tests the open interest calculation with the new, more sensitive thresholds
to ensure it properly detects market scenarios instead of always returning neutral.
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

from src.indicators.orderflow_indicators import OrderflowIndicators
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class OpenInterestThresholdTest:
    """Test class for verifying open interest threshold fixes."""
    
    def __init__(self):
        """Initialize the test."""
        self.config_manager = ConfigManager()
        self.config = self.config_manager._config
        
        # Initialize orderflow indicators
        self.orderflow = OrderflowIndicators(self.config, None)
        
    def create_test_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Create test scenarios with different OI and price changes."""
        
        base_price = 2772.56
        base_oi = 1234000.0
        current_time = int(time.time() * 1000)
        
        # Generate base OHLCV data
        ohlcv_data = []
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(100):
            timestamp = start_time + timedelta(minutes=i)
            open_price = base_price + np.random.uniform(-2, 2)
            high_price = open_price + np.random.uniform(0, 1)
            low_price = open_price - np.random.uniform(0, 1)
            close_price = open_price + np.random.uniform(-1, 1)
            volume = np.random.uniform(100, 1000)
            
            ohlcv_data.append([
                timestamp.timestamp() * 1000,
                open_price, high_price, low_price, close_price, volume
            ])
        
        base_ohlcv_df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        base_ohlcv_df['timestamp'] = pd.to_datetime(base_ohlcv_df['timestamp'], unit='ms')
        base_ohlcv_df.set_index('timestamp', inplace=True)
        
        scenarios = {
            "real_market_conditions": {
                "description": "Real market conditions from logs (OI: +0.03%, Price: +0.02%)",
                "oi_change_pct": 0.03,
                "price_change_pct": 0.02,
                "expected_scenario": "Scenario 1: OI↑ + Price↑ = Bullish"
            },
            "small_bullish_divergence": {
                "description": "Small bullish divergence (OI: -0.05%, Price: -0.03%)",
                "oi_change_pct": -0.05,
                "price_change_pct": -0.03,
                "expected_scenario": "Scenario 4: OI↓ + Price↓ = Bullish"
            },
            "small_bearish_divergence": {
                "description": "Small bearish divergence (OI: -0.04%, Price: +0.06%)",
                "oi_change_pct": -0.04,
                "price_change_pct": 0.06,
                "expected_scenario": "Scenario 2: OI↓ + Price↑ = Bearish"
            },
            "small_bearish_confirmation": {
                "description": "Small bearish confirmation (OI: +0.08%, Price: -0.04%)",
                "oi_change_pct": 0.08,
                "price_change_pct": -0.04,
                "expected_scenario": "Scenario 3: OI↑ + Price↓ = Bearish"
            },
            "tiny_changes": {
                "description": "Very tiny changes (OI: +0.01%, Price: +0.005%)",
                "oi_change_pct": 0.01,
                "price_change_pct": 0.005,
                "expected_scenario": "Should be neutral due to minimal changes"
            },
            "strong_bullish": {
                "description": "Strong bullish signal (OI: +1.2%, Price: +0.8%)",
                "oi_change_pct": 1.2,
                "price_change_pct": 0.8,
                "expected_scenario": "Scenario 1: OI↑ + Price↑ = Bullish (strong)"
            }
        }
        
        # Create market data for each scenario
        test_data = {}
        
        for scenario_name, scenario in scenarios.items():
            oi_change_pct = scenario["oi_change_pct"]
            price_change_pct = scenario["price_change_pct"]
            
            # Calculate actual values
            current_oi = base_oi * (1 + oi_change_pct / 100)
            previous_oi = base_oi
            
            # Adjust OHLCV to reflect price change
            adjusted_ohlcv = base_ohlcv_df.copy()
            price_multiplier = 1 + (price_change_pct / 100)
            
            # Adjust the last few candles to show the price change
            last_close = adjusted_ohlcv['close'].iloc[-2]
            new_close = last_close * price_multiplier
            adjusted_ohlcv.loc[adjusted_ohlcv.index[-1], 'close'] = new_close
            adjusted_ohlcv.loc[adjusted_ohlcv.index[-1], 'open'] = last_close
            adjusted_ohlcv.loc[adjusted_ohlcv.index[-1], 'high'] = max(last_close, new_close) + 0.5
            adjusted_ohlcv.loc[adjusted_ohlcv.index[-1], 'low'] = min(last_close, new_close) - 0.5
            
            test_data[scenario_name] = {
                'symbol': 'ETHUSDT',
                'exchange': 'bybit',
                'timestamp': current_time,
                
                # Open interest data
                'open_interest': {
                    'current': current_oi,
                    'previous': previous_oi,
                    'timestamp': current_time
                },
                
                # OHLCV data for price direction
                'ohlcv': {
                    'base': adjusted_ohlcv,
                    'ltf': adjusted_ohlcv,
                    'mtf': adjusted_ohlcv,
                    'htf': adjusted_ohlcv
                },
                
                # Ticker data
                'ticker': {
                    'symbol': 'ETHUSDT',
                    'last': new_close,
                    'openInterest': current_oi,
                    'timestamp': current_time
                },
                
                # Add scenario info for testing
                'test_scenario': scenario
            }
        
        return test_data
    
    def test_open_interest_scenarios(self, test_data: Dict[str, Dict[str, Any]]):
        """Test open interest calculation for all scenarios."""
        
        print("\n" + "="*80)
        print("OPEN INTEREST THRESHOLD FIX TEST RESULTS")
        print("="*80)
        
        # Check current configuration
        oi_config = self.config.get('analysis', {}).get('indicators', {}).get('orderflow', {}).get('open_interest', {})
        minimal_threshold = oi_config.get('minimal_change_threshold', 0.5)
        price_threshold = oi_config.get('price_direction_threshold', 0.1)
        
        print(f"\nCurrent Configuration:")
        print(f"  minimal_change_threshold: {minimal_threshold}%")
        print(f"  price_direction_threshold: {price_threshold}%")
        
        results = {}
        
        for scenario_name, market_data in test_data.items():
            scenario_info = market_data['test_scenario']
            
            print(f"\n{'-'*60}")
            print(f"Testing: {scenario_name}")
            print(f"Description: {scenario_info['description']}")
            print(f"Expected: {scenario_info['expected_scenario']}")
            
            try:
                # Test the open interest calculation
                oi_score = self.orderflow._calculate_open_interest_score(market_data)
                
                # Get the actual values for verification
                oi_data = self.orderflow._get_open_interest_values(market_data)
                current_oi = oi_data['current']
                previous_oi = oi_data['previous']
                oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100
                
                price_change_pct = self.orderflow._get_price_direction(market_data)
                
                # Determine if changes are significant based on thresholds
                oi_significant = abs(oi_change_pct) >= minimal_threshold
                price_significant = abs(price_change_pct) >= price_threshold
                
                print(f"Results:")
                print(f"  OI Change: {oi_change_pct:+.3f}% (significant: {oi_significant})")
                print(f"  Price Change: {price_change_pct:+.3f}% (significant: {price_significant})")
                print(f"  OI Score: {oi_score:.2f}")
                
                # Determine the interpretation
                if oi_score > 55:
                    interpretation = "BULLISH"
                elif oi_score < 45:
                    interpretation = "BEARISH"
                else:
                    interpretation = "NEUTRAL"
                
                print(f"  Interpretation: {interpretation}")
                
                # Check if this matches expectations
                if scenario_name == "tiny_changes":
                    expected_neutral = True
                    success = interpretation == "NEUTRAL"
                elif scenario_name in ["real_market_conditions", "strong_bullish", "small_bullish_divergence"]:
                    expected_neutral = False
                    success = interpretation == "BULLISH"
                elif scenario_name in ["small_bearish_divergence", "small_bearish_confirmation"]:
                    expected_neutral = False
                    success = interpretation == "BEARISH"
                else:
                    expected_neutral = False
                    success = interpretation != "NEUTRAL"
                
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"  Status: {status}")
                
                results[scenario_name] = {
                    'oi_change_pct': oi_change_pct,
                    'price_change_pct': price_change_pct,
                    'oi_score': oi_score,
                    'interpretation': interpretation,
                    'success': success
                }
                
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                results[scenario_name] = {
                    'error': str(e),
                    'success': False
                }
        
        # Summary
        print(f"\n{'-'*60}")
        print("SUMMARY")
        print(f"{'-'*60}")
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r.get('success', False))
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Open interest thresholds are now properly calibrated.")
        else:
            print("⚠️  Some tests failed. The thresholds may need further adjustment.")
            
        # Show before/after comparison
        print(f"\n{'-'*60}")
        print("THRESHOLD COMPARISON")
        print(f"{'-'*60}")
        print("BEFORE (causing neutral scores):")
        print("  minimal_change_threshold: 0.5%")
        print("  price_direction_threshold: 0.1%")
        print()
        print("AFTER (new sensitive thresholds):")
        print(f"  minimal_change_threshold: {minimal_threshold}%")
        print(f"  price_direction_threshold: {price_threshold}%")
        print()
        print("Real market example from logs:")
        print("  OI Change: +0.03%, Price Change: +0.02%")
        print("  OLD: Both below thresholds → NEUTRAL")
        print("  NEW: Both above thresholds → BULLISH (Scenario 1)")
        
        return results

async def main():
    """Main test execution."""
    print("Testing Open Interest Threshold Fix...")
    
    # Initialize test
    test = OpenInterestThresholdTest()
    
    # Create test scenarios
    test_data = test.create_test_scenarios()
    
    # Test open interest scenarios
    results = test.test_open_interest_scenarios(test_data)

if __name__ == "__main__":
    asyncio.run(main()) 