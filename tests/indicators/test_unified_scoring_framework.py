#!/usr/bin/env python3

"""
Comprehensive unit tests for the UnifiedScoringFramework.

This test suite validates the elegant integration of linear and non-linear
scoring methods across all indicator types.
"""

import pytest
import numpy as np
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.scoring import ScoringMode, ScoringConfig, UnifiedScoringFramework


class TestUnifiedScoringFramework:
    """Test suite for UnifiedScoringFramework functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ScoringConfig(
            mode=ScoringMode.AUTO_DETECT,
            sigmoid_steepness=0.1,
            tanh_sensitivity=1.0,
            debug_mode=True
        )
        self.framework = UnifiedScoringFramework(self.config)
    
    # ==================== CONFIGURATION TESTS ====================
    
    def test_default_configuration(self):
        """Test default configuration initialization."""
        framework = UnifiedScoringFramework()
        assert framework.config.mode == ScoringMode.AUTO_DETECT
        assert framework.config.sigmoid_steepness == 0.1
        assert framework.config.tanh_sensitivity == 1.0
        assert framework.config.market_regime_aware is True
        assert framework.config.confluence_enhanced is True
    
    def test_custom_configuration(self):
        """Test custom configuration initialization."""
        config = ScoringConfig(
            mode=ScoringMode.ENHANCED_LINEAR,
            sigmoid_steepness=0.2,
            tanh_sensitivity=2.0,
            market_regime_aware=False,
            debug_mode=True
        )
        framework = UnifiedScoringFramework(config)
        assert framework.config.mode == ScoringMode.ENHANCED_LINEAR
        assert framework.config.sigmoid_steepness == 0.2
        assert framework.config.tanh_sensitivity == 2.0
        assert framework.config.market_regime_aware is False
        assert framework.config.debug_mode is True
    
    # ==================== SOPHISTICATION DETECTION TESTS ====================
    
    def test_sophisticated_method_detection(self):
        """Test automatic detection of sophisticated methods."""
        # Test sophisticated method patterns
        assert self.framework._is_sophisticated_method('obv_sigmoid') is True
        assert self.framework._is_sophisticated_method('vwap_tanh_log') is True
        assert self.framework._is_sophisticated_method('volume_profile_tanh') is True
        assert self.framework._is_sophisticated_method('cvd_calculation') is True
        assert self.framework._is_sophisticated_method('orderbook_pressure') is True
        
        # Test linear method patterns
        assert self.framework._is_sophisticated_method('rsi_score') is False
        assert self.framework._is_sophisticated_method('volatility_score') is False
        assert self.framework._is_sophisticated_method('simple_momentum') is False
        assert self.framework._is_sophisticated_method('basic_volume') is False
    
    # ==================== TRADITIONAL SOPHISTICATED METHODS TESTS ====================
    
    def test_obv_sigmoid_transform(self):
        """Test OBV sigmoid transformation preservation."""
        # Test normal z-scores
        assert abs(self.framework._obv_sigmoid_transform(0.0) - 50.0) < 0.1
        assert self.framework._obv_sigmoid_transform(2.0) > 70.0
        assert self.framework._obv_sigmoid_transform(-2.0) < 30.0
        
        # Test extreme values
        assert self.framework._obv_sigmoid_transform(10.0) > 95.0
        assert self.framework._obv_sigmoid_transform(-10.0) < 5.0
        
        # Test bounds
        result = self.framework._obv_sigmoid_transform(100.0)
        assert 0 <= result <= 100
    
    def test_vwap_tanh_log_transform(self):
        """Test VWAP tanh + log transformation preservation."""
        # Test normal ratios
        assert abs(self.framework._vwap_tanh_log_transform(1.0) - 50.0) < 0.1
        assert self.framework._vwap_tanh_log_transform(1.1) > 50.0
        assert self.framework._vwap_tanh_log_transform(0.9) < 50.0
        
        # Test extreme ratios
        assert self.framework._vwap_tanh_log_transform(2.0) > 70.0
        assert self.framework._vwap_tanh_log_transform(0.5) < 30.0
        
        # Test edge cases
        assert self.framework._vwap_tanh_log_transform(0.0) == 50.0  # Invalid ratio
        assert self.framework._vwap_tanh_log_transform(-1.0) == 50.0  # Invalid ratio
    
    def test_volume_profile_tanh_transform(self):
        """Test volume profile tanh transformation preservation."""
        # Test normal position ratios
        assert abs(self.framework._volume_profile_tanh_transform(0.5) - 50.0) < 0.1
        assert self.framework._volume_profile_tanh_transform(0.8) > 60.0
        assert self.framework._volume_profile_tanh_transform(0.2) < 40.0
        
        # Test extreme positions
        assert self.framework._volume_profile_tanh_transform(1.0) > 80.0
        assert self.framework._volume_profile_tanh_transform(0.0) < 20.0
    
    def test_cvd_tanh_transform(self):
        """Test CVD tanh transformation preservation."""
        # Test normal CVD percentages
        assert abs(self.framework._cvd_tanh_transform(0.0) - 50.0) < 0.1
        assert self.framework._cvd_tanh_transform(0.5) > 70.0
        assert self.framework._cvd_tanh_transform(-0.5) < 30.0
        
        # Test extreme CVD values
        assert self.framework._cvd_tanh_transform(1.0) > 90.0
        assert self.framework._cvd_tanh_transform(-1.0) < 10.0
    
    def test_relative_volume_tanh_transform(self):
        """Test relative volume tanh transformation preservation."""
        # Test normal relative volume
        assert abs(self.framework._relative_volume_tanh_transform(1.0) - 50.0) < 0.1
        assert self.framework._relative_volume_tanh_transform(2.0) > 70.0
        assert self.framework._relative_volume_tanh_transform(0.5) < 30.0
        
        # Test extreme relative volume
        assert self.framework._relative_volume_tanh_transform(5.0) > 90.0
        assert self.framework._relative_volume_tanh_transform(0.1) < 20.0
    
    # ==================== ENHANCED LINEAR METHODS TESTS ====================
    
    def test_rsi_enhanced_transform(self):
        """Test enhanced RSI transformation."""
        # Test normal RSI values
        assert abs(self.framework._rsi_enhanced_transform(50.0) - 50.0) < 5.0
        assert self.framework._rsi_enhanced_transform(60.0) > 50.0
        assert self.framework._rsi_enhanced_transform(40.0) < 50.0
        
        # Test extreme RSI values (should show exponential behavior)
        rsi_75 = self.framework._rsi_enhanced_transform(75.0)
        rsi_85 = self.framework._rsi_enhanced_transform(85.0)
        rsi_95 = self.framework._rsi_enhanced_transform(95.0)
        
        # Exponential decay should make differences more pronounced
        assert rsi_75 > rsi_85 > rsi_95  # Lower scores for higher RSI (bearish)
        assert rsi_95 < 20.0  # Very extreme RSI should give very low score
        
        # Test oversold extreme values
        rsi_25 = self.framework._rsi_enhanced_transform(25.0)
        rsi_15 = self.framework._rsi_enhanced_transform(15.0)
        rsi_5 = self.framework._rsi_enhanced_transform(5.0)
        
        assert rsi_25 < rsi_15 < rsi_5  # Higher scores for lower RSI (bullish)
        assert rsi_5 > 80.0  # Very extreme oversold should give very high score
    
    def test_rsi_enhanced_transform_with_regime(self):
        """Test enhanced RSI transformation with market regime awareness."""
        # Test with high volatility regime (wider bands)
        regime = {'volatility': 'HIGH'}
        
        # RSI 72 should be neutral in high volatility (threshold moved to 75)
        score_high_vol = self.framework._rsi_enhanced_transform(72.0, market_regime=regime)
        score_normal = self.framework._rsi_enhanced_transform(72.0)
        
        # High volatility should result in higher score (less bearish)
        assert score_high_vol > score_normal
    
    def test_volatility_enhanced_transform(self):
        """Test enhanced volatility transformation."""
        # Test normal volatility
        assert self.framework._volatility_enhanced_transform(30.0) >= 50.0
        assert self.framework._volatility_enhanced_transform(45.0) >= 50.0
        
        # Test high volatility (should show exponential decay)
        vol_65 = self.framework._volatility_enhanced_transform(65.0)
        vol_80 = self.framework._volatility_enhanced_transform(80.0)
        vol_100 = self.framework._volatility_enhanced_transform(100.0)
        
        # Higher volatility should result in lower scores
        assert vol_65 > vol_80 > vol_100
        assert vol_100 < 20.0  # Very high volatility should give very low score
    
    def test_volume_enhanced_transform(self):
        """Test enhanced volume transformation."""
        # Test normal volume ratios
        assert abs(self.framework._volume_enhanced_transform(1.0) - 50.0) < 10.0
        assert self.framework._volume_enhanced_transform(1.5) > 50.0
        
        # Test volume spikes (should show exponential behavior)
        vol_3 = self.framework._volume_enhanced_transform(3.0)
        vol_5 = self.framework._volume_enhanced_transform(5.0)
        vol_10 = self.framework._volume_enhanced_transform(10.0)
        
        # Volume spikes should result in high scores with exponential decay
        assert vol_3 < vol_5 < vol_10
        assert vol_10 > 90.0  # Very high volume should give very high score
    
    def test_oir_di_enhanced_transform(self):
        """Test enhanced OIR/DI transformation."""
        # Test normal ratios
        assert abs(self.framework._oir_di_enhanced_transform(0.0) - 50.0) < 5.0
        assert self.framework._oir_di_enhanced_transform(0.5) > 60.0
        assert self.framework._oir_di_enhanced_transform(-0.5) < 40.0
        
        # Test with confidence weighting
        high_conf = self.framework._oir_di_enhanced_transform(0.5, confidence_weight=0.9)
        low_conf = self.framework._oir_di_enhanced_transform(0.5, confidence_weight=0.1)
        
        # High confidence should result in more extreme scores
        assert abs(high_conf - 50.0) > abs(low_conf - 50.0)
    
    def test_momentum_enhanced_transform(self):
        """Test enhanced momentum transformation."""
        # Test normal momentum
        assert abs(self.framework._momentum_enhanced_transform(0.0) - 50.0) < 1.0
        assert self.framework._momentum_enhanced_transform(0.5) > 60.0
        assert self.framework._momentum_enhanced_transform(-0.5) < 40.0
        
        # Test with volatility adjustment
        high_vol = self.framework._momentum_enhanced_transform(0.5, volatility_adjustment=2.0)
        low_vol = self.framework._momentum_enhanced_transform(0.5, volatility_adjustment=0.5)
        
        # Higher volatility adjustment should result in more extreme scores
        assert abs(high_vol - 50.0) > abs(low_vol - 50.0)
    
    # ==================== SCORING MODE TESTS ====================
    
    def test_auto_detect_mode(self):
        """Test automatic detection mode."""
        framework = UnifiedScoringFramework(ScoringConfig(mode=ScoringMode.AUTO_DETECT))
        
        # Sophisticated method should use traditional approach
        obv_score = framework.transform_score(1.0, 'obv_sigmoid')
        expected_obv = framework._obv_sigmoid_transform(1.0)
        assert abs(obv_score - expected_obv) < 0.1
        
        # Linear method should use enhanced approach
        rsi_score = framework.transform_score(80.0, 'rsi_score')
        assert rsi_score < 40.0  # Should show enhanced exponential behavior
    
    def test_traditional_mode(self):
        """Test traditional mode."""
        framework = UnifiedScoringFramework(ScoringConfig(mode=ScoringMode.TRADITIONAL))
        
        # Should use traditional methods when available
        obv_score = framework.transform_score(1.0, 'obv_sigmoid')
        expected_obv = framework._obv_sigmoid_transform(1.0)
        assert abs(obv_score - expected_obv) < 0.1
        
        # Should fallback to enhanced for unknown traditional methods
        rsi_score = framework.transform_score(80.0, 'rsi_unknown')
        assert 0 <= rsi_score <= 100
    
    def test_enhanced_linear_mode(self):
        """Test enhanced linear mode."""
        framework = UnifiedScoringFramework(ScoringConfig(mode=ScoringMode.ENHANCED_LINEAR))
        
        # Should use enhanced methods for all inputs
        rsi_score = framework.transform_score(80.0, 'rsi_score')
        assert rsi_score < 40.0  # Should show enhanced exponential behavior
        
        # Should use enhanced even for sophisticated method names
        obv_score = framework.transform_score(1.0, 'obv_sigmoid')
        assert 0 <= obv_score <= 100
    
    def test_hybrid_mode(self):
        """Test hybrid mode."""
        framework = UnifiedScoringFramework(ScoringConfig(mode=ScoringMode.HYBRID))
        
        # Sophisticated methods should use weighted combination
        obv_score = framework.transform_score(1.0, 'obv_sigmoid')
        traditional_score = framework._obv_sigmoid_transform(1.0)
        enhanced_score = framework._apply_enhanced_method(1.0, 'obv_sigmoid')
        expected_hybrid = 0.7 * traditional_score + 0.3 * enhanced_score
        assert abs(obv_score - expected_hybrid) < 0.1
        
        # Linear methods should use enhanced approach
        rsi_score = framework.transform_score(80.0, 'rsi_score')
        assert rsi_score < 40.0
    
    def test_linear_fallback_mode(self):
        """Test linear fallback mode."""
        framework = UnifiedScoringFramework(ScoringConfig(mode=ScoringMode.LINEAR_FALLBACK))
        
        # Should use simple linear scaling
        score = framework.transform_score(75.0, 'any_method')
        assert score == 75.0  # Should be clipped to input value
        
        # Should handle out-of-bounds values
        score_high = framework.transform_score(150.0, 'any_method')
        assert score_high == 100.0
        
        score_low = framework.transform_score(-50.0, 'any_method')
        assert score_low == 0.0
    
    # ==================== UTILITY TRANSFORMATION TESTS ====================
    
    def test_sigmoid_transform(self):
        """Test configurable sigmoid transformation."""
        # Test default parameters
        assert abs(self.framework._sigmoid_transform(50.0) - 50.0) < 0.1
        assert self.framework._sigmoid_transform(60.0) > 50.0
        assert self.framework._sigmoid_transform(40.0) < 50.0
        
        # Test custom parameters
        steep_score = self.framework._sigmoid_transform(55.0, center=50.0, steepness=1.0)
        gentle_score = self.framework._sigmoid_transform(55.0, center=50.0, steepness=0.01)
        
        # Steeper curve should result in more extreme scores
        assert abs(steep_score - 50.0) > abs(gentle_score - 50.0)
    
    def test_exponential_decay_transform(self):
        """Test exponential decay transformation."""
        # Test normal range
        assert self.framework._exponential_decay_transform(5.0, 10.0) == 25.0  # 50 * (5/10)
        
        # Test extreme range
        score_15 = self.framework._exponential_decay_transform(15.0, 10.0)
        score_20 = self.framework._exponential_decay_transform(20.0, 10.0)
        
        # Should show exponential decay behavior (scores decrease as distance increases)
        assert score_15 > score_20
        assert score_20 > 50.0  # Should be above baseline
        assert score_20 < score_15  # But should decay with distance
    
    def test_hyperbolic_transform(self):
        """Test hyperbolic tangent transformation."""
        # Test center point
        assert abs(self.framework._hyperbolic_transform(0.0) - 50.0) < 0.1
        
        # Test positive and negative values
        assert self.framework._hyperbolic_transform(1.0) > 50.0
        assert self.framework._hyperbolic_transform(-1.0) < 50.0
        
        # Test extreme values (should saturate)
        assert self.framework._hyperbolic_transform(10.0) > 95.0
        assert self.framework._hyperbolic_transform(-10.0) < 5.0
    
    # ==================== CACHING TESTS ====================
    
    def test_caching_enabled(self):
        """Test caching functionality."""
        config = ScoringConfig(enable_caching=True, cache_timeout=60)
        framework = UnifiedScoringFramework(config)
        
        # First call should compute and cache
        score1 = framework.transform_score(75.0, 'rsi_enhanced')
        
        # Second call should use cache
        score2 = framework.transform_score(75.0, 'rsi_enhanced')
        
        assert score1 == score2
        assert len(framework._cache) > 0
    
    def test_caching_disabled(self):
        """Test disabled caching."""
        config = ScoringConfig(enable_caching=False)
        framework = UnifiedScoringFramework(config)
        
        # Should not create cache
        framework.transform_score(75.0, 'rsi_enhanced')
        assert framework._cache is None
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        config = ScoringConfig(enable_caching=True, cache_timeout=60)
        framework = UnifiedScoringFramework(config)
        
        # Add many entries to trigger cleanup
        for i in range(1100):
            framework.transform_score(float(i), f'test_method_{i}')
        
        # Should have triggered cleanup
        assert len(framework._cache) <= 1000
    
    # ==================== ERROR HANDLING TESTS ====================
    
    def test_invalid_inputs(self):
        """Test error handling for invalid inputs."""
        # Test NaN values
        score = self.framework.transform_score(float('nan'), 'rsi_enhanced')
        assert score == 50.0  # Should return safe fallback
        
        # Test infinite values
        score = self.framework.transform_score(float('inf'), 'rsi_enhanced')
        assert score == 50.0  # Should return safe fallback
        
        # Test None values
        score = self.framework.transform_score(None, 'rsi_enhanced')
        assert score == 50.0  # Should return safe fallback
    
    def test_unknown_method_handling(self):
        """Test handling of unknown method names."""
        # Should not crash and return reasonable score
        score = self.framework.transform_score(75.0, 'completely_unknown_method')
        assert 0 <= score <= 100
    
    def test_transformation_error_handling(self):
        """Test error handling in transformation methods."""
        # Test with invalid parameters that might cause errors
        score = self.framework._rsi_enhanced_transform(
            75.0, overbought=30.0, oversold=70.0  # Invalid: overbought < oversold
        )
        assert score == 50.0  # Should return safe fallback
    
    # ==================== PERFORMANCE TESTS ====================
    
    def test_performance_stats(self):
        """Test performance statistics."""
        stats = self.framework.get_performance_stats()
        
        assert 'cache_size' in stats
        assert 'cache_hit_rate' in stats
        assert 'method_usage' in stats
        assert 'config' in stats
        
        # Config should contain expected values
        assert stats['config']['mode'] == 'auto_detect'
        assert stats['config']['caching_enabled'] is True
    
    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        config = ScoringConfig(enable_caching=True)
        framework = UnifiedScoringFramework(config)
        
        # Add some cached entries
        framework.transform_score(75.0, 'rsi_enhanced')
        framework.transform_score(80.0, 'rsi_enhanced')
        
        assert len(framework._cache) > 0
        
        # Clear cache
        framework.clear_cache()
        assert len(framework._cache) == 0
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_method_mapping(self):
        """Test method name mapping to enhanced transformations."""
        # Test RSI mapping
        rsi_score = self.framework._apply_enhanced_method(80.0, 'rsi_calculation')
        assert rsi_score < 40.0  # Should use RSI enhanced transform
        
        # Test volume mapping
        vol_score = self.framework._apply_enhanced_method(3.0, 'volume_analysis')
        assert vol_score > 70.0  # Should use volume enhanced transform
        
        # Test OIR mapping
        oir_score = self.framework._apply_enhanced_method(0.5, 'oir_calculation')
        assert oir_score > 60.0  # Should use OIR enhanced transform
    
    def test_bounds_checking(self):
        """Test that all transformations maintain proper bounds."""
        test_values = [-100, -10, -1, 0, 1, 10, 50, 100, 1000]
        test_methods = ['rsi_enhanced', 'volatility_enhanced', 'volume_enhanced', 
                       'oir_di_enhanced', 'momentum_enhanced']
        
        for value in test_values:
            for method in test_methods:
                score = self.framework.transform_score(value, method)
                assert 0 <= score <= 100, f"Score {score} out of bounds for {method} with value {value}"
    
    def test_consistency(self):
        """Test consistency of transformations."""
        # Same input should produce same output
        for _ in range(10):
            score1 = self.framework.transform_score(75.0, 'rsi_enhanced')
            score2 = self.framework.transform_score(75.0, 'rsi_enhanced')
            assert abs(score1 - score2) < 0.001
    
    def test_monotonicity_where_expected(self):
        """Test monotonicity properties where expected."""
        # For RSI in overbought region, higher RSI should give lower score
        rsi_75 = self.framework.transform_score(75.0, 'rsi_enhanced')
        rsi_85 = self.framework.transform_score(85.0, 'rsi_enhanced')
        rsi_95 = self.framework.transform_score(95.0, 'rsi_enhanced')
        
        assert rsi_75 > rsi_85 > rsi_95
        
        # For volume, higher volume should generally give higher score
        vol_1 = self.framework.transform_score(1.0, 'volume_enhanced')
        vol_2 = self.framework.transform_score(2.0, 'volume_enhanced')
        vol_3 = self.framework.transform_score(3.0, 'volume_enhanced')
        
        assert vol_1 < vol_2 < vol_3


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 