#!/usr/bin/env python3
"""
Tests for Optimized Alpha Scanner
Comprehensive testing for production deployment
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.monitoring.optimized_alpha_scanner import (
    OptimizedAlphaScanner, AlphaAlert, AlertTier, PatternPriority
)
from src.monitoring.alpha_integration_manager import (
    AlphaIntegrationManager, ScannerMode, ScannerPerformanceMetrics
)

class TestOptimizedAlphaScanner:
    """Test suite for OptimizedAlphaScanner."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'alpha_scanning_optimized': {
                'alpha_tiers': {
                    'tier_1_critical': {
                        'min_alpha': 0.50,
                        'min_confidence': 0.95,
                        'scan_interval_minutes': 1,
                        'max_alerts_per_hour': 2,
                        'cooldown_override': True
                    },
                    'tier_2_high': {
                        'min_alpha': 0.15,
                        'min_confidence': 0.90,
                        'scan_interval_minutes': 3,
                        'max_alerts_per_hour': 3,
                        'cooldown_minutes': 15
                    },
                    'tier_3_medium': {
                        'min_alpha': 0.08,
                        'min_confidence': 0.85,
                        'scan_interval_minutes': 10,
                        'max_alerts_per_hour': 2,
                        'cooldown_minutes': 60
                    },
                    'tier_4_background': {
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
                    'min_alert_value_score': 25.0
                },
                'throttling': {
                    'max_total_alerts_per_hour': 8,
                    'emergency_override': {
                        'min_alpha_for_override': 1.00,
                        'min_confidence_for_override': 0.98
                    }
                }
            },
            'pattern_configs': {}
        }
    
    @pytest.fixture
    def scanner(self, mock_config, tmp_path):
        """Create scanner instance for testing."""
        # Create temporary config file
        config_file = tmp_path / "test_config.yaml"
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(mock_config, f)
        
        return OptimizedAlphaScanner(str(config_file))
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing."""
        return {
            'ETHUSDT': {
                'beta_change': 0.6,
                'beta': 1.4,
                'volume_spike': True,
                'correlation_reduction': 0.4,
                'independence_factor': 0.7,
                'trend_strength': 0.8,
                'alpha_trend': 0.1
            },
            'SOLUSDT': {
                'beta_change': 1.2,
                'beta': 2.1,
                'volume_spike': True,
                'correlation_reduction': 0.6,
                'independence_factor': 0.8
            },
            'BTCUSDT': {
                'beta_change': 0.0,
                'beta': 1.0,
                'volume_spike': False
            }
        }
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly."""
        assert scanner is not None
        assert len(scanner.tiers) == 4
        assert AlertTier.CRITICAL in scanner.tiers
        assert scanner.pattern_weights['beta_expansion'] == 1.0
    
    def test_tier_determination(self, scanner):
        """Test alpha tier determination logic."""
        assert scanner._determine_tier(0.60) == AlertTier.CRITICAL
        assert scanner._determine_tier(0.25) == AlertTier.HIGH
        assert scanner._determine_tier(0.10) == AlertTier.MEDIUM
        assert scanner._determine_tier(0.06) == AlertTier.BACKGROUND
    
    def test_value_score_calculation(self, scanner):
        """Test alert value score calculation."""
        score = scanner._calculate_value_score(
            alpha=0.50,
            confidence=0.95,
            pattern='beta_expansion',
            volume_confirmed=True
        )
        
        assert score > 0
        assert score <= 100
        
        # Higher alpha should give higher score
        higher_score = scanner._calculate_value_score(
            alpha=0.80,
            confidence=0.95,
            pattern='beta_expansion',
            volume_confirmed=True
        )
        assert higher_score > score
    
    def test_scan_frequency_control(self, scanner):
        """Test tier-based scanning frequency."""
        current_time = time.time()
        
        # Should scan immediately on first call
        assert scanner._should_scan_tier(AlertTier.CRITICAL, current_time)
        
        # Update last scan time
        scanner.last_scan_times[AlertTier.CRITICAL] = current_time
        
        # Should not scan immediately after
        assert not scanner._should_scan_tier(AlertTier.CRITICAL, current_time + 30)
        
        # Should scan after interval
        assert scanner._should_scan_tier(AlertTier.CRITICAL, current_time + 120)
    
    def test_alert_filtering(self, scanner):
        """Test alert filtering by value score."""
        # Create mock alerts with different value scores
        alerts = [
            Mock(value_score=50.0),
            Mock(value_score=20.0),  # Below threshold
            Mock(value_score=80.0),
            Mock(value_score=15.0)   # Below threshold
        ]
        
        filtered = scanner._filter_by_value(alerts)
        
        # Should filter out alerts below threshold (25.0)
        assert len(filtered) == 2
        assert all(alert.value_score >= 25.0 for alert in filtered)
        
        # Should be sorted by value score (highest first)
        assert filtered[0].value_score >= filtered[1].value_score
    
    def test_throttling_limits(self, scanner):
        """Test alert throttling functionality."""
        current_time = time.time()
        
        # Create mock alerts
        alerts = [
            Mock(
                tier=AlertTier.CRITICAL,
                symbol='ETHUSDT',
                alpha_magnitude=0.60,
                confidence=0.95
            ),
            Mock(
                tier=AlertTier.HIGH,
                symbol='SOLUSDT',
                alpha_magnitude=0.25,
                confidence=0.90
            ),
            Mock(
                tier=AlertTier.CRITICAL,
                symbol='ADAUSDT',
                alpha_magnitude=0.55,
                confidence=0.96
            )
        ]
        
        # Mock tier configs
        for alert in alerts:
            scanner.tiers[alert.tier] = {'max_alerts_per_hour': 2, 'cooldown_override': True}
        
        throttled = scanner._apply_throttling(alerts)
        
        # Should respect tier limits
        critical_alerts = [a for a in throttled if a.tier == AlertTier.CRITICAL]
        assert len(critical_alerts) <= 2
    
    def test_emergency_override(self, scanner):
        """Test emergency override functionality."""
        # Create emergency-level alert
        emergency_alert = Mock(
            alpha_magnitude=1.20,  # 120% alpha
            confidence=0.99,       # 99% confidence
            tier=AlertTier.CRITICAL,
            symbol='ETHUSDT'
        )
        
        assert scanner._is_emergency_override(emergency_alert)
        
        # Normal alert should not trigger override
        normal_alert = Mock(
            alpha_magnitude=0.30,
            confidence=0.85,
            tier=AlertTier.HIGH,
            symbol='SOLUSDT'
        )
        
        assert not scanner._is_emergency_override(normal_alert)
    
    def test_performance_tracking(self, scanner):
        """Test performance metrics tracking."""
        # Create mock results
        results = [
            Mock(alpha_magnitude=0.50, confidence=0.95),
            Mock(alpha_magnitude=0.25, confidence=0.90),
            Mock(alpha_magnitude=0.80, confidence=0.98)
        ]
        
        start_time = time.time() - 0.1  # 100ms ago
        
        scanner._track_performance('test', results, start_time)
        
        assert len(scanner.performance_history) == 1
        metrics = scanner.performance_history[0]
        
        assert metrics.scanner_type == 'test'
        assert metrics.total_alerts == 3
        assert metrics.processing_time_ms > 0

