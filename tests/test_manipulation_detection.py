"""Unit tests for Order Book Manipulation Detection

Tests the ManipulationDetector class for detecting spoofing, layering,
and wash trading patterns in orderbook data.
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from collections import deque
import logging
from unittest.mock import MagicMock, patch

from src.indicators.manipulation_detector import (
    ManipulationDetector, ManipulationType
)


class TestManipulationDetector:
    """Test suite for ManipulationDetector class"""
    
    @pytest.fixture
    def detector_config(self):
        """Default configuration for testing"""
        return {
            'manipulation_detection': {
                'enabled': True,
                'history': {
                    'max_snapshots': 10,
                    'trade_history_size': 20
                },
                'spoofing': {
                    'enabled': True,
                    'volatility_threshold': 2.0,
                    'min_order_size_usd': 50000,
                    'execution_ratio_threshold': 0.1
                },
                'layering': {
                    'enabled': True,
                    'price_gap_threshold': 0.001,
                    'size_uniformity_threshold': 0.1,
                    'min_layers': 3
                },
                'alerts': {
                    'severity_levels': {
                        'low': 0.5,
                        'medium': 0.7,
                        'high': 0.85,
                        'critical': 0.95
                    }
                }
            }
        }
    
    @pytest.fixture
    def detector(self, detector_config):
        """Create a ManipulationDetector instance"""
        logger = logging.getLogger('test')
        return ManipulationDetector(detector_config, logger)
    
    @pytest.fixture
    def sample_orderbook(self):
        """Sample orderbook data"""
        return {
            'bids': [
                [49900.0, 2.5],
                [49899.0, 1.8],
                [49898.0, 3.2],
                [49897.0, 1.5],
                [49896.0, 2.0]
            ],
            'asks': [
                [49901.0, 2.3],
                [49902.0, 1.9],
                [49903.0, 3.1],
                [49904.0, 1.6],
                [49905.0, 2.1]
            ],
            'timestamp': 1234567890123
        }
    
    @pytest.fixture
    def sample_trades(self):
        """Sample trade data"""
        return [
            {
                'id': 'trade_1',
                'price': 49900.5,
                'size': 0.5,
                'side': 'buy',
                'timestamp': 1234567890100
            },
            {
                'id': 'trade_2',
                'price': 49901.0,
                'size': 0.3,
                'side': 'sell',
                'timestamp': 1234567890200
            }
        ]
    
    def test_initialization(self, detector):
        """Test detector initialization"""
        assert detector.enabled is True
        assert isinstance(detector.orderbook_history, deque)
        assert detector.orderbook_history.maxlen == 10
        assert detector.spoof_volatility_threshold == 2.0
        assert detector.layer_min_count == 3
    
    def test_update_history(self, detector, sample_orderbook, sample_trades):
        """Test history update functionality"""
        initial_history_size = len(detector.orderbook_history)
        
        detector.update_history(sample_orderbook, sample_trades)
        
        assert len(detector.orderbook_history) == initial_history_size + 1
        assert len(detector.trade_history) == len(sample_trades)
        
        # Check stored data
        latest_snapshot = detector.orderbook_history[-1]
        assert latest_snapshot['mid_price'] == 49900.5  # (49900 + 49901) / 2
        assert latest_snapshot['spread'] == 1.0  # 49901 - 49900
    
    def test_insufficient_history(self, detector, sample_orderbook, sample_trades):
        """Test behavior with insufficient history"""
        result = detector.analyze_manipulation(sample_orderbook, sample_trades)
        
        assert result['overall_likelihood'] == 0.0
        assert result['manipulation_type'] == 'none'
        assert result['confidence'] == 0.0
    
    @pytest.mark.asyncio
    async def test_spoofing_detection(self, detector, sample_orderbook, sample_trades):
        """Test spoofing pattern detection"""
        # Build history with volatile changes
        for i in range(5):
            # Create volatile orderbook changes
            volatile_book = sample_orderbook.copy()
            if i % 2 == 0:
                # Large bid appears
                volatile_book['bids'] = [[49910.0, 50.0]] + volatile_book['bids']
            else:
                # Large bid disappears
                volatile_book['bids'] = volatile_book['bids'][1:]
            
            detector.update_history(volatile_book, [])
        
        # Analyze for spoofing
        result = await detector.analyze_manipulation(sample_orderbook, sample_trades)
        
        # Should detect spoofing due to high volatility and low execution
        assert result['spoofing']['likelihood'] > 0
        assert 'volatility_ratio' in result['spoofing']
        assert 'execution_ratio' in result['spoofing']
    
    @pytest.mark.asyncio
    async def test_layering_detection(self, detector):
        """Test layering pattern detection"""
        # Create layered orderbook
        layered_orderbook = {
            'bids': [
                [49900.0, 10.0],
                [49899.0, 10.1],  # Similar sizes
                [49898.0, 9.9],
                [49897.0, 10.0],
                [49896.0, 10.2]
            ],
            'asks': [
                [49901.0, 2.3],
                [49902.0, 1.9],
                [49903.0, 3.1],
                [49904.0, 1.6],
                [49905.0, 2.1]
            ]
        }
        
        # Build minimal history
        for _ in range(3):
            detector.update_history(layered_orderbook, [])
        
        result = await detector.analyze_manipulation(layered_orderbook, [])
        
        # Should detect layering on bid side
        assert result['layering']['bid_side']['likelihood'] > 0
        assert result['layering']['bid_side']['size_uniformity'] < 0.1  # Low variance
    
    @pytest.mark.asyncio
    async def test_manipulation_score_calculation(self, detector, sample_orderbook):
        """Test manipulation score conversion"""
        # Build history
        for _ in range(5):
            detector.update_history(sample_orderbook, [])
        
        # Mock high manipulation likelihood
        with patch.object(detector, '_detect_spoofing') as mock_spoof:
            mock_spoof.return_value = {'likelihood': 0.8, 'detected': True}
            
            result = await detector.analyze_manipulation(sample_orderbook, [])
            
            # High likelihood should result in low manipulation score
            assert result['overall_likelihood'] >= 0.4  # At least spoofing weight * 0.8
            assert result['severity'] in ['MEDIUM', 'HIGH', 'CRITICAL']
    
    def test_confidence_calculation(self, detector, sample_orderbook):
        """Test confidence calculation based on data quality"""
        # Low confidence with minimal history
        for _ in range(3):
            detector.update_history(sample_orderbook, [])
        
        confidence = detector._calculate_confidence()
        assert confidence < 1.0  # Should be reduced due to insufficient history
        
        # Higher confidence with more history
        for _ in range(20):
            detector.update_history(sample_orderbook, [])
        
        confidence = detector._calculate_confidence()
        assert confidence > 0.7  # Should be higher with more data
    
    def test_severity_mapping(self, detector):
        """Test severity level mapping"""
        assert detector._get_severity(0.3) == 'LOW'
        assert detector._get_severity(0.6) == 'MEDIUM'
        assert detector._get_severity(0.8) == 'HIGH'
        assert detector._get_severity(0.96) == 'CRITICAL'
    
    def test_large_order_detection(self, detector, sample_orderbook):
        """Test large order change detection"""
        # First snapshot
        detector.update_history(sample_orderbook, [])
        
        # Second snapshot with large order
        large_order_book = sample_orderbook.copy()
        large_order_book['bids'][0] = [49900.0, 100.0]  # Large order appears
        detector.update_history(large_order_book, [])
        
        changes = detector._detect_large_order_changes()
        assert changes > 0  # Should detect the large order change
    
    def test_order_clustering(self, detector):
        """Test order clustering detection"""
        prices = np.array([100.0, 100.05, 100.1, 101.0, 101.05])
        sizes = np.array([10.0, 10.0, 10.0, 5.0, 5.0])
        
        clusters = detector._find_order_clusters(prices, sizes)
        
        # Should find at least one cluster (first 3 orders)
        assert len(clusters) >= 1
        assert clusters[0]['count'] >= 3
    
    @pytest.mark.asyncio
    async def test_disabled_detector(self, detector_config):
        """Test behavior when detector is disabled"""
        detector_config['manipulation_detection']['enabled'] = False
        logger = logging.getLogger('test')
        detector = ManipulationDetector(detector_config, logger)
        
        result = await detector.analyze_manipulation({}, [])
        
        assert result['overall_likelihood'] == 0.0
        assert result['manipulation_type'] == 'none'
    
    def test_statistics_tracking(self, detector, sample_orderbook):
        """Test statistics and metrics tracking"""
        # Initial state
        stats = detector.get_statistics()
        assert stats['detection_count'] == 0
        assert stats['last_detection'] is None
        
        # After detection
        for _ in range(5):
            detector.update_history(sample_orderbook, [])
        
        # Force a detection
        detector.detection_count = 1
        detector.last_detection_time = datetime.now(timezone.utc)
        
        stats = detector.get_statistics()
        assert stats['detection_count'] == 1
        assert stats['last_detection'] is not None
        assert stats['history_size'] == 5


class TestIntegrationWithOrderbook:
    """Test integration with OrderbookIndicators"""
    
    @pytest.mark.asyncio
    async def test_orderbook_integration(self):
        """Test that manipulation detection integrates properly with OrderbookIndicators"""
        from src.indicators.orderbook_indicators import OrderbookIndicators
        
        # Create orderbook indicators with test config
        config = {
            'analysis': {
                'indicators': {
                    'orderbook': {
                        'manipulation_detection': {
                            'enabled': True
                        }
                    }
                }
            }
        }
        
        logger = logging.getLogger('test')
        orderbook_indicators = OrderbookIndicators(config, logger)
        
        # Verify manipulation detector is initialized
        assert hasattr(orderbook_indicators, 'manipulation_detector')
        assert orderbook_indicators.manipulation_detector.enabled is True
        
        # Verify weights include manipulation
        assert 'manipulation' in orderbook_indicators.component_weights
        assert orderbook_indicators.component_weights['manipulation'] == 0.08
        
        # Test calculate method includes manipulation
        market_data = {
            'symbol': 'BTCUSDT',
            'orderbook': {
                'bids': [[49900.0, 2.5]] * 25,
                'asks': [[49901.0, 2.3]] * 25
            },
            'trades': []
        }
        
        result = await orderbook_indicators.calculate(market_data)
        
        # Verify result includes manipulation analysis
        assert 'manipulation_analysis' in result
        assert 'manipulation' in result['components']
        assert 'confidence' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])