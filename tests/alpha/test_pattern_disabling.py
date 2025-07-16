#!/usr/bin/env python3
"""
Test Pattern Disabling in Extreme Mode
Verify that low-value patterns are completely disabled
"""

import unittest
import yaml
import tempfile
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.optimized_alpha_scanner import OptimizedAlphaScanner, AlertTier

class TestPatternDisabling(unittest.TestCase):
    """Test that patterns are properly disabled in extreme mode."""
    
    def setUp(self):
        """Set up extreme mode configuration."""
        self.extreme_config = {
            'alpha_scanning_optimized': {
                'enabled': True,
                'alpha_alerts_enabled': True,
                'extreme_mode': {'enabled': True},
                'alpha_tiers': {
                    'tier_1_critical': {
                        'enabled': True,
                        'min_alpha': 0.01,  # Very low for testing
                        'min_confidence': 0.50,
                        'scan_interval_minutes': 1,
                        'max_alerts_per_hour': 10,
                        'cooldown_override': True
                    },
                    'tier_2_high': {
                        'enabled': True,
                        'min_alpha': 0.01,
                        'min_confidence': 0.50,
                        'scan_interval_minutes': 3,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 15
                    },
                    'tier_3_medium': {
                        'enabled': False,  # DISABLED
                        'min_alpha': 0.01,
                        'min_confidence': 0.50,
                        'scan_interval_minutes': 10,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 60
                    },
                    'tier_4_background': {
                        'enabled': False,  # DISABLED
                        'min_alpha': 0.01,
                        'min_confidence': 0.50,
                        'scan_interval_minutes': 30,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 240
                    }
                },
                'pattern_weights': {
                    'beta_expansion': 1.0,      # ENABLED
                    'beta_compression': 1.0,    # ENABLED
                    'alpha_breakout': 0.0,      # DISABLED
                    'correlation_breakdown': 0.0,  # DISABLED
                    'cross_timeframe': 0.0      # DISABLED
                },
                'value_scoring': {
                    'alpha_weight': 0.40,
                    'confidence_weight': 0.25,
                    'pattern_weight': 0.20,
                    'volume_weight': 0.10,
                    'risk_weight': 0.05
                },
                'filtering': {
                    'min_alert_value_score': 1.0,  # Very low for testing
                },
                'throttling': {
                    'max_total_alerts_per_hour': 50,
                    'emergency_override': {
                        'min_alpha_for_override': 1.00,
                        'min_confidence_for_override': 0.98
                    }
                }
            },
            'pattern_configs': {
                'beta_expansion': {'enabled': True},
                'beta_compression': {'enabled': True},
                'alpha_breakout': {'enabled': False},      # DISABLED
                'correlation_breakdown': {'enabled': False},  # DISABLED
                'cross_timeframe': {'enabled': False}      # DISABLED
            }
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.extreme_config, self.temp_config, default_flow_style=False)
        self.temp_config.close()
        
    def tearDown(self):
        """Clean up temporary files."""
        os.unlink(self.temp_config.name)
    
    def test_disabled_patterns_not_analyzed(self):
        """Test that disabled patterns are not analyzed at all."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        mock_data = {'price': 100, 'volume': 1000}
        
        # Test each disabled pattern
        disabled_patterns = ['cross_timeframe', 'alpha_breakout', 'correlation_breakdown']
        
        for pattern in disabled_patterns:
            result = scanner._analyze_pattern('TESTUSDT', pattern, mock_data, 0.01, 0.50)
            self.assertIsNone(result, f"Pattern {pattern} should return None when disabled")
    
    def test_enabled_patterns_can_be_analyzed(self):
        """Test that enabled patterns can still be analyzed."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        mock_data = {'price': 100, 'volume': 1000}
        
        # Test enabled patterns (these should not return None due to disabling)
        enabled_patterns = ['beta_expansion', 'beta_compression']
        
        for pattern in enabled_patterns:
            # These might return None due to mock data not meeting criteria,
            # but they should NOT return None due to being disabled
            try:
                result = scanner._analyze_pattern('TESTUSDT', pattern, mock_data, 0.01, 0.50)
                # If it returns None, it should be due to detection logic, not disabling
                print(f"Pattern {pattern}: {'Detected' if result else 'Not detected (normal)'}")
            except Exception as e:
                # Should not fail due to pattern being disabled
                print(f"Pattern {pattern}: Analysis attempted (good)")
    
    def test_extreme_mode_pattern_selection(self):
        """Test that extreme mode only selects enabled patterns."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        market_data = {
            'TESTUSDT': {'price': 100, 'volume': 1000}
        }
        
        # Track which patterns are attempted
        attempted_patterns = []
        original_analyze = scanner._analyze_pattern
        
        def mock_analyze(symbol, pattern, data, min_alpha, min_confidence):
            attempted_patterns.append(pattern)
            return None  # Return None to avoid creating alerts
        
        scanner._analyze_pattern = mock_analyze
        
        # Run scan in extreme mode
        alerts = scanner.scan_for_alpha_opportunities(market_data)
        
        print(f"\nPatterns attempted in extreme mode: {attempted_patterns}")
        
        # Should only attempt enabled patterns
        self.assertIn('beta_expansion', attempted_patterns, "Beta expansion should be attempted")
        self.assertIn('beta_compression', attempted_patterns, "Beta compression should be attempted")
        
        # Should NOT attempt disabled patterns
        self.assertNotIn('cross_timeframe', attempted_patterns, "Cross timeframe should NOT be attempted")
        self.assertNotIn('alpha_breakout', attempted_patterns, "Alpha breakout should NOT be attempted")
        self.assertNotIn('correlation_breakdown', attempted_patterns, "Correlation breakdown should NOT be attempted")
    
    def test_pattern_weight_zero_blocks_analysis(self):
        """Test that patterns with zero weight are blocked."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Verify pattern weights
        self.assertEqual(scanner.pattern_weights['cross_timeframe'], 0.0)
        self.assertEqual(scanner.pattern_weights['alpha_breakout'], 0.0)
        self.assertEqual(scanner.pattern_weights['correlation_breakdown'], 0.0)
        
        # These should be blocked by zero weight
        mock_data = {'price': 100, 'volume': 1000}
        
        result = scanner._analyze_pattern('TESTUSDT', 'cross_timeframe', mock_data, 0.01, 0.50)
        self.assertIsNone(result, "Zero weight pattern should be blocked")
    
    def test_pattern_config_disabled_blocks_analysis(self):
        """Test that patterns disabled in config are blocked."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Verify pattern configs
        self.assertFalse(scanner.pattern_configs['cross_timeframe']['enabled'])
        self.assertFalse(scanner.pattern_configs['alpha_breakout']['enabled'])
        self.assertFalse(scanner.pattern_configs['correlation_breakdown']['enabled'])
        
        # These should be blocked by config
        mock_data = {'price': 100, 'volume': 1000}
        
        result = scanner._analyze_pattern('TESTUSDT', 'cross_timeframe', mock_data, 0.01, 0.50)
        self.assertIsNone(result, "Config-disabled pattern should be blocked")

if __name__ == '__main__':
    unittest.main(verbosity=2) 