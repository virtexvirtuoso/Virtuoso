import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock
from src.indicators.base_indicator import BaseIndicator
from src.core.logger import Logger

class TestIndicatorTransformations(BaseIndicator):
    """Test implementation of BaseIndicator for testing transformation methods."""
    
    def __init__(self, config=None, logger=None):
        if config is None:
            config = {
                'timeframes': {
                    'base': {'interval': '1', 'validation': {'min_candles': 100}, 'weight': 0.5},
                    'ltf': {'interval': '5', 'validation': {'min_candles': 50}, 'weight': 0.15},
                    'mtf': {'interval': '30', 'validation': {'min_candles': 50}, 'weight': 0.20},
                    'htf': {'interval': '240', 'validation': {'min_candles': 20}, 'weight': 0.15}
                }
            }
        
        self.indicator_type = 'technical'
        self.component_weights = {'test_component': 1.0}
        
        super().__init__(config, logger)
        
    async def calculate(self, market_data):
        return {'score': 50.0, 'components': {}, 'signals': {}, 'metadata': {}}

class TestBaseIndicatorTransformations:
    """Test suite for BaseIndicator transformation methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.indicator = TestIndicatorTransformations()
    
    # ==================== SIGMOID TRANSFORM TESTS ====================
    
    def test_sigmoid_transform_basic(self):
        """Test basic sigmoid transformation functionality."""
        # Test center point
        result = self.indicator._sigmoid_transform(50.0, center=50.0, steepness=0.1)
        assert abs(result - 50.0) < 0.1  # Should be close to center
        
        # Test values above center
        result = self.indicator._sigmoid_transform(60.0, center=50.0, steepness=0.1)
        assert result > 50.0  # Should be above center
        
        # Test values below center
        result = self.indicator._sigmoid_transform(40.0, center=50.0, steepness=0.1)
        assert result < 50.0  # Should be below center
    
    def test_sigmoid_transform_bounds(self):
        """Test sigmoid transformation stays within bounds."""
        # Test extreme values
        result = self.indicator._sigmoid_transform(1000.0, center=50.0, steepness=0.1)
        assert 0.0 <= result <= 100.0
        
        result = self.indicator._sigmoid_transform(-1000.0, center=50.0, steepness=0.1)
        assert 0.0 <= result <= 100.0
    
    def test_sigmoid_transform_steepness(self):
        """Test sigmoid transformation steepness parameter."""
        # Higher steepness should create sharper transitions
        gentle = self.indicator._sigmoid_transform(55.0, center=50.0, steepness=0.05)
        steep = self.indicator._sigmoid_transform(55.0, center=50.0, steepness=0.2)
        
        assert steep > gentle  # Steeper curve should have higher value for same input
    
    def test_sigmoid_transform_error_handling(self):
        """Test sigmoid transformation error handling."""
        # Test with invalid inputs
        result = self.indicator._sigmoid_transform(np.nan, center=50.0, steepness=0.1)
        assert result == 50.0  # Should return safe fallback
        
        result = self.indicator._sigmoid_transform(np.inf, center=50.0, steepness=0.1)
        assert result == 50.0  # Should return safe fallback
    
    # ==================== EXTREME VALUE TRANSFORM TESTS ====================
    
    def test_extreme_value_transform_basic(self):
        """Test basic extreme value transformation functionality."""
        # Test normal range (below threshold)
        result = self.indicator._extreme_value_transform(30.0, threshold=50.0, max_extreme=100.0)
        assert result == 30.0  # Should be linear scaling: 50 * (30/50) = 30
        
        # Test extreme range (above threshold)
        result = self.indicator._extreme_value_transform(70.0, threshold=50.0, max_extreme=100.0)
        assert result > 50.0  # Should be above threshold with exponential scaling
        
        # Test at threshold
        result = self.indicator._extreme_value_transform(50.0, threshold=50.0, max_extreme=100.0)
        assert result == 50.0  # Should be exactly at threshold
    
    def test_extreme_value_transform_exponential_behavior(self):
        """Test exponential behavior in extreme range."""
        # Test increasing extreme values
        result_70 = self.indicator._extreme_value_transform(70.0, threshold=50.0, max_extreme=100.0)
        result_80 = self.indicator._extreme_value_transform(80.0, threshold=50.0, max_extreme=100.0)
        result_90 = self.indicator._extreme_value_transform(90.0, threshold=50.0, max_extreme=100.0)
        
        # Should show exponential increase
        assert result_70 < result_80 < result_90
        
        # Differences should decrease (exponential curve flattens)
        diff_70_80 = result_80 - result_70
        diff_80_90 = result_90 - result_80
        assert diff_70_80 > diff_80_90  # Exponential curve should flatten
    
    def test_extreme_value_transform_bounds(self):
        """Test extreme value transformation stays within bounds."""
        # Test extreme values
        result = self.indicator._extreme_value_transform(1000.0, threshold=50.0, max_extreme=100.0)
        assert 0.0 <= result <= 100.0
        
        result = self.indicator._extreme_value_transform(0.0, threshold=50.0, max_extreme=100.0)
        assert 0.0 <= result <= 100.0
    
    def test_extreme_value_transform_error_handling(self):
        """Test extreme value transformation error handling."""
        # Test with invalid threshold
        result = self.indicator._extreme_value_transform(30.0, threshold=0.0, max_extreme=100.0)
        assert result == 50.0  # Should handle zero threshold
        
        # Test with invalid max_extreme
        result = self.indicator._extreme_value_transform(70.0, threshold=50.0, max_extreme=50.0)
        assert result == 50.0  # Should handle max_extreme <= threshold
    
    # ==================== HYPERBOLIC TRANSFORM TESTS ====================
    
    def test_hyperbolic_transform_basic(self):
        """Test basic hyperbolic transformation functionality."""
        # Test zero input
        result = self.indicator._hyperbolic_transform(0.0, sensitivity=1.0)
        assert abs(result - 50.0) < 0.1  # Should be close to center
        
        # Test positive input
        result = self.indicator._hyperbolic_transform(1.0, sensitivity=1.0)
        assert result > 50.0  # Should be above center
        
        # Test negative input
        result = self.indicator._hyperbolic_transform(-1.0, sensitivity=1.0)
        assert result < 50.0  # Should be below center
    
    def test_hyperbolic_transform_bounds(self):
        """Test hyperbolic transformation stays within bounds."""
        # Test extreme values
        result = self.indicator._hyperbolic_transform(1000.0, sensitivity=1.0)
        assert 0.0 <= result <= 100.0
        
        result = self.indicator._hyperbolic_transform(-1000.0, sensitivity=1.0)
        assert 0.0 <= result <= 100.0
    
    def test_hyperbolic_transform_sensitivity(self):
        """Test hyperbolic transformation sensitivity parameter."""
        # Higher sensitivity should create more responsive curves
        low_sens = self.indicator._hyperbolic_transform(0.5, sensitivity=0.5)
        high_sens = self.indicator._hyperbolic_transform(0.5, sensitivity=2.0)
        
        assert high_sens > low_sens  # Higher sensitivity should give higher value
    
    def test_hyperbolic_transform_symmetry(self):
        """Test hyperbolic transformation symmetry."""
        # Should be symmetric around center
        positive = self.indicator._hyperbolic_transform(1.0, sensitivity=1.0)
        negative = self.indicator._hyperbolic_transform(-1.0, sensitivity=1.0)
        
        assert abs((positive - 50.0) - (50.0 - negative)) < 0.1  # Should be symmetric
    
    # ==================== EXPONENTIAL DECAY TRANSFORM TESTS ====================
    
    def test_exponential_decay_transform_basic(self):
        """Test basic exponential decay transformation functionality."""
        # Test at threshold
        result = self.indicator._exponential_decay_transform(50.0, threshold=50.0, half_life=10.0)
        assert abs(result - 100.0) < 0.1  # Should be maximum at threshold
        
        # Test at half-life distance
        result = self.indicator._exponential_decay_transform(60.0, threshold=50.0, half_life=10.0)
        assert abs(result - 50.0) < 1.0  # Should be ~50% at half-life distance
        
        # Test further away
        result = self.indicator._exponential_decay_transform(70.0, threshold=50.0, half_life=10.0)
        assert result < 50.0  # Should be less than half-life value
    
    def test_exponential_decay_transform_symmetry(self):
        """Test exponential decay transformation symmetry."""
        # Should be symmetric around threshold
        above = self.indicator._exponential_decay_transform(60.0, threshold=50.0, half_life=10.0)
        below = self.indicator._exponential_decay_transform(40.0, threshold=50.0, half_life=10.0)
        
        assert abs(above - below) < 0.1  # Should be symmetric
    
    def test_exponential_decay_transform_bounds(self):
        """Test exponential decay transformation stays within bounds."""
        # Test extreme distances
        result = self.indicator._exponential_decay_transform(1000.0, threshold=50.0, half_life=10.0)
        assert 0.0 <= result <= 100.0
        
        result = self.indicator._exponential_decay_transform(-1000.0, threshold=50.0, half_life=10.0)
        assert 0.0 <= result <= 100.0
    
    def test_exponential_decay_transform_error_handling(self):
        """Test exponential decay transformation error handling."""
        # Test with invalid half_life
        result = self.indicator._exponential_decay_transform(60.0, threshold=50.0, half_life=0.0)
        assert result == 50.0  # Should return safe fallback
        
        result = self.indicator._exponential_decay_transform(60.0, threshold=50.0, half_life=-10.0)
        assert result == 50.0  # Should return safe fallback
    
    # ==================== ENHANCED RSI TRANSFORM TESTS ====================
    
    def test_enhanced_rsi_transform_basic(self):
        """Test basic enhanced RSI transformation functionality."""
        # Test neutral zone
        result = self.indicator._enhanced_rsi_transform(50.0, overbought=70.0, oversold=30.0)
        assert abs(result - 50.0) < 5.0  # Should be close to neutral
        
        # Test overbought zone
        result = self.indicator._enhanced_rsi_transform(80.0, overbought=70.0, oversold=30.0)
        assert result < 50.0  # Should be bearish (below 50)
        
        # Test oversold zone
        result = self.indicator._enhanced_rsi_transform(20.0, overbought=70.0, oversold=30.0)
        assert result > 50.0  # Should be bullish (above 50)
    
    def test_enhanced_rsi_transform_extreme_differentiation(self):
        """Test that enhanced RSI properly differentiates extreme values."""
        # Test different overbought levels
        rsi_75 = self.indicator._enhanced_rsi_transform(75.0, overbought=70.0, oversold=30.0)
        rsi_85 = self.indicator._enhanced_rsi_transform(85.0, overbought=70.0, oversold=30.0)
        rsi_95 = self.indicator._enhanced_rsi_transform(95.0, overbought=70.0, oversold=30.0)
        
        # Should show proper differentiation (more extreme = lower score)
        assert rsi_75 > rsi_85 > rsi_95
        
        # Test different oversold levels
        rsi_25 = self.indicator._enhanced_rsi_transform(25.0, overbought=70.0, oversold=30.0)
        rsi_15 = self.indicator._enhanced_rsi_transform(15.0, overbought=70.0, oversold=30.0)
        rsi_5 = self.indicator._enhanced_rsi_transform(5.0, overbought=70.0, oversold=30.0)
        
        # Should show proper differentiation (more extreme = higher score)
        assert rsi_25 < rsi_15 < rsi_5
    
    def test_enhanced_rsi_transform_bounds(self):
        """Test enhanced RSI transformation stays within bounds."""
        # Test extreme RSI values
        result = self.indicator._enhanced_rsi_transform(100.0, overbought=70.0, oversold=30.0)
        assert 0.0 <= result <= 100.0
        
        result = self.indicator._enhanced_rsi_transform(0.0, overbought=70.0, oversold=30.0)
        assert 0.0 <= result <= 100.0
    
    def test_enhanced_rsi_transform_thresholds(self):
        """Test enhanced RSI transformation with different thresholds."""
        # Test with different overbought/oversold levels
        result_70_30 = self.indicator._enhanced_rsi_transform(75.0, overbought=70.0, oversold=30.0)
        result_80_20 = self.indicator._enhanced_rsi_transform(75.0, overbought=80.0, oversold=20.0)
        
        # With higher overbought threshold, RSI 75 should be less bearish
        assert result_80_20 > result_70_30
    
    def test_enhanced_rsi_transform_error_handling(self):
        """Test enhanced RSI transformation error handling."""
        # Test with invalid thresholds
        result = self.indicator._enhanced_rsi_transform(50.0, overbought=30.0, oversold=70.0)
        assert result == 50.0  # Should return safe fallback for invalid thresholds
        
        # Test with NaN input
        result = self.indicator._enhanced_rsi_transform(np.nan, overbought=70.0, oversold=30.0)
        assert result == 50.0  # Should return safe fallback
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_transformation_methods_integration(self):
        """Test that transformation methods work together properly."""
        # Test that all methods return valid scores
        sigmoid_score = self.indicator._sigmoid_transform(60.0)
        extreme_score = self.indicator._extreme_value_transform(70.0, 50.0, 100.0)
        hyperbolic_score = self.indicator._hyperbolic_transform(0.5)
        decay_score = self.indicator._exponential_decay_transform(60.0, 50.0)
        rsi_score = self.indicator._enhanced_rsi_transform(80.0)
        
        # All should be within valid bounds
        for score in [sigmoid_score, extreme_score, hyperbolic_score, decay_score, rsi_score]:
            assert 0.0 <= score <= 100.0
            assert not np.isnan(score)
            assert not np.isinf(score)
    
    def test_transformation_methods_consistency(self):
        """Test consistency of transformation methods."""
        # Test that similar inputs produce similar outputs
        input_values = [45.0, 50.0, 55.0]
        sigmoid_scores = [self.indicator._sigmoid_transform(val) for val in input_values]
        
        # Should show monotonic behavior
        assert sigmoid_scores[0] < sigmoid_scores[1] < sigmoid_scores[2]
    
    def test_transformation_methods_performance(self):
        """Test performance of transformation methods with arrays."""
        # Test with array-like inputs
        test_values = np.linspace(0, 100, 1000)
        
        # All methods should handle array inputs gracefully
        for value in test_values[::100]:  # Test every 100th value
            sigmoid_score = self.indicator._sigmoid_transform(float(value))
            extreme_score = self.indicator._extreme_value_transform(float(value), 50.0, 100.0)
            hyperbolic_score = self.indicator._hyperbolic_transform(float(value - 50) / 50)
            decay_score = self.indicator._exponential_decay_transform(float(value), 50.0)
            rsi_score = self.indicator._enhanced_rsi_transform(float(value))
            
            # All should be valid
            for score in [sigmoid_score, extreme_score, hyperbolic_score, decay_score, rsi_score]:
                assert 0.0 <= score <= 100.0
                assert not np.isnan(score)
                assert not np.isinf(score) 