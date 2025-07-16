#!/usr/bin/env python3
"""
Test Enhanced Trading Insights
Demonstrate the improved, human-readable trading insights
"""

import unittest
import yaml
import tempfile
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.optimized_alpha_scanner import OptimizedAlphaScanner

class TestEnhancedInsights(unittest.TestCase):
    """Test enhanced trading insights functionality."""
    
    def setUp(self):
        """Set up test configuration."""
        self.config = {
            'alpha_scanning_optimized': {
                'enabled': True,
                'alpha_alerts_enabled': True,
                'extreme_mode': {'enabled': False},  # Use normal mode for testing all patterns
                'alpha_tiers': {
                    'tier_1_critical': {
                        'enabled': True,
                        'min_alpha': 0.10,  # Lower threshold for testing
                        'min_confidence': 0.70,
                        'scan_interval_minutes': 1,
                        'max_alerts_per_hour': 10,
                        'cooldown_override': True
                    },
                    'tier_2_high': {
                        'enabled': True,
                        'min_alpha': 0.05,
                        'min_confidence': 0.60,
                        'scan_interval_minutes': 3,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 15
                    },
                    'tier_3_medium': {
                        'enabled': True,
                        'min_alpha': 0.03,
                        'min_confidence': 0.50,
                        'scan_interval_minutes': 10,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 60
                    },
                    'tier_4_background': {
                        'enabled': True,
                        'min_alpha': 0.01,
                        'min_confidence': 0.40,
                        'scan_interval_minutes': 30,
                        'max_alerts_per_hour': 10,
                        'cooldown_minutes': 240
                    }
                },
                'pattern_weights': {
                    'beta_expansion': 1.0,
                    'beta_compression': 1.0,
                    'alpha_breakout': 0.6,
                    'correlation_breakdown': 0.4,
                    'cross_timeframe': 0.2
                },
                'value_scoring': {
                    'alpha_weight': 0.40,
                    'confidence_weight': 0.25,
                    'pattern_weight': 0.20,
                    'volume_weight': 0.10,
                    'risk_weight': 0.05
                },
                'filtering': {
                    'min_alert_value_score': 10.0,  # Lower for testing
                },
                'throttling': {
                    'max_total_alerts_per_hour': 50,
                    'emergency_override': {
                        'min_alpha_for_override': 1.00,
                        'min_confidence_for_override': 0.98
                    }
                }
            },
            'pattern_configs': {}
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.config, self.temp_config, default_flow_style=False)
        self.temp_config.close()
        
    def tearDown(self):
        """Clean up temporary files."""
        os.unlink(self.temp_config.name)
    
    def test_beta_expansion_insight(self):
        """Test beta expansion trading insight generation."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Test beta expansion insight
        insight = scanner._generate_beta_expansion_insight(
            symbol="ETHUSDT",
            alpha=1.25,  # 125% alpha
            confidence=0.96,  # 96% confidence
            data={
                'beta_change': 0.75,  # 75% volatility increase
                'volume_spike': 4.2   # 4.2x volume
            }
        )
        
        print("\n" + "="*80)
        print("BETA EXPANSION INSIGHT EXAMPLE:")
        print("="*80)
        print(insight)
        print("="*80)
        
        # Verify key components are present
        self.assertIn("🚀", insight)  # Emoji for visual appeal
        self.assertIn("ETHUSDT", insight)
        self.assertIn("125%", insight)  # Alpha percentage
        self.assertIn("exceptional", insight)  # Magnitude description
        self.assertIn("TRADING IMPLICATIONS", insight)  # Trading section
        self.assertIn("STRATEGY", insight)  # Strategy recommendations
        self.assertIn("ENTRY", insight)  # Entry conditions
        self.assertIn("STOPS", insight)  # Stop loss guidance
        self.assertIn("TARGET", insight)  # Target guidance
    
    def test_beta_compression_insight(self):
        """Test beta compression trading insight generation."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        insight = scanner._generate_beta_compression_insight(
            symbol="ADAUSDT",
            alpha=0.85,  # 85% alpha
            confidence=0.92,  # 92% confidence
            data={
                'correlation_drop': 0.45,  # 45% correlation drop
                'independence_score': 0.78  # 78% independence
            }
        )
        
        print("\n" + "="*80)
        print("BETA COMPRESSION INSIGHT EXAMPLE:")
        print("="*80)
        print(insight)
        print("="*80)
        
        # Verify key components
        self.assertIn("🎯", insight)
        self.assertIn("ADAUSDT", insight)
        self.assertIn("85%", insight)
        self.assertIn("independence", insight)
        self.assertIn("MARKET CONTEXT", insight)
        self.assertIn("TRADING STRATEGY", insight)
    
    def test_alpha_breakout_insight(self):
        """Test alpha breakout trading insight generation."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        insight = scanner._generate_alpha_breakout_insight(
            symbol="SOLUSDT",
            alpha=0.35,  # 35% alpha
            confidence=0.88,  # 88% confidence
            data={
                'trend_strength': 0.82,
                'breakout_level': 'resistance'
            }
        )
        
        print("\n" + "="*80)
        print("ALPHA BREAKOUT INSIGHT EXAMPLE:")
        print("="*80)
        print(insight)
        print("="*80)
        
        # Verify key components
        self.assertIn("⚡", insight)
        self.assertIn("SOLUSDT", insight)
        self.assertIn("35%", insight)
        self.assertIn("breaking out", insight)
        self.assertIn("BREAKOUT ANALYSIS", insight)
        self.assertIn("RECOMMENDED APPROACH", insight)
    
    def test_correlation_breakdown_insight(self):
        """Test correlation breakdown trading insight generation."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        insight = scanner._generate_correlation_breakdown_insight(
            symbol="DOTUSDT",
            alpha=0.18,  # 18% alpha
            confidence=0.82,  # 82% confidence
            data={
                'breakdown_magnitude': 0.38,
                'historical_context': 'elevated'
            }
        )
        
        print("\n" + "="*80)
        print("CORRELATION BREAKDOWN INSIGHT EXAMPLE:")
        print("="*80)
        print(insight)
        print("="*80)
        
        # Verify key components
        self.assertIn("🔄", insight)
        self.assertIn("DOTUSDT", insight)
        self.assertIn("18%", insight)
        self.assertIn("correlation breakdown", insight)
        self.assertIn("MARKET IMPLICATIONS", insight)
        self.assertIn("TRADING APPROACH", insight)
    
    def test_cross_timeframe_insight(self):
        """Test cross timeframe trading insight generation."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        insight = scanner._generate_cross_timeframe_insight(
            symbol="LINKUSDT",
            alpha=0.12,  # 12% alpha
            confidence=0.78,  # 78% confidence
            data={
                'timeframe_alignment': 0.85,
                'consensus_strength': 0.72
            }
        )
        
        print("\n" + "="*80)
        print("CROSS TIMEFRAME INSIGHT EXAMPLE:")
        print("="*80)
        print(insight)
        print("="*80)
        
        # Verify key components
        self.assertIn("📊", insight)
        self.assertIn("LINKUSDT", insight)
        self.assertIn("12%", insight)
        self.assertIn("timeframe alignment", insight)
        self.assertIn("CONFLUENCE ANALYSIS", insight)
        self.assertIn("STRATEGY", insight)
    
    def test_full_alert_generation(self):
        """Test full alert generation with enhanced insights."""
        scanner = OptimizedAlphaScanner(self.temp_config.name)
        
        # Mock market data
        market_data = {
            'ETHUSDT': {'price': 2000, 'volume': 1000000},
            'ADAUSDT': {'price': 0.5, 'volume': 500000}
        }
        
        # Generate alerts
        alerts = scanner.scan_for_alpha_opportunities(market_data)
        
        print("\n" + "="*80)
        print("FULL ALERT EXAMPLES:")
        print("="*80)
        
        for i, alert in enumerate(alerts[:3]):  # Show first 3 alerts
            print(f"\nALERT {i+1}: {alert.symbol} - {alert.pattern_type.upper()}")
            print(f"Alpha: {alert.alpha_magnitude:.1%} | Confidence: {alert.confidence:.1%}")
            print(f"Tier: {alert.tier.value} | Value Score: {alert.value_score:.1f}")
            print("\nTRADING INSIGHT:")
            print("-" * 40)
            print(alert.trading_insight)
            print("-" * 40)
        
        # Verify alerts were generated
        self.assertGreater(len(alerts), 0, "Should generate at least one alert")
        
        # Verify all alerts have enhanced insights
        for alert in alerts:
            self.assertIsNotNone(alert.trading_insight)
            self.assertGreater(len(alert.trading_insight), 100)  # Should be substantial
            self.assertIn(alert.symbol, alert.trading_insight)  # Should mention the symbol
            self.assertIn("%", alert.trading_insight)  # Should include percentages

if __name__ == '__main__':
    # Run tests with verbose output to see the insights
    unittest.main(verbosity=2) 