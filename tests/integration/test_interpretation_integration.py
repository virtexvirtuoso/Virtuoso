"""
Integration tests for the centralized interpretation system.

This test suite verifies that the InterpretationManager works correctly
across all components of the trading system.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import json

from src.core.interpretation.interpretation_manager import InterpretationManager
from src.core.models.interpretation_schema import (
    ComponentInterpretation,
    MarketInterpretationSet,
    ComponentType,
    InterpretationSeverity
)


class TestInterpretationIntegration:
    """Integration tests for the centralized interpretation system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = InterpretationManager()
        
    def test_end_to_end_interpretation_flow(self):
        """Test the complete interpretation flow from raw data to formatted output."""
        # Simulate raw interpretations from different sources
        raw_interpretations = [
            "Technical analysis shows strong bullish momentum with RSI at 75",
            {
                'component': 'volume_analysis',
                'display_name': 'Volume Analysis',
                'interpretation': 'High volume confirms the upward price movement'
            },
            {
                'sentiment_analysis': 'Market sentiment is extremely positive with fear/greed index at 80'
            }
        ]
        
        # Process through InterpretationManager
        interpretation_set = self.manager.process_interpretations(
            raw_interpretations,
            'integration_test',
            datetime.now()
        )
        
        # Verify processing
        assert len(interpretation_set.interpretations) == 3
        assert interpretation_set.source_component == 'integration_test'
        
        # Test different output formats
        alert_format = self.manager.get_formatted_interpretation(interpretation_set, 'alert')
        pdf_format = self.manager.get_formatted_interpretation(interpretation_set, 'pdf')
        json_format = self.manager.get_formatted_interpretation(interpretation_set, 'json')
        text_format = self.manager.get_formatted_interpretation(interpretation_set, 'text')
        
        # Verify all formats are generated
        assert alert_format is not None
        assert pdf_format is not None
        assert json_format is not None
        assert text_format is not None
        
        # Verify JSON format is serializable
        json_str = json.dumps(json_format)
        assert len(json_str) > 0
        
    def test_monitor_integration(self):
        """Test integration with MarketMonitor component."""
        # Simulate monitor processing interpretations
        monitor_interpretations = [
            {
                'component': 'technical',
                'display_name': 'Technical Analysis',
                'interpretation': 'Strong bullish signals across multiple timeframes'
            },
            {
                'component': 'volume',
                'display_name': 'Volume Analysis', 
                'interpretation': 'Volume surge indicates institutional buying'
            }
        ]
        
        interpretation_set = self.manager.process_interpretations(
            monitor_interpretations,
            'market_monitor',
            datetime.now()
        )
        
        # Verify monitor-specific processing
        assert len(interpretation_set.interpretations) == 2
        assert all(interp.component_type in [ComponentType.TECHNICAL_INDICATOR, ComponentType.VOLUME_ANALYSIS] 
                  for interp in interpretation_set.interpretations)
        
    def test_signal_generator_integration(self):
        """Test integration with SignalGenerator component."""
        # Simulate signal generator interpretations
        signal_interpretations = [
            "Overall Analysis: BTC shows bullish sentiment with confluence score of 75.2",
            "Technical: Score of 78.5 indicates strong bullish momentum",
            "Volume: Score of 72.1 shows increased buying pressure"
        ]
        
        interpretation_set = self.manager.process_interpretations(
            signal_interpretations,
            'signal_generator',
            datetime.now()
        )
        
        # Verify signal generator processing
        assert len(interpretation_set.interpretations) == 3
        assert interpretation_set.source_component == 'signal_generator'
        
        # Test formatting for alerts
        alert_format = self.manager.get_formatted_interpretation(interpretation_set, 'alert')
        assert isinstance(alert_format, list)
        
    def test_alert_manager_integration(self):
        """Test integration with AlertManager component."""
        # Simulate complex interpretations that AlertManager might receive
        complex_interpretations = [
            {
                'component': 'sentiment_analysis',
                'interpretation': {
                    'funding_rate': 'Funding rate at 0.05% indicates bullish sentiment',
                    'social_sentiment': 'Social media sentiment strongly positive',
                    'whale_activity': 'Large wallet accumulation detected'
                }
            },
            "Critical: Price approaching key resistance level at $45,000"
        ]
        
        interpretation_set = self.manager.process_interpretations(
            complex_interpretations,
            'alert_manager',
            datetime.now()
        )
        
        # Verify complex interpretation handling
        assert len(interpretation_set.interpretations) >= 2
        
        # Test alert formatting
        alert_format = self.manager.get_formatted_interpretation(interpretation_set, 'alert')
        assert isinstance(alert_format, list)
        
    def test_pdf_generator_integration(self):
        """Test integration with PDF generator component."""
        # Simulate PDF generator processing interpretations
        pdf_interpretations = [
            {
                'component': 'overall_analysis',
                'display_name': 'Market Overview',
                'interpretation': 'Comprehensive market analysis shows bullish trend continuation'
            },
            {
                'component': 'risk_assessment',
                'display_name': 'Risk Assessment',
                'interpretation': 'Risk levels are moderate with proper stop-loss placement recommended'
            }
        ]
        
        interpretation_set = self.manager.process_interpretations(
            pdf_interpretations,
            'pdf_generator',
            datetime.now()
        )
        
        # Test PDF-specific formatting
        pdf_format = self.manager.get_formatted_interpretation(interpretation_set, 'pdf')
        assert isinstance(pdf_format, dict)
        assert 'title' in pdf_format
        assert 'sections' in pdf_format
        assert 'summary' in pdf_format
        
    def test_formatter_integration(self):
        """Test integration with formatting components."""
        # Simulate formatter processing interpretations
        formatter_data = {
            'technical_analysis': {
                'interpretation': 'Technical indicators show strong bullish momentum',
                'signals': {'RSI': 75, 'MACD': 'bullish_crossover'}
            },
            'volume_analysis': {
                'enhanced_interpretation': 'Volume profile indicates strong institutional interest'
            }
        }
        
        # Convert to format suitable for InterpretationManager
        raw_interpretations = []
        for component_name, component_data in formatter_data.items():
            interpretation = None
            if 'enhanced_interpretation' in component_data:
                interpretation = component_data['enhanced_interpretation']
            elif 'interpretation' in component_data:
                interpretation = component_data['interpretation']
            
            if interpretation:
                raw_interpretations.append({
                    'component': component_name,
                    'display_name': component_name.replace('_', ' ').title(),
                    'interpretation': interpretation
                })
        
        interpretation_set = self.manager.process_interpretations(
            raw_interpretations,
            'formatter',
            datetime.now()
        )
        
        # Verify formatter integration
        assert len(interpretation_set.interpretations) == 2
        
    def test_cross_component_consistency(self):
        """Test that interpretations are consistent across different components."""
        # Same raw data processed by different components
        raw_data = [
            "Technical analysis shows bullish momentum",
            "Volume confirms the trend"
        ]
        
        # Process through different components
        monitor_set = self.manager.process_interpretations(raw_data, 'monitor', market_data=None, timestamp=datetime.now())
        signal_set = self.manager.process_interpretations(raw_data, 'signal_generator', market_data=None, timestamp=datetime.now())
        alert_set = self.manager.process_interpretations(raw_data, 'alert_manager', market_data=None, timestamp=datetime.now())
        
        # Verify consistency
        assert len(monitor_set.interpretations) == len(signal_set.interpretations) == len(alert_set.interpretations)
        
        # Verify interpretation text is consistent
        for i in range(len(raw_data)):
            assert monitor_set.interpretations[i].interpretation_text == signal_set.interpretations[i].interpretation_text
            assert signal_set.interpretations[i].interpretation_text == alert_set.interpretations[i].interpretation_text
            
    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        # Test with invalid data
        invalid_data = [
            None,
            "",
            {},
            [],
            {"invalid": "structure"}
        ]
        
        interpretation_set = self.manager.process_interpretations(
            invalid_data,
            'error_test',
            datetime.now()
        )
        
        # Should handle gracefully and return valid set
        assert isinstance(interpretation_set, MarketInterpretationSet)
        assert interpretation_set.source_component == 'error_test'
        
    def test_caching_functionality(self):
        """Test interpretation caching functionality."""
        raw_data = ["Test interpretation for caching"]
        timestamp = datetime.now()
        
        # Process interpretations
        interpretation_set1 = self.manager.process_interpretations(raw_data, 'cache_test', timestamp)
        
        # Check cache
        cache_key = f"cache_test_{timestamp.isoformat()}"
        cached_set = self.manager.get_cached_interpretation(cache_key)
        
        assert cached_set is not None
        assert cached_set.source_component == interpretation_set1.source_component
        assert len(cached_set.interpretations) == len(interpretation_set1.interpretations)
        
    def test_processing_statistics(self):
        """Test processing statistics tracking."""
        initial_stats = self.manager.get_processing_stats()
        initial_count = initial_stats['total_processed']
        
        # Process some interpretations
        for i in range(3):
            self.manager.process_interpretations(
                [f"Test interpretation {i}"],
                f'stats_test_{i}',
                datetime.now()
            )
        
        final_stats = self.manager.get_processing_stats()
        assert final_stats['total_processed'] == initial_count + 3
        
    def test_serialization_and_deserialization(self):
        """Test that interpretation sets can be serialized and deserialized."""
        raw_data = [
            {
                'component': 'test_component',
                'display_name': 'Test Component',
                'interpretation': 'Test interpretation for serialization'
            }
        ]
        
        # Process interpretations
        original_set = self.manager.process_interpretations(raw_data, 'serialization_test', market_data=None, timestamp=datetime.now())
        
        # Serialize to dict
        serialized = original_set.to_dict()
        
        # Deserialize back
        deserialized_set = MarketInterpretationSet.from_dict(serialized)
        
        # Verify integrity
        assert deserialized_set.source_component == original_set.source_component
        assert len(deserialized_set.interpretations) == len(original_set.interpretations)
        assert deserialized_set.interpretations[0].interpretation_text == original_set.interpretations[0].interpretation_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 