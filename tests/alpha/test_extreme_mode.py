#!/usr/bin/env python3
"""
Test Extreme Mode Alpha Scanner
Verify that extreme mode settings are working correctly
"""

import unittest
import yaml
import tempfile
import os
from unittest.mock import Mock, patch
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.optimized_alpha_scanner import OptimizedAlphaScanner, AlertTier

class TestExtremeMode(unittest.TestCase):
    """Test extreme mode functionality."""
    
    def setUp(self):
        """Set up test configuration."""
        self.extreme_config = {
            'alpha_scanning_optimized': {
                'enabled': True,
                'alpha_alerts_enabled': True,
                'extreme_mode': {
                    'enabled': True
                },
                'alpha_tiers': {
                    'tier_1_critical': {
                        'enabled': True,
                        'min_alpha': 1.00,  # 100%+ alpha
                        'min_confidence': 0.98,  # 98% confidence
                        'scan_interval_minutes': 0.5,
                        'max_alerts_per_hour': 1,
                        'cooldown_override': True
                    },
                    'tier_2_high': {
                        'enabled': True,
                        'min_alpha': 0.50,  # 50%+ alpha
                        'min_confidence': 0.95,  # 95% confidence
                        'scan_interval_minutes': 2,
                        'max_alerts_per_hour': 2,
                        'cooldown_minutes': 30
                    },
                    'tier_3_medium': {
                        'enabled': False,  # DISABLED
                        'min_alpha': 0.08,
                        'min_confidence': 0.85,
                        'scan_interval_minutes': 10,
                        'max_alerts_per_hour': 2,
                        'cooldown_minutes': 60
                    },
                    'tier_4_background': {
                        'enabled': False,  # DISABLED
                        'min_alpha': 0.05,
                        'min_confidence': 0.80,
                        'scan_interval_minutes': 30,
                        'max_alerts_per_hour': 1,
                        'cooldown_minutes': 240
                    }
                },
                'pattern_weights': {
                    'beta_expansion': 1.0,
                    'beta_compression': 1.0,
                    'alpha_breakout': 0.0,  # DISABLED
                    'correlation_breakdown': 0.0,  # DISABLED
                    'cross_timeframe': 0.0  # DISABLED
                },
                'value_scoring': {
                    'alpha_weight': 0.40,
                    'confidence_weight': 0.25,
                    'pattern_weight': 0.20,
                    'volume_weight': 0.10,
                    'risk_weight': 0.05
                },
                'filtering': {
                    'min_alert_value_score': 100.0,  # 4x higher threshold
                    'volume_confirmation': {
                        'tier_1_required': True,
                        'tier_2_required': True,
                        'min_volume_multiplier': 5.0  # 5x volume spike
                    }
                },
                'throttling': {
                    'max_total_alerts_per_hour': 3,
                    'max_total_alerts_per_day': 10,
                    'max_alerts_per_symbol_per_day': 1
                }
            },
            'pattern_configs': {}
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.extreme_config, self.temp_config, default_flow_style=False)
        self.temp_config.close()
        
    def tearDown(self):
        """Clean up temporary files."""
        os.unlink(self.temp_config.name)
    
    def test_extreme_mode_initialization(self):
        """Test that extreme mode initializes correctly."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Check that extreme mode is enabled
        self.assertTrue(scanner.alpha_config.get('extreme_mode', {}).get('enabled', False))
        
        # Check tier thresholds
        self.assertEqual(scanner.tiers[AlertTier.CRITICAL]['min_alpha'], 1.00)
        self.assertEqual(scanner.tiers[AlertTier.HIGH]['min_alpha'], 0.50)
        
        # Check disabled patterns
        self.assertEqual(scanner.pattern_weights['alpha_breakout'], 0.0)
        self.assertEqual(scanner.pattern_weights['correlation_breakdown'], 0.0)
        self.assertEqual(scanner.pattern_weights['cross_timeframe'], 0.0)
    
    def test_master_toggle_disabled(self):
        """Test that master toggle disables all alerts."""
        # Disable alpha alerts
        config = self.extreme_config.copy()
        config['alpha_scanning_optimized']['alpha_alerts_enabled'] = False
        
        temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config, temp_config, default_flow_style=False)
        temp_config.close()
        
        try:
            scanner = OptimizedAlphaScanner(temp_config.name)
            
            # Mock market data
            market_data = {
                'ETHUSDT': {'price': 2000, 'volume': 1000000},
                'ADAUSDT': {'price': 0.5, 'volume': 500000}
            }
            
            # Should return empty list when disabled
            alerts = scanner.scan_for_alpha_opportunities(market_data)
            self.assertEqual(len(alerts), 0)
            
        finally:
            os.unlink(temp_config.name)
    
    def test_disabled_tiers_skipped(self):
        """Test that disabled tiers are skipped in extreme mode."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        market_data = {
            'ETHUSDT': {'price': 2000, 'volume': 1000000},
            'ADAUSDT': {'price': 0.5, 'volume': 500000}
        }
        
        # Mock the _scan_tier method to track which tiers are called
        called_tiers = []
        original_scan_tier = scanner._scan_tier
        
        def mock_scan_tier(tier, market_data, extreme_mode=False):
            called_tiers.append(tier)
            return []
        
        scanner._scan_tier = mock_scan_tier
        
        # Run scan
        scanner.scan_for_alpha_opportunities(market_data)
        
        # Should only call enabled tiers (Tier 1 and 2)
        self.assertIn(AlertTier.CRITICAL, called_tiers)
        self.assertIn(AlertTier.HIGH, called_tiers)
        self.assertNotIn(AlertTier.MEDIUM, called_tiers)
        self.assertNotIn(AlertTier.BACKGROUND, called_tiers)
    
    def test_extreme_mode_pattern_filtering(self):
        """Test that only beta patterns are used in extreme mode."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        market_data = {
            'ETHUSDT': {'price': 2000, 'volume': 1000000}
        }
        
        # Test tier scanning with extreme mode
        patterns_used = []
        
        def mock_analyze_pattern(symbol, pattern, data, min_alpha, min_confidence):
            patterns_used.append(pattern)
            return None
        
        scanner._analyze_pattern = mock_analyze_pattern
        
        # Scan tier 1 (should only use beta patterns)
        scanner._scan_tier(AlertTier.CRITICAL, market_data, extreme_mode=True)
        
        # Should only use beta expansion and compression
        self.assertIn('beta_expansion', patterns_used)
        self.assertIn('beta_compression', patterns_used)
        self.assertNotIn('alpha_breakout', patterns_used)
        self.assertNotIn('correlation_breakdown', patterns_used)
        self.assertNotIn('cross_timeframe', patterns_used)
    
    def test_extreme_thresholds(self):
        """Test that extreme thresholds are properly applied."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Check filtering thresholds
        self.assertEqual(scanner.alpha_config['filtering']['min_alert_value_score'], 100.0)
        self.assertEqual(scanner.alpha_config['filtering']['volume_confirmation']['min_volume_multiplier'], 5.0)
        
        # Check throttling limits
        self.assertEqual(scanner.alpha_config['throttling']['max_total_alerts_per_hour'], 3)
        self.assertEqual(scanner.alpha_config['throttling']['max_total_alerts_per_day'], 10)
        self.assertEqual(scanner.alpha_config['throttling']['max_alerts_per_symbol_per_day'], 1)

if __name__ == '__main__':
    unittest.main() 