"""
Test suite for InterpretationManager

Tests the centralized interpretation processing system including:
- Legacy format conversion
- Validation and standardization
- Output formatting for different systems
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.interpretation.interpretation_manager import InterpretationManager
from src.core.models.interpretation_schema import (
    ComponentInterpretation,
    MarketInterpretationSet,
    ComponentType,
    InterpretationSeverity
)


class TestInterpretationManager:
    """Test cases for InterpretationManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = InterpretationManager()
    
    def test_process_simple_string_interpretation(self):
        """Test processing a simple string interpretation."""
        raw_data = "Market shows bullish momentum with strong volume support"
        source = "test_component"
        
        result = self.manager.process_interpretations(raw_data, source)
        
        assert isinstance(result, MarketInterpretationSet)
        assert result.source_component == source
        assert len(result.interpretations) == 1
        
        interpretation = result.interpretations[0]
        assert interpretation.interpretation_text == raw_data
        assert interpretation.component_name == source
        assert interpretation.severity == InterpretationSeverity.INFO
    
    def test_process_list_of_strings(self):
        """Test processing a list of string interpretations."""
        raw_data = [
            "RSI indicates oversold conditions",
            "MACD showing bullish crossover",
            "Volume confirms the breakout"
        ]
        source = "technical_analysis"
        
        result = self.manager.process_interpretations(raw_data, source)
        
        assert len(result.interpretations) == 3
        for i, interpretation in enumerate(result.interpretations):
            assert interpretation.interpretation_text == raw_data[i]
            assert interpretation.component_name == f"{source}_{i}"
    
    def test_process_dict_with_interpretation_key(self):
        """Test processing dictionary with 'interpretation' key."""
        raw_data = {
            'interpretation': 'Strong bullish signal detected',
            'confidence': 0.85,
            'severity': 'warning',
            'metadata': {'signal_strength': 'high'}
        }
        source = "signal_generator"
        
        result = self.manager.process_interpretations(raw_data, source)
        
        assert len(result.interpretations) == 1
        interpretation = result.interpretations[0]
        assert interpretation.interpretation_text == 'Strong bullish signal detected'
        assert interpretation.confidence_score == 0.85
        assert interpretation.severity == InterpretationSeverity.WARNING
        assert interpretation.metadata == {'signal_strength': 'high'}
    
    def test_process_component_keyed_dict(self):
        """Test processing dictionary with component names as keys."""
        raw_data = {
            'rsi': 'RSI shows oversold at 25',
            'macd': 'MACD bullish crossover confirmed',
            'volume': {
                'text': 'Volume spike indicates strong interest',
                'confidence': 0.9,
                'severity': 'critical'
            }
        }
        source = "technical_indicators"
        
        result = self.manager.process_interpretations(raw_data, source)
        
        assert len(result.interpretations) == 3
        
        # Check RSI interpretation
        rsi_interp = next(i for i in result.interpretations if i.component_name == 'rsi')
        assert rsi_interp.interpretation_text == 'RSI shows oversold at 25'
        assert rsi_interp.component_type == ComponentType.TECHNICAL_INDICATOR
        
        # Check volume interpretation with nested structure
        vol_interp = next(i for i in result.interpretations if i.component_name == 'volume')
        assert vol_interp.interpretation_text == 'Volume spike indicates strong interest'
        assert vol_interp.confidence_score == 0.9
        assert vol_interp.severity == InterpretationSeverity.CRITICAL
    
    def test_component_type_inference(self):
        """Test component type inference from component names."""
        test_cases = [
            ('rsi_analysis', ComponentType.TECHNICAL_INDICATOR),
            ('sentiment_score', ComponentType.SENTIMENT_ANALYSIS),
            ('funding_rate', ComponentType.FUNDING_ANALYSIS),
            ('volume_profile', ComponentType.VOLUME_ANALYSIS),
            ('price_action', ComponentType.PRICE_ANALYSIS),
            ('whale_movements', ComponentType.WHALE_ANALYSIS),
            ('unknown_component', ComponentType.GENERAL_ANALYSIS)
        ]
        
        for component_name, expected_type in test_cases:
            inferred_type = self.manager._infer_component_type(component_name)
            assert inferred_type == expected_type, f"Failed for {component_name}"
    
    def test_severity_inference(self):
        """Test severity inference from various input formats."""
        test_cases = [
            ('critical', InterpretationSeverity.CRITICAL),
            ('high', InterpretationSeverity.CRITICAL),
            ('warning', InterpretationSeverity.WARNING),
            ('medium', InterpretationSeverity.WARNING),
            ('info', InterpretationSeverity.INFO),
            ('low', InterpretationSeverity.INFO),
            (3, InterpretationSeverity.CRITICAL),
            (2, InterpretationSeverity.WARNING),
            (1, InterpretationSeverity.INFO),
            ('unknown', InterpretationSeverity.INFO)
        ]
        
        for severity_input, expected_severity in test_cases:
            inferred_severity = self.manager._infer_severity(severity_input)
            assert inferred_severity == expected_severity, f"Failed for {severity_input}"
    
    def test_validation_empty_text(self):
        """Test validation handles empty interpretation text."""
        # Create interpretations with empty text by bypassing __post_init__ validation
        valid_interp = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="test2",
            interpretation_text="Valid interpretation",
            severity=InterpretationSeverity.INFO,
            confidence_score=0.5,
            timestamp=datetime.now()
        )
        
        # Manually create invalid interpretation to test validation
        invalid_interp = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="test",
            interpretation_text="placeholder",  # Will be changed after creation
            severity=InterpretationSeverity.INFO,
            confidence_score=0.5,
            timestamp=datetime.now()
        )
        invalid_interp.interpretation_text = ""  # Make it empty after creation
        
        interpretations = [invalid_interp, valid_interp]
        
        validated = self.manager._validate_interpretations(interpretations)
        
        # Should only return the valid interpretation
        assert len(validated) == 1
        assert validated[0].interpretation_text == "Valid interpretation"
    
    def test_validation_long_text_truncation(self):
        """Test validation truncates overly long interpretation text."""
        long_text = "A" * 15000  # Very long text
        
        interpretations = [
            ComponentInterpretation(
                component_type=ComponentType.TECHNICAL_INDICATOR,
                component_name="test",
                interpretation_text=long_text,
                severity=InterpretationSeverity.INFO,
                confidence_score=0.5,
                timestamp=datetime.now()
            )
        ]
        
        validated = self.manager._validate_interpretations(interpretations)
        
        assert len(validated) == 1
        assert len(validated[0].interpretation_text) <= 10003  # 10000 + "..."
        assert validated[0].interpretation_text.endswith("...")
    
    def test_validation_confidence_score_bounds(self):
        """Test validation enforces confidence score bounds."""
        # Create interpretations with valid scores first, then modify them
        interp1 = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="test1",
            interpretation_text="Test",
            severity=InterpretationSeverity.INFO,
            confidence_score=0.5,  # Valid initially
            timestamp=datetime.now()
        )
        interp1.confidence_score = -0.5  # Make invalid after creation
        
        interp2 = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="test2",
            interpretation_text="Test",
            severity=InterpretationSeverity.INFO,
            confidence_score=0.5,  # Valid initially
            timestamp=datetime.now()
        )
        interp2.confidence_score = 1.5  # Make invalid after creation
        
        interpretations = [interp1, interp2]
        
        validated = self.manager._validate_interpretations(interpretations)
        
        assert len(validated) == 2
        assert validated[0].confidence_score == 0.0  # Clamped to 0
        assert validated[1].confidence_score == 1.0  # Clamped to 1
    
    def test_format_as_text(self):
        """Test text formatting output."""
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            source_component="test_source",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="RSI",
                    interpretation_text="RSI oversold at 25",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.85,
                    timestamp=datetime.now()
                )
            ],
            metadata={}
        )
        
        text_output = self.manager.get_formatted_interpretation(interpretation_set, 'text')
        
        assert isinstance(text_output, str)
        assert "Market Analysis - 2024-01-01 12:00:00" in text_output
        assert "Source: test_source" in text_output
        assert "🟡 RSI" in text_output  # Warning emoji
        assert "RSI oversold at 25" in text_output
        assert "Confidence: 0.85" in text_output
    
    def test_format_as_json(self):
        """Test JSON formatting output."""
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            source_component="test_source",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="RSI",
                    interpretation_text="RSI oversold at 25",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.85,
                    timestamp=datetime(2024, 1, 1, 12, 0, 0)
                )
            ],
            metadata={'test': 'data'}
        )
        
        json_output = self.manager.get_formatted_interpretation(interpretation_set, 'json')
        
        assert isinstance(json_output, dict)
        assert json_output['timestamp'] == '2024-01-01T12:00:00'
        assert json_output['source_component'] == 'test_source'
        assert len(json_output['interpretations']) == 1
        
        interp = json_output['interpretations'][0]
        assert interp['component_type'] == 'technical_indicator'
        assert interp['component_name'] == 'RSI'
        assert interp['interpretation_text'] == 'RSI oversold at 25'
        assert interp['severity'] == 'warning'
        assert interp['confidence_score'] == 0.85
    
    def test_format_for_alerts(self):
        """Test alert formatting output."""
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            source_component="test_source",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="RSI",
                    interpretation_text="RSI oversold at 25",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.85,
                    timestamp=datetime(2024, 1, 1, 12, 0, 0)
                ),
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="MACD",
                    interpretation_text="MACD neutral",
                    severity=InterpretationSeverity.INFO,  # Should not create alert
                    confidence_score=0.5,
                    timestamp=datetime(2024, 1, 1, 12, 0, 0)
                )
            ],
            metadata={}
        )
        
        alert_output = self.manager.get_formatted_interpretation(interpretation_set, 'alert')
        
        assert isinstance(alert_output, list)
        assert len(alert_output) == 1  # Only warning/critical create alerts
        
        alert = alert_output[0]
        assert alert['title'] == 'RSI Alert'
        assert alert['message'] == 'RSI oversold at 25'
        assert alert['severity'] == 'warning'
        assert alert['confidence'] == 0.85
        assert alert['component'] == 'RSI'
        assert alert['type'] == 'technical_indicator'
    
    def test_format_for_pdf(self):
        """Test PDF formatting output."""
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            source_component="test_source",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="RSI",
                    interpretation_text="RSI oversold at 25",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.85,
                    timestamp=datetime.now()
                )
            ],
            metadata={}
        )
        
        pdf_output = self.manager.get_formatted_interpretation(interpretation_set, 'pdf')
        
        assert isinstance(pdf_output, dict)
        assert pdf_output['title'] == 'Market Analysis Report - 2024-01-01 12:00:00'
        assert pdf_output['source'] == 'test_source'
        assert len(pdf_output['sections']) == 1
        
        section = pdf_output['sections'][0]
        assert section['component_name'] == 'RSI'
        assert section['component_type'] == 'technical_indicator'
        assert section['content'] == 'RSI oversold at 25'
        assert section['severity'] == 'warning'
        assert section['confidence'] == 0.85
        
        # Check summary
        assert 'Analysis Summary' in pdf_output['summary']
        assert '1 interpretations processed' in pdf_output['summary']
    
    def test_error_handling_invalid_input(self):
        """Test error handling for invalid input."""
        # This should not raise an exception but return a fallback interpretation
        result = self.manager.process_interpretations(None, "test_source")
        
        assert isinstance(result, MarketInterpretationSet)
        assert len(result.interpretations) == 0  # Empty for None input
    
    def test_processing_stats(self):
        """Test processing statistics tracking."""
        initial_stats = self.manager.get_processing_stats()
        assert initial_stats['total_processed'] == 0
        
        # Process some interpretations
        self.manager.process_interpretations("Test interpretation", "test_source")
        
        updated_stats = self.manager.get_processing_stats()
        assert updated_stats['total_processed'] == 1
        assert updated_stats['conversion_successes'] == 1
    
    def test_caching_functionality(self):
        """Test interpretation caching."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        result = self.manager.process_interpretations(
            "Test interpretation", 
            "test_source", 
            timestamp
        )
        
        # Check cache
        cache_key = f"test_source_{timestamp.isoformat()}"
        cached_result = self.manager.get_cached_interpretation(cache_key)
        
        assert cached_result is not None
        assert cached_result.source_component == "test_source"
        assert len(cached_result.interpretations) == 1
        
        # Clear cache
        self.manager.clear_cache()
        cached_result_after_clear = self.manager.get_cached_interpretation(cache_key)
        assert cached_result_after_clear is None
    
    def test_already_standardized_input(self):
        """Test processing already standardized ComponentInterpretation objects."""
        standardized_interp = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="RSI",
            interpretation_text="RSI oversold at 25",
            severity=InterpretationSeverity.WARNING,
            confidence_score=0.85,
            timestamp=datetime.now()
        )
        
        result = self.manager.process_interpretations(standardized_interp, "test_source")
        
        assert len(result.interpretations) == 1
        assert result.interpretations[0] == standardized_interp
    
    def test_market_interpretation_set_input(self):
        """Test processing MarketInterpretationSet input."""
        existing_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="original_source",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="RSI",
                    interpretation_text="RSI oversold at 25",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.85,
                    timestamp=datetime.now()
                )
            ],
            metadata={}
        )
        
        result = self.manager.process_interpretations(existing_set, "new_source")
        
        assert len(result.interpretations) == 1
        assert result.source_component == "new_source"  # New source component
        assert result.interpretations[0].component_name == "RSI"  # Original interpretation preserved