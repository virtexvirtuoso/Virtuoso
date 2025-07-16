"""
Comprehensive tests for the enhanced InterpretationManager with market context awareness.

This test suite verifies:
- Market context-aware interpretation processing
- Dynamic confidence scoring
- Component interaction analysis
- Enhanced formatting with market context
- Actionable insights generation
- Risk assessment and position sizing
"""

import pytest
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import numpy as np

from src.core.interpretation.interpretation_manager import InterpretationManager, MarketContext
from src.core.models.interpretation_schema import (
    ComponentInterpretation,
    MarketInterpretationSet,
    ComponentType,
    InterpretationSeverity
)


class TestEnhancedInterpretationManager(unittest.TestCase):
    """Test suite for enhanced interpretation manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = InterpretationManager()
        
        # Sample market data for different scenarios
        self.bullish_market_data = {
            'market_overview': {
                'regime': 'BULLISH',
                'volatility': 2.5,
                'trend_strength': 0.8,
                'volume_change': 15.0
            },
            'smart_money_index': {
                'index': 75.0
            },
            'whale_activity': {
                'sentiment': 'BULLISH'
            },
            'funding_rate': {
                'average': 0.0001
            }
        }
        
        self.bearish_high_vol_data = {
            'market_overview': {
                'regime': 'BEARISH',
                'volatility': 4.2,
                'trend_strength': 0.7,
                'volume_change': -20.0
            },
            'smart_money_index': {
                'index': 25.0
            },
            'whale_activity': {
                'sentiment': 'BEARISH'
            },
            'funding_rate': {
                'average': -0.0005
            }
        }
        
        self.ranging_market_data = {
            'market_overview': {
                'regime': 'RANGING',
                'volatility': 1.2,
                'trend_strength': 0.3,
                'volume_change': 2.0
            },
            'smart_money_index': {
                'index': 50.0
            },
            'whale_activity': {
                'sentiment': 'NEUTRAL'
            },
            'funding_rate': {
                'average': 0.0
            }
        }
    
    def test_market_context_creation(self):
        """Test MarketContext creation and derived properties."""
        context = MarketContext(self.bullish_market_data)
        
        self.assertEqual(context.regime, 'BULLISH')
        self.assertEqual(context.volatility, 2.5)
        self.assertEqual(context.smart_money_index, 75.0)
        self.assertEqual(context.institutional_bias, 'bullish')
        self.assertFalse(context.is_high_volatility)
        self.assertFalse(context.is_low_volatility)
        self.assertTrue(context.is_trending)
        self.assertFalse(context.is_ranging)
        
        # Test high volatility context
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        self.assertTrue(high_vol_context.is_high_volatility)
        self.assertEqual(high_vol_context.institutional_bias, 'bearish')
        
        # Test ranging context
        ranging_context = MarketContext(self.ranging_market_data)
        self.assertTrue(ranging_context.is_low_volatility)
        self.assertTrue(ranging_context.is_ranging)
        self.assertEqual(ranging_context.institutional_bias, 'neutral')
    
    def test_dynamic_confidence_scoring(self):
        """Test dynamic confidence scoring based on market context."""
        bullish_context = MarketContext(self.bullish_market_data)
        bearish_context = MarketContext(self.bearish_high_vol_data)
        
        # Test regime alignment boost
        bullish_text = "Strong bullish momentum with clear buy signals"
        bullish_confidence = self.manager._calculate_dynamic_confidence(
            bullish_text, "technical_rsi", bullish_context
        )
        
        # Same text in bearish context should have lower confidence
        bearish_confidence = self.manager._calculate_dynamic_confidence(
            bullish_text, "technical_rsi", bearish_context
        )
        
        self.assertGreater(bullish_confidence, bearish_confidence)
        
        # Test certainty analysis
        certain_text = "Strong and clear definitive bullish signal confirmed"
        uncertain_text = "Possible potential bullish signal might develop"
        
        certain_confidence = self.manager._calculate_dynamic_confidence(
            certain_text, "technical_macd", bullish_context
        )
        uncertain_confidence = self.manager._calculate_dynamic_confidence(
            uncertain_text, "technical_macd", bullish_context
        )
        
        self.assertGreater(certain_confidence, uncertain_confidence)
    
    def test_volatility_adjustment(self):
        """Test volatility-based confidence adjustments."""
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        low_vol_context = MarketContext(self.ranging_market_data)
        
        # Technical indicators should be boosted in high volatility
        tech_adjustment_high = self.manager._get_volatility_adjustment("technical_rsi", high_vol_context)
        tech_adjustment_low = self.manager._get_volatility_adjustment("technical_rsi", low_vol_context)
        
        self.assertGreater(tech_adjustment_high, tech_adjustment_low)
        
        # Sentiment indicators should be boosted in low volatility
        sentiment_adjustment_high = self.manager._get_volatility_adjustment("sentiment_funding", high_vol_context)
        sentiment_adjustment_low = self.manager._get_volatility_adjustment("sentiment_funding", low_vol_context)
        
        self.assertGreater(sentiment_adjustment_low, sentiment_adjustment_high)
    
    def test_component_interaction_analysis(self):
        """Test confluence and divergence detection."""
        # Create interpretations with bullish confluence
        bullish_interpretations = [
            ComponentInterpretation(
                component_type=ComponentType.TECHNICAL_INDICATOR,
                component_name="rsi_analysis",
                interpretation_text="Strong bullish momentum with RSI showing positive divergence",
                severity=InterpretationSeverity.INFO,
                confidence_score=0.8,
                timestamp=datetime.now()
            ),
            ComponentInterpretation(
                component_type=ComponentType.VOLUME_ANALYSIS,
                component_name="volume_analysis",
                interpretation_text="Significant buying pressure with strong volume confirmation",
                severity=InterpretationSeverity.INFO,
                confidence_score=0.75,
                timestamp=datetime.now()
            ),
            ComponentInterpretation(
                component_type=ComponentType.SENTIMENT_ANALYSIS,
                component_name="sentiment_analysis",
                interpretation_text="Bullish sentiment with positive funding rates",
                severity=InterpretationSeverity.INFO,
                confidence_score=0.7,
                timestamp=datetime.now()
            )
        ]
        
        enhanced = self.manager._analyze_component_interactions(bullish_interpretations)
        
        # Should detect confluence
        confluence_found = any('confluence' in interp.component_name.lower() for interp in enhanced)
        self.assertTrue(confluence_found)
        
        # Test divergence detection
        mixed_interpretations = [
            ComponentInterpretation(
                component_type=ComponentType.TECHNICAL_INDICATOR,
                component_name="rsi_analysis",
                interpretation_text="Bullish technical signals emerging",
                severity=InterpretationSeverity.INFO,
                confidence_score=0.8,
                timestamp=datetime.now()
            ),
            ComponentInterpretation(
                component_type=ComponentType.SENTIMENT_ANALYSIS,
                component_name="sentiment_analysis",
                interpretation_text="Bearish sentiment with negative funding",
                severity=InterpretationSeverity.WARNING,
                confidence_score=0.7,
                timestamp=datetime.now()
            ),
            ComponentInterpretation(
                component_type=ComponentType.VOLUME_ANALYSIS,
                component_name="volume_analysis",
                interpretation_text="Bearish volume patterns with selling pressure",
                severity=InterpretationSeverity.WARNING,
                confidence_score=0.75,
                timestamp=datetime.now()
            )
        ]
        
        enhanced_mixed = self.manager._analyze_component_interactions(mixed_interpretations)
        
        # Should detect divergence
        divergence_found = any('divergence' in interp.component_name.lower() for interp in enhanced_mixed)
        self.assertTrue(divergence_found)
    
    def test_market_context_enhancement(self):
        """Test market context enhancement of interpretations."""
        bullish_context = MarketContext(self.bullish_market_data)
        
        original_interpretation = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="rsi_analysis",
            interpretation_text="RSI showing oversold conditions",
            severity=InterpretationSeverity.INFO,
            confidence_score=0.6,
            timestamp=datetime.now()
        )
        
        enhanced = self.manager._enhance_with_market_context([original_interpretation], bullish_context)
        
        self.assertEqual(len(enhanced), 1)
        enhanced_interp = enhanced[0]
        
        # Check that market context was added to metadata
        self.assertEqual(enhanced_interp.metadata['market_regime'], 'BULLISH')
        self.assertEqual(enhanced_interp.metadata['institutional_bias'], 'bullish')
        self.assertTrue(enhanced_interp.metadata['context_enhanced'])
        
        # Check that interpretation text was enhanced
        self.assertIn('bullish momentum conditions', enhanced_interp.interpretation_text.lower())
    
    def test_severity_adjustment_with_context(self):
        """Test context-aware severity adjustment."""
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        
        # Warning in high volatility should become critical for certain keywords
        warning_severity = self.manager._infer_severity_with_context(
            "divergence breakdown pattern emerging", high_vol_context
        )
        
        # Should be elevated due to high volatility and critical keywords
        self.assertEqual(warning_severity, InterpretationSeverity.WARNING)
        
        # Counter-trend signals in trending markets should be elevated
        bullish_context = MarketContext(self.bullish_market_data)
        counter_trend_severity = self.manager._infer_severity_with_context(
            "bearish signals emerging", bullish_context
        )
        
        # Should be at least warning level
        self.assertIn(counter_trend_severity, [InterpretationSeverity.WARNING, InterpretationSeverity.CRITICAL])
    
    def test_enhanced_formatting(self):
        """Test enhanced formatting with market context."""
        bullish_context = MarketContext(self.bullish_market_data)
        
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="test_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="rsi_analysis",
                    interpretation_text="Strong bullish momentum detected",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.8,
                    timestamp=datetime.now(),
                    metadata={'context_enhanced': True, 'market_regime': 'BULLISH'}
                )
            ]
        )
        
        # Test text formatting
        text_output = self.manager.get_formatted_interpretation(
            interpretation_set, 'text', bullish_context
        )
        self.assertIn('BULLISH', text_output)
        self.assertIn('75.0', text_output)  # Smart money index
        self.assertIn('Institutional Bias: Bullish', text_output)
        
        # Test JSON formatting
        json_output = self.manager.get_formatted_interpretation(
            interpretation_set, 'json', bullish_context
        )
        self.assertIn('market_context', json_output)
        self.assertEqual(json_output['market_context']['regime'], 'BULLISH')
        self.assertEqual(json_output['market_context']['institutional_bias'], 'bullish')
        
        # Test actionable insights formatting
        actionable_output = self.manager.get_formatted_interpretation(
            interpretation_set, 'actionable', bullish_context
        )
        self.assertIn('overall_bias', actionable_output)
        self.assertIn('actionable_recommendations', actionable_output)
        self.assertIn('position_sizing_guidance', actionable_output)
    
    def test_actionable_insights_generation(self):
        """Test generation of actionable trading insights."""
        bullish_context = MarketContext(self.bullish_market_data)
        
        # Create high-confidence bullish interpretation set
        interpretation_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="confluence_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="technical_confluence",
                    interpretation_text="Strong bullish technical signals with momentum confirmation",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.85,
                    timestamp=datetime.now()
                ),
                ComponentInterpretation(
                    component_type=ComponentType.VOLUME_ANALYSIS,
                    component_name="volume_confirmation",
                    interpretation_text="Bullish volume patterns with strong buying pressure",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.8,
                    timestamp=datetime.now()
                )
            ]
        )
        
        insights = self.manager._format_as_actionable_insights(interpretation_set, bullish_context)
        
        # Verify key components
        self.assertEqual(insights['overall_bias'], 'bullish')
        self.assertGreater(insights['confidence_level'], 0.7)
        self.assertIn('actionable_recommendations', insights)
        self.assertIn('position_sizing_guidance', insights)
        self.assertIn('risk_management', insights)
        
        # Check recommendations contain actionable advice
        recommendations = insights['actionable_recommendations']
        self.assertTrue(any('long position' in rec.lower() for rec in recommendations))
        
        # Check position sizing guidance
        sizing = insights['position_sizing_guidance']
        self.assertIn('final_recommendation', sizing)
        self.assertIn('rationale', sizing)
    
    def test_risk_assessment(self):
        """Test risk level assessment based on interpretations and market context."""
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        
        # Create high-risk interpretation set
        high_risk_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="risk_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="breakdown_signal",
                    interpretation_text="Critical breakdown pattern with divergence signals",
                    severity=InterpretationSeverity.CRITICAL,
                    confidence_score=0.9,
                    timestamp=datetime.now()
                ),
                ComponentInterpretation(
                    component_type=ComponentType.GENERAL_ANALYSIS,
                    component_name="divergence_analysis",
                    interpretation_text="Significant divergence detected between components",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.8,
                    timestamp=datetime.now()
                )
            ]
        )
        
        risk_level = self.manager._assess_risk_level(high_risk_set, high_vol_context)
        self.assertEqual(risk_level, 'high')
        
        # Test low-risk scenario
        low_risk_context = MarketContext(self.ranging_market_data)
        low_risk_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="stable_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="stable_signal",
                    interpretation_text="Stable technical conditions with neutral bias",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.6,
                    timestamp=datetime.now()
                )
            ]
        )
        
        low_risk_level = self.manager._assess_risk_level(low_risk_set, low_risk_context)
        self.assertEqual(low_risk_level, 'low')
    
    def test_position_sizing_guidance(self):
        """Test position sizing guidance generation."""
        # High confidence, low risk scenario
        high_conf_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="high_conf_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="strong_signal",
                    interpretation_text="Very strong bullish signal with high certainty",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.9,
                    timestamp=datetime.now()
                )
            ]
        )
        
        low_vol_context = MarketContext(self.ranging_market_data)
        guidance = self.manager._generate_position_sizing_guidance(high_conf_set, low_vol_context)
        
        self.assertIn('Standard', guidance['base_size'])
        self.assertGreater(float(guidance['volatility_adjustment'].replace('x', '')), 1.0)  # Should be boosted for low vol
        
        # High volatility scenario should reduce position size
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        high_vol_guidance = self.manager._generate_position_sizing_guidance(high_conf_set, high_vol_context)
        
        high_vol_multiplier = float(high_vol_guidance['volatility_adjustment'].replace('x', ''))
        low_vol_multiplier = float(guidance['volatility_adjustment'].replace('x', ''))
        
        self.assertLess(high_vol_multiplier, low_vol_multiplier)
    
    def test_time_horizon_analysis(self):
        """Test time horizon analysis for different strategies."""
        high_vol_context = MarketContext(self.bearish_high_vol_data)
        
        # Technical + high volatility should be suitable for scalping
        tech_set = MarketInterpretationSet(
            timestamp=datetime.now(),
            source_component="technical_analyzer",
            interpretations=[
                ComponentInterpretation(
                    component_type=ComponentType.TECHNICAL_INDICATOR,
                    component_name="scalping_signal",
                    interpretation_text="Short-term technical signal",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.7,
                    timestamp=datetime.now()
                )
            ]
        )
        
        horizons = self.manager._analyze_time_horizons(tech_set, high_vol_context)
        self.assertIn('scalping', horizons)
        self.assertIn('Suitable', horizons['scalping'])
        
        # Trending market should be suitable for trend following
        bullish_context = MarketContext(self.bullish_market_data)
        trend_horizons = self.manager._analyze_time_horizons(tech_set, bullish_context)
        self.assertIn('trend_following', trend_horizons)
        self.assertIn('Suitable', trend_horizons['trend_following'])
    
    def test_processing_with_market_data(self):
        """Test end-to-end processing with market data."""
        # Test with various input formats and market context
        test_interpretations = {
            'technical': "Strong bullish momentum with RSI divergence",
            'volume': "Significant buying pressure detected",
            'sentiment': {"interpretation": "Positive funding rates indicate bullish sentiment"}
        }
        
        result = self.manager.process_interpretations(
            test_interpretations,
            "test_component",
            market_data=self.bullish_market_data
        )
        
        # Verify market context was applied
        self.assertTrue(result.metadata['enhancement_applied'])
        self.assertIsNotNone(result.metadata['market_context'])
        
        # Verify interpretations were enhanced
        enhanced_count = sum(1 for interp in result.interpretations 
                           if interp.metadata.get('context_enhanced', False))
        self.assertGreater(enhanced_count, 0)
        
        # Verify confluence analysis was performed
        self.assertTrue(result.metadata['confluence_analysis'])
    
    def test_processing_stats(self):
        """Test enhanced processing statistics."""
        # Process some interpretations to generate stats
        self.manager.process_interpretations(
            "Test interpretation",
            "test_component",
            market_data=self.bullish_market_data
        )
        
        stats = self.manager.get_processing_stats()
        
        # Verify enhanced stats are present
        self.assertIn('context_enhancements', stats)
        self.assertIn('confluence_detections', stats)
        self.assertIn('enhancement_rate', stats)
        self.assertIn('confluence_detection_rate', stats)
        self.assertIn('cache_size', stats)
        
        # Verify stats are reasonable
        self.assertGreaterEqual(stats['total_processed'], 1)
        self.assertGreaterEqual(stats['context_enhancements'], 1)
    
    def test_data_freshness_warnings(self):
        """Test data freshness warnings for stale interpretations."""
        # Create old interpretation
        old_interpretation = ComponentInterpretation(
            component_type=ComponentType.TECHNICAL_INDICATOR,
            component_name="old_signal",
            interpretation_text="Old technical signal",
            severity=InterpretationSeverity.INFO,
            confidence_score=0.7,
            timestamp=datetime.now() - timedelta(hours=2)  # 2 hours old
        )
        
        validated = self.manager._validate_interpretations([old_interpretation])
        
        # Should have freshness warning
        self.assertTrue(validated[0].metadata.get('freshness_warning', False))
        self.assertIn('[Note: Data may be stale]', validated[0].interpretation_text)


if __name__ == '__main__':
    unittest.main() 