class TestAlphaIntegrationManager:
    """Test suite for AlphaIntegrationManager."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for integration manager."""
        return {
            'alpha_scanning': {
                'enabled': True,
                'interval_minutes': 15
            },
            'alpha_scanning_optimized': {
                'enabled': False,  # Start disabled
                'alpha_tiers': {
                    'tier_1_critical': {'min_alpha': 0.50, 'min_confidence': 0.95}
                }
            }
        }
    
    @pytest.fixture
    def integration_manager(self, mock_config):
        """Create integration manager for testing."""
        return AlphaIntegrationManager(mock_config)
    
    def test_mode_determination(self, integration_manager):
        """Test scanner mode determination."""
        assert integration_manager.mode == ScannerMode.LEGACY_ONLY
    
    def test_parallel_mode_initialization(self):
        """Test parallel mode initialization."""
        config = {
            'alpha_scanning': {'enabled': True},
            'alpha_scanning_optimized': {'enabled': True}
        }
        
        manager = AlphaIntegrationManager(config)
        assert manager.mode == ScannerMode.PARALLEL
    
    @pytest.mark.asyncio
    async def test_legacy_scanning(self, integration_manager):
        """Test legacy scanner execution."""
        # Mock legacy scanner
        integration_manager.legacy_scanner = Mock()
        integration_manager.legacy_scanner.scan_for_alpha_opportunities.return_value = [
            Mock(symbol='ETHUSDT', alpha_potential=0.15, confidence=0.85)
        ]
        
        market_data = {'ETHUSDT': {'price': 2000}}
        results = await integration_manager._scan_legacy_only(market_data)
        
        assert len(results) == 1
        assert results[0]['symbol'] == 'ETHUSDT'
        assert results[0]['scanner_type'] == 'legacy'
    
    @pytest.mark.asyncio
    async def test_parallel_scanning(self, integration_manager):
        """Test parallel scanning execution."""
        # Mock both scanners
        integration_manager.legacy_scanner = Mock()
        integration_manager.optimized_scanner = Mock()
        
        integration_manager.legacy_scanner.scan_for_alpha_opportunities.return_value = [
            Mock(symbol='ETHUSDT', alpha_potential=0.10, confidence=0.80)
        ]
        
        integration_manager.optimized_scanner.scan_for_alpha_opportunities.return_value = [
            Mock(
                symbol='ETHUSDT',
                alpha_magnitude=0.25,
                confidence=0.90,
                value_score=75.0,
                tier=AlertTier.HIGH,
                pattern_type='beta_expansion',
                trading_insight='Test insight',
                risk_level='Medium',
                expected_duration='3-5 days',
                entry_conditions=['Test condition'],
                exit_conditions=['Test exit'],
                timestamp=datetime.now(timezone.utc),
                volume_confirmed=True
            )
        ]
        
        # Set mode to parallel
        integration_manager.mode = ScannerMode.PARALLEL
        
        market_data = {'ETHUSDT': {'price': 2000}}
        results = await integration_manager._scan_parallel(market_data)
        
        # Should return optimized results
        assert len(results) == 1
        assert results[0]['scanner_type'] == 'optimized'
        
        # Should have comparison metrics
        assert 'latest' in integration_manager.comparison_metrics
    
    def test_rollout_percentage_update(self, integration_manager):
        """Test gradual rollout percentage updates."""
        integration_manager.mode = ScannerMode.GRADUAL_ROLLOUT
        integration_manager.rollout_percentage = 20
        integration_manager.last_rollout_time = time.time() - (25 * 3600)  # 25 hours ago
        
        # Mock safety check to return True
        integration_manager._is_safe_to_increase_rollout = Mock(return_value=True)
        
        integration_manager._update_rollout_percentage()
        
        # Should increase by increment (10%)
        assert integration_manager.rollout_percentage == 30
    
    def test_safety_threshold_check(self, integration_manager):
        """Test safety threshold checking."""
        # Set up comparison metrics
        integration_manager.comparison_metrics = {
            'latest': {
                'optimized': {
                    'error_rate': 0.02,  # 2% error rate (below 5% threshold)
                    'avg_alpha': 0.25
                },
                'legacy': {
                    'avg_alpha': 0.20
                }
            }
        }
        
        assert integration_manager._is_safe_to_increase_rollout()
        
        # Test with high error rate
        integration_manager.comparison_metrics['latest']['optimized']['error_rate'] = 0.08
        assert not integration_manager._is_safe_to_increase_rollout()
    
    def test_performance_summary(self, integration_manager):
        """Test performance summary generation."""
        # Add some mock performance history
        integration_manager.performance_history = [
            ScannerPerformanceMetrics(
                scanner_type='legacy',
                total_alerts=5,
                high_value_alerts=1,
                average_alpha=0.08,
                average_confidence=0.80,
                processing_time_ms=150.0,
                memory_usage_mb=50.0,
                error_count=0,
                timestamp=datetime.now(timezone.utc)
            ),
            ScannerPerformanceMetrics(
                scanner_type='optimized',
                total_alerts=3,
                high_value_alerts=2,
                average_alpha=0.35,
                average_confidence=0.92,
                processing_time_ms=120.0,
                memory_usage_mb=45.0,
                error_count=0,
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        summary = integration_manager.get_performance_summary()
        
        assert 'mode' in summary
        assert 'rollout_percentage' in summary
        assert 'legacy_performance' in summary
        assert 'optimized_performance' in summary
    
    def test_force_rollback(self, integration_manager):
        """Test force rollback functionality."""
        integration_manager.mode = ScannerMode.PARALLEL
        integration_manager.rollout_percentage = 50
        
        integration_manager.force_rollback()
        
        assert integration_manager.mode == ScannerMode.LEGACY_ONLY
        assert integration_manager.rollout_percentage == 0
        assert not integration_manager.optimized_config['enabled']

class TestProductionScenarios:
    """Test production deployment scenarios."""
    
    @pytest.mark.asyncio
    async def test_high_load_scenario(self):
        """Test scanner performance under high load."""
        config = {
            'alpha_scanning_optimized': {
                'alpha_tiers': {
                    'tier_1_critical': {'min_alpha': 0.50, 'min_confidence': 0.95, 'scan_interval_minutes': 1}
                },
                'pattern_weights': {'beta_expansion': 1.0},
                'value_scoring': {'alpha_weight': 0.40, 'confidence_weight': 0.25, 'pattern_weight': 0.20, 'volume_weight': 0.10, 'risk_weight': 0.05},
                'filtering': {'min_alert_value_score': 25.0},
                'throttling': {'max_total_alerts_per_hour': 8}
            },
            'pattern_configs': {}
        }
        
        # Create large market data set
        market_data = {}
        for i in range(100):  # 100 symbols
            market_data[f'SYMBOL{i}USDT'] = {
                'beta_change': 0.3 + (i * 0.01),
                'beta': 1.0 + (i * 0.02),
                'volume_spike': i % 2 == 0
            }
        
        scanner = OptimizedAlphaScanner()
        scanner.config = config
        scanner.alpha_config = config['alpha_scanning_optimized']
        scanner.pattern_configs = config['pattern_configs']
        scanner._initialize_from_config()
        
        start_time = time.time()
        results = scanner.scan_for_alpha_opportunities(market_data)
        processing_time = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        assert processing_time < 5.0
        
        # Should respect throttling limits
        assert len(results) <= 8
    
    def test_memory_usage_monitoring(self):
        """Test memory usage tracking."""
        scanner = OptimizedAlphaScanner()
        
        memory_usage = scanner._get_memory_usage()
        assert memory_usage >= 0  # Should return valid memory usage
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """Test error handling and fallback mechanisms."""
        config = {
            'alpha_scanning': {'enabled': True},
            'alpha_scanning_optimized': {'enabled': True}
        }
        
        manager = AlphaIntegrationManager(config)
        
        # Mock optimized scanner to raise exception
        manager.optimized_scanner = Mock()
        manager.optimized_scanner.scan_for_alpha_opportunities.side_effect = Exception("Test error")
        
        # Mock legacy scanner to work normally
        manager.legacy_scanner = Mock()
        manager.legacy_scanner.scan_for_alpha_opportunities.return_value = [
            Mock(symbol='ETHUSDT', alpha_potential=0.10)
        ]
        
        market_data = {'ETHUSDT': {'price': 2000}}
        results = await manager.scan_for_opportunities(market_data)
        
        # Should fallback to legacy scanner
        assert len(results) > 0
        assert results[0]['symbol'] == 'ETHUSDT'

if __name__ == '__main__':
    pytest.main([__file__, '-v']) 