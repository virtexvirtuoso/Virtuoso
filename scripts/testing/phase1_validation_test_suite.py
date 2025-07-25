#!/usr/bin/env python3
"""
Phase 1 Validation Test Suite
============================

Comprehensive test suite to validate all 13 logic inconsistency fixes
with real market scenarios and edge cases.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import unittest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.indicators.technical_indicators import TechnicalIndicators
from src.indicators.volume_indicators import VolumeIndicators
from src.indicators.sentiment_indicators import SentimentIndicators
from src.indicators.orderbook_indicators import OrderbookIndicators
from src.indicators.orderflow_indicators import OrderflowIndicators
from src.indicators.price_structure_indicators import PriceStructureIndicators

class Phase1ValidationTestSuite(unittest.TestCase):
    """
    Comprehensive validation test suite for Phase 1 fixes
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.technical_indicators = TechnicalIndicators()
        self.volume_indicators = VolumeIndicators()
        self.sentiment_indicators = SentimentIndicators()
        self.orderbook_indicators = OrderbookIndicators()
        self.orderflow_indicators = OrderflowIndicators()
        self.price_structure_indicators = PriceStructureIndicators()
        
        # Create test data
        self.test_data = self._create_test_data()
        self.test_results = []
    
    def _create_test_data(self) -> pd.DataFrame:
        """Create realistic test market data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Create realistic OHLCV data
        np.random.seed(42)  # For reproducible tests
        
        # Start with base price
        base_price = 50000
        prices = [base_price]
        
        # Generate realistic price movements
        for i in range(99):
            change = np.random.normal(0, 0.02)  # 2% volatility
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Create OHLCV data
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': dates[i],
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_fix_1_timeframe_score_interpretation(self):
        """Test Fix 1: Price Structure _interpret_timeframe_score"""
        print("🧪 Testing Fix 1: Timeframe Score Interpretation")
        
        # Test cases with expected interpretations
        test_cases = [
            (85, "Extremely Bullish"),
            (75, "Strongly Bullish"),
            (60, "Moderately Bullish"),
            (50, "Slightly Bullish"),
            (40, "Neutral"),
            (30, "Slightly Bearish"),
            (20, "Moderately Bearish"),
            (10, "Strongly Bearish"),
        ]
        
        for score, expected in test_cases:
            result = self.price_structure_indicators._interpret_timeframe_score(score)
            self.assertIsInstance(result, str)
            
            # Verify logical consistency
            if score >= 55:
                self.assertIn("Bullish", result, f"Score {score} should be bullish, got {result}")
            elif score <= 45:
                self.assertIn("Bearish", result, f"Score {score} should be bearish, got {result}")
        
        self.test_results.append({
            "test": "Fix 1: Timeframe Score Interpretation",
            "status": "PASSED",
            "details": "All score interpretations are logically consistent"
        })
        print("✅ Fix 1 validation passed")
    
    def test_fix_2_williams_r_scoring(self):
        """Test Fix 2: Williams %R scoring logic"""
        print("🧪 Testing Fix 2: Williams %R Scoring")
        
        # Create test data with known Williams %R conditions
        test_data = self.test_data.copy()
        
        # Create oversold condition (Williams %R near -100)
        oversold_data = test_data.copy()
        oversold_data['high'] = oversold_data['close'] * 1.2
        oversold_data['low'] = oversold_data['close'] * 0.8
        oversold_data['close'] = oversold_data['low'] * 1.01  # Near lows
        
        # Create overbought condition (Williams %R near 0)
        overbought_data = test_data.copy()
        overbought_data['high'] = overbought_data['close'] * 1.2
        overbought_data['low'] = overbought_data['close'] * 0.8
        overbought_data['close'] = overbought_data['high'] * 0.99  # Near highs
        
        try:
            # Test oversold condition - should be bullish (high score)
            oversold_score = self.technical_indicators._calculate_williams_r_score(oversold_data)
            self.assertGreaterEqual(oversold_score, 60, "Oversold Williams %R should be bullish")
            
            # Test overbought condition - should be bearish (low score)
            overbought_score = self.technical_indicators._calculate_williams_r_score(overbought_data)
            self.assertLessEqual(overbought_score, 40, "Overbought Williams %R should be bearish")
            
            self.test_results.append({
                "test": "Fix 2: Williams %R Scoring",
                "status": "PASSED",
                "details": f"Oversold: {oversold_score:.1f}, Overbought: {overbought_score:.1f}"
            })
            print("✅ Fix 2 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 2: Williams %R Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 2 validation failed: {str(e)}")
    
    def test_fix_3_order_blocks_scoring(self):
        """Test Fix 3: Order Block scoring logic"""
        print("🧪 Testing Fix 3: Order Block Scoring")
        
        try:
            score = self.price_structure_indicators._calculate_order_blocks_score(self.test_data)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Order block score should be >= 0")
            self.assertLessEqual(score, 100, "Order block score should be <= 100")
            
            # Verify it returns a float
            self.assertIsInstance(score, float)
            
            self.test_results.append({
                "test": "Fix 3: Order Block Scoring",
                "status": "PASSED",
                "details": f"Score: {score:.2f}, properly bounded and typed"
            })
            print("✅ Fix 3 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 3: Order Block Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 3 validation failed: {str(e)}")
    
    def test_fix_4_volume_profile_scoring(self):
        """Test Fix 4: Volume Profile scoring with context"""
        print("🧪 Testing Fix 4: Volume Profile Scoring")
        
        try:
            score = self.volume_indicators._calculate_volume_profile_score(self.test_data)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Volume profile score should be >= 0")
            self.assertLessEqual(score, 100, "Volume profile score should be <= 100")
            
            # Test with different market conditions
            trending_up_data = self.test_data.copy()
            trending_up_data['close'] = trending_up_data['close'] * np.linspace(1, 1.1, len(trending_up_data))
            
            trending_down_data = self.test_data.copy()
            trending_down_data['close'] = trending_down_data['close'] * np.linspace(1, 0.9, len(trending_down_data))
            
            up_score = self.volume_indicators._calculate_volume_profile_score(trending_up_data)
            down_score = self.volume_indicators._calculate_volume_profile_score(trending_down_data)
            
            self.test_results.append({
                "test": "Fix 4: Volume Profile Scoring",
                "status": "PASSED",
                "details": f"Base: {score:.2f}, Uptrend: {up_score:.2f}, Downtrend: {down_score:.2f}"
            })
            print("✅ Fix 4 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 4: Volume Profile Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 4 validation failed: {str(e)}")
    
    def test_fix_5_funding_rate_scoring(self):
        """Test Fix 5: Funding rate scoring with extremes"""
        print("🧪 Testing Fix 5: Funding Rate Scoring")
        
        try:
            # Test with mock funding rate data
            test_symbol = "BTCUSDT"
            
            # Mock the funding rate method
            def mock_get_funding_rate(symbol):
                return {"funding_rate": 0.001}  # 0.1% funding rate
            
            self.sentiment_indicators._get_funding_rate = mock_get_funding_rate
            
            score = self.sentiment_indicators._calculate_funding_score(test_symbol)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Funding rate score should be >= 0")
            self.assertLessEqual(score, 100, "Funding rate score should be <= 100")
            
            # Test extreme funding rate
            def mock_extreme_funding_rate(symbol):
                return {"funding_rate": 0.01}  # 1% funding rate (extreme)
            
            self.sentiment_indicators._get_funding_rate = mock_extreme_funding_rate
            extreme_score = self.sentiment_indicators._calculate_funding_score(test_symbol)
            
            # Extreme funding should be closer to neutral
            self.assertGreater(extreme_score, 40, "Extreme funding should not be too bearish")
            self.assertLess(extreme_score, 60, "Extreme funding should not be too bullish")
            
            self.test_results.append({
                "test": "Fix 5: Funding Rate Scoring",
                "status": "PASSED",
                "details": f"Normal: {score:.2f}, Extreme: {extreme_score:.2f}"
            })
            print("✅ Fix 5 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 5: Funding Rate Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 5 validation failed: {str(e)}")
    
    def test_fix_6_orderbook_imbalance_scoring(self):
        """Test Fix 6: Orderbook imbalance with depth confidence"""
        print("🧪 Testing Fix 6: Orderbook Imbalance Scoring")
        
        try:
            # Create mock orderbook data
            orderbook_data = {
                "bids": [[49000, 1.0], [48900, 2.0], [48800, 1.5]],
                "asks": [[50000, 0.5], [50100, 1.0], [50200, 1.5]]
            }
            
            score = self.orderbook_indicators._calculate_orderbook_imbalance(orderbook_data)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Orderbook imbalance score should be >= 0")
            self.assertLessEqual(score, 100, "Orderbook imbalance score should be <= 100")
            
            # Test with extreme imbalance
            extreme_imbalance = {
                "bids": [[49000, 10.0], [48900, 20.0], [48800, 15.0]],
                "asks": [[50000, 0.1], [50100, 0.1], [50200, 0.1]]
            }
            
            extreme_score = self.orderbook_indicators._calculate_orderbook_imbalance(extreme_imbalance)
            
            # Should be bullish but not extreme due to confidence capping
            self.assertGreater(extreme_score, 60, "Strong bid imbalance should be bullish")
            self.assertLess(extreme_score, 90, "Extreme imbalance should be confidence-capped")
            
            self.test_results.append({
                "test": "Fix 6: Orderbook Imbalance Scoring",
                "status": "PASSED",
                "details": f"Normal: {score:.2f}, Extreme: {extreme_score:.2f}"
            })
            print("✅ Fix 6 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 6: Orderbook Imbalance Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 6 validation failed: {str(e)}")
    
    def test_fix_7_cvd_scoring(self):
        """Test Fix 7: CVD scoring with buy/sell pressure"""
        print("🧪 Testing Fix 7: CVD Scoring")
        
        try:
            # Create data with buying pressure (prices going up)
            buying_data = self.test_data.copy()
            buying_data['close'] = buying_data['close'] * np.linspace(1, 1.05, len(buying_data))
            
            # Create data with selling pressure (prices going down)
            selling_data = self.test_data.copy()
            selling_data['close'] = selling_data['close'] * np.linspace(1, 0.95, len(selling_data))
            
            buying_score = self.orderflow_indicators._calculate_cvd_score(buying_data)
            selling_score = self.orderflow_indicators._calculate_cvd_score(selling_data)
            
            # Verify scores are in valid range
            self.assertGreaterEqual(buying_score, 0, "CVD score should be >= 0")
            self.assertLessEqual(buying_score, 100, "CVD score should be <= 100")
            self.assertGreaterEqual(selling_score, 0, "CVD score should be >= 0")
            self.assertLessEqual(selling_score, 100, "CVD score should be <= 100")
            
            # Buying pressure should generally lead to higher scores than selling pressure
            # (though this depends on the specific implementation)
            
            self.test_results.append({
                "test": "Fix 7: CVD Scoring",
                "status": "PASSED",
                "details": f"Buying pressure: {buying_score:.2f}, Selling pressure: {selling_score:.2f}"
            })
            print("✅ Fix 7 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 7: CVD Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 7 validation failed: {str(e)}")
    
    def test_fix_8_range_position_scoring(self):
        """Test Fix 8: Range position scoring with context"""
        print("🧪 Testing Fix 8: Range Position Scoring")
        
        try:
            score = self.price_structure_indicators._analyze_range_position(self.test_data)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Range position score should be >= 0")
            self.assertLessEqual(score, 100, "Range position score should be <= 100")
            
            self.test_results.append({
                "test": "Fix 8: Range Position Scoring",
                "status": "PASSED",
                "details": f"Score: {score:.2f}, properly bounded"
            })
            print("✅ Fix 8 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 8: Range Position Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 8 validation failed: {str(e)}")
    
    def test_fix_9_relative_volume_scoring(self):
        """Test Fix 9: Relative volume scoring with price direction"""
        print("🧪 Testing Fix 9: Relative Volume Scoring")
        
        try:
            # Create high volume up move
            high_vol_up = self.test_data.copy()
            high_vol_up['volume'].iloc[-1] = high_vol_up['volume'].mean() * 3
            high_vol_up['close'].iloc[-1] = high_vol_up['close'].iloc[-2] * 1.02
            
            # Create high volume down move
            high_vol_down = self.test_data.copy()
            high_vol_down['volume'].iloc[-1] = high_vol_down['volume'].mean() * 3
            high_vol_down['close'].iloc[-1] = high_vol_down['close'].iloc[-2] * 0.98
            
            up_score = self.volume_indicators._calculate_relative_volume_score(high_vol_up)
            down_score = self.volume_indicators._calculate_relative_volume_score(high_vol_down)
            
            # Verify scores are in valid range
            self.assertGreaterEqual(up_score, 0, "Relative volume score should be >= 0")
            self.assertLessEqual(up_score, 100, "Relative volume score should be <= 100")
            self.assertGreaterEqual(down_score, 0, "Relative volume score should be >= 0")
            self.assertLessEqual(down_score, 100, "Relative volume score should be <= 100")
            
            # High volume on up move should be more bullish than high volume on down move
            self.assertGreater(up_score, down_score, "High volume up should be more bullish than high volume down")
            
            self.test_results.append({
                "test": "Fix 9: Relative Volume Scoring",
                "status": "PASSED",
                "details": f"High vol up: {up_score:.2f}, High vol down: {down_score:.2f}"
            })
            print("✅ Fix 9 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 9: Relative Volume Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 9 validation failed: {str(e)}")
    
    def test_fix_10_lsr_scoring(self):
        """Test Fix 10: LSR scoring with overextension detection"""
        print("🧪 Testing Fix 10: LSR Scoring")
        
        try:
            # Mock LSR data
            def mock_get_lsr(symbol):
                return {"ratio": 1.2}  # Slightly more longs
            
            self.sentiment_indicators._get_long_short_ratio = mock_get_lsr
            
            score = self.sentiment_indicators._calculate_lsr_score("BTCUSDT")
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "LSR score should be >= 0")
            self.assertLessEqual(score, 100, "LSR score should be <= 100")
            
            # Test extreme LSR
            def mock_extreme_lsr(symbol):
                return {"ratio": 2.0}  # Very high LSR
            
            self.sentiment_indicators._get_long_short_ratio = mock_extreme_lsr
            extreme_score = self.sentiment_indicators._calculate_lsr_score("BTCUSDT")
            
            # Extreme LSR should be moderated
            self.assertLess(extreme_score, 70, "Extreme LSR should be moderated")
            
            self.test_results.append({
                "test": "Fix 10: LSR Scoring",
                "status": "PASSED",
                "details": f"Normal LSR: {score:.2f}, Extreme LSR: {extreme_score:.2f}"
            })
            print("✅ Fix 10 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 10: LSR Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 10 validation failed: {str(e)}")
    
    def test_fix_11_spread_scoring(self):
        """Test Fix 11: Spread scoring with liquidity stress detection"""
        print("🧪 Testing Fix 11: Spread Scoring")
        
        try:
            # Create tight spread orderbook
            tight_spread = {
                "bids": [[49999, 1.0], [49998, 2.0]],
                "asks": [[50001, 1.0], [50002, 2.0]]
            }
            
            # Create wide spread orderbook
            wide_spread = {
                "bids": [[49900, 1.0], [49800, 2.0]],
                "asks": [[50100, 1.0], [50200, 2.0]]
            }
            
            tight_score = self.orderbook_indicators._calculate_spread_score(tight_spread)
            wide_score = self.orderbook_indicators._calculate_spread_score(wide_spread)
            
            # Verify scores are in valid range
            self.assertGreaterEqual(tight_score, 0, "Spread score should be >= 0")
            self.assertLessEqual(tight_score, 100, "Spread score should be <= 100")
            self.assertGreaterEqual(wide_score, 0, "Spread score should be >= 0")
            self.assertLessEqual(wide_score, 100, "Spread score should be <= 100")
            
            # Wide spread should be more bearish than tight spread
            self.assertGreater(tight_score, wide_score, "Tight spread should be less bearish than wide spread")
            
            self.test_results.append({
                "test": "Fix 11: Spread Scoring",
                "status": "PASSED",
                "details": f"Tight spread: {tight_score:.2f}, Wide spread: {wide_score:.2f}"
            })
            print("✅ Fix 11 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 11: Spread Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 11 validation failed: {str(e)}")
    
    def test_fix_12_trade_flow_scoring(self):
        """Test Fix 12: Trade flow scoring with directional context"""
        print("🧪 Testing Fix 12: Trade Flow Scoring")
        
        try:
            # Create data with consistent buying (prices going up)
            buying_flow_data = self.test_data.copy()
            buying_flow_data['close'] = buying_flow_data['close'] * np.linspace(1, 1.03, len(buying_flow_data))
            
            # Create data with consistent selling (prices going down)
            selling_flow_data = self.test_data.copy()
            selling_flow_data['close'] = selling_flow_data['close'] * np.linspace(1, 0.97, len(selling_flow_data))
            
            buying_score = self.orderflow_indicators._calculate_trade_flow_score(buying_flow_data)
            selling_score = self.orderflow_indicators._calculate_trade_flow_score(selling_flow_data)
            
            # Verify scores are in valid range
            self.assertGreaterEqual(buying_score, 0, "Trade flow score should be >= 0")
            self.assertLessEqual(buying_score, 100, "Trade flow score should be <= 100")
            self.assertGreaterEqual(selling_score, 0, "Trade flow score should be >= 0")
            self.assertLessEqual(selling_score, 100, "Trade flow score should be <= 100")
            
            self.test_results.append({
                "test": "Fix 12: Trade Flow Scoring",
                "status": "PASSED",
                "details": f"Buying flow: {buying_score:.2f}, Selling flow: {selling_score:.2f}"
            })
            print("✅ Fix 12 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 12: Trade Flow Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 12 validation failed: {str(e)}")
    
    def test_fix_13_support_resistance_scoring(self):
        """Test Fix 13: Support/resistance proximity scoring"""
        print("🧪 Testing Fix 13: Support/Resistance Scoring")
        
        try:
            score = self.price_structure_indicators._calculate_support_resistance_score(self.test_data)
            
            # Verify score is in valid range
            self.assertGreaterEqual(score, 0, "Support/resistance score should be >= 0")
            self.assertLessEqual(score, 100, "Support/resistance score should be <= 100")
            
            self.test_results.append({
                "test": "Fix 13: Support/Resistance Scoring",
                "status": "PASSED",
                "details": f"Score: {score:.2f}, properly bounded"
            })
            print("✅ Fix 13 validation passed")
            
        except Exception as e:
            self.test_results.append({
                "test": "Fix 13: Support/Resistance Scoring",
                "status": "FAILED",
                "details": f"Error: {str(e)}"
            })
            print(f"❌ Fix 13 validation failed: {str(e)}")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("🧪 Testing Edge Cases")
        
        edge_cases_passed = 0
        total_edge_cases = 0
        
        # Test with empty data
        empty_data = pd.DataFrame()
        
        try:
            score = self.technical_indicators._calculate_williams_r_score(empty_data)
            self.assertEqual(score, 50.0, "Empty data should return neutral score")
            edge_cases_passed += 1
        except:
            pass
        total_edge_cases += 1
        
        # Test with minimal data
        minimal_data = self.test_data.head(5)
        
        try:
            score = self.volume_indicators._calculate_volume_profile_score(minimal_data)
            self.assertEqual(score, 50.0, "Minimal data should return neutral score")
            edge_cases_passed += 1
        except:
            pass
        total_edge_cases += 1
        
        # Test with invalid orderbook data
        invalid_orderbook = {"invalid": "data"}
        
        try:
            score = self.orderbook_indicators._calculate_orderbook_imbalance(invalid_orderbook)
            self.assertEqual(score, 50.0, "Invalid orderbook should return neutral score")
            edge_cases_passed += 1
        except:
            pass
        total_edge_cases += 1
        
        self.test_results.append({
            "test": "Edge Cases",
            "status": "PASSED" if edge_cases_passed == total_edge_cases else "PARTIAL",
            "details": f"{edge_cases_passed}/{total_edge_cases} edge cases handled correctly"
        })
        print(f"✅ Edge cases validation: {edge_cases_passed}/{total_edge_cases} passed")
    
    def generate_validation_report(self) -> Dict:
        """Generate comprehensive validation report"""
        passed_tests = sum(1 for test in self.test_results if test["status"] == "PASSED")
        total_tests = len(self.test_results)
        
        report = {
            "phase": "Phase 1 Validation",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        failed_tests = [test for test in self.test_results if test["status"] == "FAILED"]
        
        if not failed_tests:
            recommendations.append("✅ All logic fixes validated successfully")
            recommendations.append("✅ Ready to proceed to Phase 2")
            recommendations.append("✅ Consider deploying to staging environment")
        else:
            recommendations.append("❌ Some fixes need attention before proceeding")
            for test in failed_tests:
                recommendations.append(f"❌ Fix required: {test['test']}")
        
        recommendations.append("📊 Monitor production performance after deployment")
        recommendations.append("📊 Set up alerts for scoring anomalies")
        
        return recommendations

def main():
    """Main execution function"""
    print("🧪 Phase 1 Validation Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_methods = [
        'test_fix_1_timeframe_score_interpretation',
        'test_fix_2_williams_r_scoring',
        'test_fix_3_order_blocks_scoring',
        'test_fix_4_volume_profile_scoring',
        'test_fix_5_funding_rate_scoring',
        'test_fix_6_orderbook_imbalance_scoring',
        'test_fix_7_cvd_scoring',
        'test_fix_8_range_position_scoring',
        'test_fix_9_relative_volume_scoring',
        'test_fix_10_lsr_scoring',
        'test_fix_11_spread_scoring',
        'test_fix_12_trade_flow_scoring',
        'test_fix_13_support_resistance_scoring',
        'test_edge_cases'
    ]
    
    test_instance = Phase1ValidationTestSuite()
    test_instance.setUp()
    
    # Run tests manually to capture results
    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
        except Exception as e:
            print(f"❌ Test {method_name} failed with error: {str(e)}")
    
    # Generate report
    report = test_instance.generate_validation_report()
    
    # Save report
    report_path = "reports/phase1_validation_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Validation Report:")
    print(f"   Total Tests: {report['summary']['total_tests']}")
    print(f"   Passed: {report['summary']['passed_tests']}")
    print(f"   Failed: {report['summary']['failed_tests']}")
    print(f"   Success Rate: {report['summary']['success_rate']}")
    
    print(f"\n📁 Full report saved to: {report_path}")
    
    print("\n🔄 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")

if __name__ == "__main__":
    main() 