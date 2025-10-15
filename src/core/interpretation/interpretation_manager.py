"""
Centralized Interpretation Management System

This module provides a unified interface for processing, validating, and distributing
market analysis interpretations across all output systems (alerts, PDFs, JSON exports).

Key Features:
- Standardized interpretation format validation
- Legacy format conversion and compatibility
- Consistent distribution to all output systems
- Centralized processing logic
- Error handling and fallback mechanisms
- Market context-aware interpretation processing
- Dynamic confidence scoring based on market conditions
- Component interaction analysis and confluence detection
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import json
import numpy as np

from src.core.models.interpretation_schema import (
    MarketInterpretationSet,
    ComponentInterpretation,
    ComponentType,
    InterpretationSeverity,
    ActionableInsight
)

logger = logging.getLogger(__name__)


class MarketContext:
    """Container for market context information used in interpretation processing."""
    
    def __init__(self, market_data: Dict[str, Any]):
        # Defensive programming: ensure market_data is a dictionary
        if not isinstance(market_data, dict):
            logger = logging.getLogger(__name__)
            logger.warning(f"MarketContext received non-dict market_data: {type(market_data)}, using defaults")
            market_data = {}
            
        # Handle regime - can be nested in market_overview or direct
        market_overview = market_data.get('market_overview', {})
        self.regime = (market_overview.get('regime') if isinstance(market_overview, dict) else market_data.get('regime')) or 'NEUTRAL'
        self.volatility = (market_overview.get('volatility') if isinstance(market_overview, dict) else market_data.get('volatility')) or 2.0
        self.trend_strength = (market_overview.get('trend_strength') if isinstance(market_overview, dict) else market_data.get('trend_strength')) or 0.5
        self.volume_change = (market_overview.get('volume_change') if isinstance(market_overview, dict) else market_data.get('volume_change')) or 0.0
        # Handle smart_money_index - can be either a float or a nested dict
        smart_money_data = market_data.get('smart_money_index', 50.0)
        if isinstance(smart_money_data, dict):
            self.smart_money_index = smart_money_data.get('index', 50.0)
        else:
            self.smart_money_index = float(smart_money_data)
        # Handle whale_sentiment - can be nested or direct
        whale_data = market_data.get('whale_activity', {})
        if isinstance(whale_data, dict):
            self.whale_sentiment = whale_data.get('sentiment', 'NEUTRAL')
        else:
            self.whale_sentiment = market_data.get('whale_sentiment', 'NEUTRAL')
        
        # Handle funding_rate - can be nested or direct
        funding_data = market_data.get('funding_rate', {})
        if isinstance(funding_data, dict):
            self.funding_rate = funding_data.get('average', 0.0)
        else:
            # Check if funding_rates is provided as a dict of exchanges
            funding_rates = market_data.get('funding_rates', {})
            if isinstance(funding_rates, dict) and funding_rates:
                # Average the funding rates from different exchanges
                self.funding_rate = sum(funding_rates.values()) / len(funding_rates)
            else:
                self.funding_rate = market_data.get('funding_rate', 0.0)
        self.timestamp = datetime.now()
        
        # Derived properties
        self.is_high_volatility = self.volatility > 3.0
        self.is_low_volatility = self.volatility < 1.5
        self.is_trending = self.regime in ['BULLISH', 'BEARISH']
        self.is_ranging = self.regime in ['RANGING', 'NEUTRAL']
        self.institutional_bias = 'bullish' if self.smart_money_index > 65 else 'bearish' if self.smart_money_index < 35 else 'neutral'


class InterpretationManager:
    """
    Enhanced centralized manager for all interpretation processing and distribution.
    
    This class handles:
    - Processing interpretations from various analysis components
    - Market context-aware interpretation enhancement
    - Dynamic confidence scoring based on market conditions
    - Component interaction analysis and confluence detection
    - Distributing interpretations to output systems consistently
    - Managing interpretation lifecycle and caching
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._interpretation_cache = {}
        self._processing_stats = {
            'total_processed': 0,
            'validation_errors': 0,
            'conversion_successes': 0,
            'distribution_errors': 0,
            'context_enhancements': 0,
            'confluence_detections': 0
        }
        
        # Market context-aware interpretation templates
        self._regime_templates = {
            'BULLISH': {
                'technical_bias': 'bullish momentum',
                'volume_emphasis': 'buying pressure',
                'sentiment_context': 'positive market sentiment',
                'risk_adjustment': 'favorable risk environment'
            },
            'BEARISH': {
                'technical_bias': 'bearish pressure',
                'volume_emphasis': 'selling pressure',
                'sentiment_context': 'negative market sentiment',
                'risk_adjustment': 'elevated risk environment'
            },
            'RANGING': {
                'technical_bias': 'range-bound conditions',
                'volume_emphasis': 'balanced participation',
                'sentiment_context': 'neutral market sentiment',
                'risk_adjustment': 'consolidation phase'
            },
            'NEUTRAL': {
                'technical_bias': 'neutral conditions',
                'volume_emphasis': 'typical participation',
                'sentiment_context': 'balanced market sentiment',
                'risk_adjustment': 'stable risk environment'
            }
        }
    
    def process_interpretations(
        self, 
        raw_interpretations: Any, 
        source_component: str,
        market_data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> MarketInterpretationSet:
        """
        Enhanced main entry point for processing interpretations with market context awareness.
        
        Args:
            raw_interpretations: Raw interpretation data in any format
            source_component: Name of the component generating interpretations
            market_data: Current market data for context-aware processing
            timestamp: Optional timestamp for the interpretations
            
        Returns:
            MarketInterpretationSet: Enhanced standardized interpretation set
            
        Raises:
            ValueError: If interpretations cannot be processed
        """
        try:
            self._processing_stats['total_processed'] += 1
            timestamp = timestamp or datetime.now()
            
            self.logger.debug(f"Processing interpretations from {source_component} with market context")
            
            # Create market context if available
            market_context = MarketContext(market_data) if market_data else None
            
            # Convert to standard format
            standardized = self._convert_to_standard_format(
                raw_interpretations, 
                source_component,
                market_context
            )
            
            # Validate the standardized interpretations
            validated_interpretations = self._validate_interpretations(standardized)
            
            # Apply market context enhancements
            if market_context:
                validated_interpretations = self._enhance_with_market_context(
                    validated_interpretations, 
                    market_context
                )
                self._processing_stats['context_enhancements'] += 1
            
            # Detect component interactions and confluence
            # Extract component scores if available in raw_interpretations
            component_scores = None
            if isinstance(raw_interpretations, dict) and 'components' in raw_interpretations:
                component_scores = raw_interpretations.get('components', {})
            elif isinstance(raw_interpretations, list):
                # Try to extract scores from list of dicts
                component_scores = {}
                for item in raw_interpretations:
                    if isinstance(item, dict) and 'component' in item:
                        comp_name = item.get('component')
                        comp_score = item.get('score')
                        if comp_name and comp_score is not None:
                            component_scores[comp_name] = comp_score

            validated_interpretations = self._analyze_component_interactions(
                validated_interpretations,
                market_context,
                component_scores if component_scores else None
            )
            
            # Create interpretation set
            interpretation_set = MarketInterpretationSet(
                timestamp=timestamp,
                source_component=source_component,
                interpretations=validated_interpretations,
                metadata={
                    'processing_timestamp': datetime.now(),
                    'market_context': market_context.__dict__ if market_context else None,
                    'enhancement_applied': market_context is not None,
                    'confluence_analysis': True
                }
            )
            
            # Cache the processed interpretations
            cache_key = f"{source_component}_{timestamp.isoformat()}"
            self._interpretation_cache[cache_key] = interpretation_set
            
            self.logger.info(
                f"Successfully processed {len(validated_interpretations)} "
                f"interpretations from {source_component} with market context enhancement"
            )
            
            return interpretation_set
            
        except Exception as e:
            self._processing_stats['validation_errors'] += 1
            self.logger.error(f"Failed to process interpretations from {source_component}: {e}")
            raise ValueError(f"Interpretation processing failed: {e}")
    
    def _convert_to_standard_format(
        self, 
        raw_data: Any, 
        source_component: str,
        market_context: Optional[MarketContext] = None
    ) -> List[ComponentInterpretation]:
        """
        Enhanced conversion with initial market context awareness.
        """
        try:
            interpretations = []
            
            # Handle None or empty data
            if not raw_data:
                return interpretations
            
            # Case 1: Simple string
            if isinstance(raw_data, str):
                interpretations.append(
                    ComponentInterpretation(
                        component_type=self._infer_component_type(source_component),
                        component_name=source_component,
                        interpretation_text=raw_data,
                        severity=self._infer_severity_with_context(raw_data, market_context),
                        confidence_score=self._calculate_dynamic_confidence(raw_data, source_component, market_context),
                        timestamp=datetime.now()
                    )
                )
            
            # Case 2: List of strings
            elif isinstance(raw_data, list):
                for i, item in enumerate(raw_data):
                    if isinstance(item, str):
                        interpretations.append(
                            ComponentInterpretation(
                                component_type=self._infer_component_type(source_component),
                                component_name=f"{source_component}_{i}",
                                interpretation_text=item,
                                severity=self._infer_severity_with_context(item, market_context),
                                confidence_score=self._calculate_dynamic_confidence(item, source_component, market_context),
                                timestamp=datetime.now()
                            )
                        )
                    elif isinstance(item, dict):
                        # Extract component name from dictionary if available
                        dict_component_name = item.get('component', f"{source_component}_{i}")
                        
                        # Use the actual component name instead of indexed name
                        interpretations.extend(
                            self._convert_dict_to_interpretations(item, dict_component_name, market_context)
                        )
            
            # Case 3: Dictionary formats
            elif isinstance(raw_data, dict):
                interpretations.extend(
                    self._convert_dict_to_interpretations(raw_data, source_component, market_context)
                )
            
            # Case 4: Already standardized
            elif isinstance(raw_data, ComponentInterpretation):
                # Still enhance with market context
                if market_context:
                    raw_data.confidence_score = self._calculate_dynamic_confidence(
                        raw_data.interpretation_text, 
                        raw_data.component_name, 
                        market_context
                    )
                interpretations.append(raw_data)
            
            elif isinstance(raw_data, MarketInterpretationSet):
                interpretations.extend(raw_data.interpretations)
            
            else:
                # Fallback: convert to string
                self.logger.warning(
                    f"Unknown interpretation format from {source_component}, "
                    f"converting to string: {type(raw_data)}"
                )
                interpretations.append(
                    ComponentInterpretation(
                        component_type=self._infer_component_type(source_component),
                        component_name=source_component,
                        interpretation_text=str(raw_data),
                        severity=InterpretationSeverity.WARNING,
                        confidence_score=0.3,
                        timestamp=datetime.now()
                    )
                )
            
            self._processing_stats['conversion_successes'] += 1
            return interpretations
            
        except Exception as e:
            self.logger.error(f"Failed to convert interpretations from {source_component}: {e}")
            # Return fallback interpretation
            return [
                ComponentInterpretation(
                    component_type=ComponentType.UNKNOWN,
                    component_name=source_component,
                    interpretation_text=f"Error processing interpretation: {str(e)}",
                    severity=InterpretationSeverity.ERROR,
                    confidence_score=0.0,
                    timestamp=datetime.now()
                )
            ]
    
    def _convert_dict_to_interpretations(
        self, 
        data_dict: Dict[str, Any], 
        source_component: str,
        market_context: Optional[MarketContext] = None
    ) -> List[ComponentInterpretation]:
        """Enhanced dictionary conversion with market context."""
        interpretations = []
        
        # Handle dict with 'interpretation' key
        if 'interpretation' in data_dict:
            interpretation_text = data_dict['interpretation']
            component_name = data_dict.get('component', source_component)
            
            if isinstance(interpretation_text, str):
                interpretations.append(
                    ComponentInterpretation(
                        component_type=self._infer_component_type(component_name),
                        component_name=component_name,
                        interpretation_text=interpretation_text,
                        severity=self._infer_severity_with_context(
                            data_dict.get('severity', interpretation_text), 
                            market_context
                        ),
                        confidence_score=self._calculate_dynamic_confidence(
                            interpretation_text, 
                            component_name, 
                            market_context,
                            base_confidence=data_dict.get('confidence', 0.5)
                        ),
                        timestamp=datetime.now(),
                        metadata=data_dict.get('metadata', {})
                    )
                )
            elif isinstance(interpretation_text, dict):
                # Handle nested interpretation dictionary
                for sub_key, sub_value in interpretation_text.items():
                    if isinstance(sub_value, str) and sub_value.strip():
                        interpretations.append(
                            ComponentInterpretation(
                                component_type=self._infer_component_type(f"{component_name}_{sub_key}"),
                                component_name=f"{component_name}_{sub_key}",
                                interpretation_text=sub_value,
                                severity=self._infer_severity_with_context(sub_value, market_context),
                                confidence_score=self._calculate_dynamic_confidence(
                                    sub_value, 
                                    f"{component_name}_{sub_key}", 
                                    market_context
                                ),
                                timestamp=datetime.now()
                            )
                        )
        
        # Handle component-name-keyed dictionaries
        else:
            for component_name, interpretation_data in data_dict.items():
                if isinstance(interpretation_data, str):
                    interpretations.append(
                        ComponentInterpretation(
                            component_type=self._infer_component_type(component_name),
                            component_name=component_name,
                            interpretation_text=interpretation_data,
                            severity=self._infer_severity_with_context(interpretation_data, market_context),
                            confidence_score=self._calculate_dynamic_confidence(
                                interpretation_data, 
                                component_name, 
                                market_context
                            ),
                            timestamp=datetime.now()
                        )
                    )
                elif isinstance(interpretation_data, dict):
                    # Handle nested interpretation structures
                    if 'text' in interpretation_data or 'interpretation' in interpretation_data:
                        # Standard nested format
                        nested_text = interpretation_data.get('text', 
                                                            interpretation_data.get('interpretation', 
                                                                                   str(interpretation_data)))
                        interpretations.append(
                            ComponentInterpretation(
                                component_type=self._infer_component_type(component_name),
                                component_name=component_name,
                                interpretation_text=nested_text,
                                severity=self._infer_severity_with_context(
                                    interpretation_data.get('severity', nested_text), 
                                    market_context
                                ),
                                confidence_score=self._calculate_dynamic_confidence(
                                    nested_text, 
                                    component_name, 
                                    market_context,
                                    base_confidence=interpretation_data.get('confidence', 0.5)
                                ),
                                timestamp=datetime.now(),
                                metadata=interpretation_data.get('metadata', {})
                            )
                        )
                    else:
                        # Dictionary with multiple sub-interpretations
                        for sub_key, sub_value in interpretation_data.items():
                            if isinstance(sub_value, str) and sub_value.strip():
                                interpretations.append(
                                    ComponentInterpretation(
                                        component_type=self._infer_component_type(f"{component_name}_{sub_key}"),
                                        component_name=f"{component_name}_{sub_key}",
                                        interpretation_text=sub_value,
                                        severity=self._infer_severity_with_context(sub_value, market_context),
                                        confidence_score=self._calculate_dynamic_confidence(
                                            sub_value, 
                                            f"{component_name}_{sub_key}", 
                                            market_context
                                        ),
                                        timestamp=datetime.now()
                                    )
                                )
        
        return interpretations
    
    def _calculate_dynamic_confidence(
        self, 
        interpretation_text: str, 
        component_name: str, 
        market_context: Optional[MarketContext] = None,
        base_confidence: float = 0.5
    ) -> float:
        """
        Calculate dynamic confidence score based on multiple factors.
        
        Factors considered:
        - Market volatility (higher volatility = lower confidence for mean reversion, higher for momentum)
        - Market regime alignment (interpretations aligned with regime get higher confidence)
        - Component type reliability in current conditions
        - Text content analysis (certainty indicators)
        - Data freshness (if available)
        """
        try:
            confidence = base_confidence
            
            if not market_context:
                return confidence
            
            # Factor 1: Market regime alignment
            regime_alignment = self._assess_regime_alignment(interpretation_text, component_name, market_context)
            confidence *= (1.0 + regime_alignment * 0.3)  # Up to 30% boost for alignment
            
            # Factor 2: Volatility adjustment based on component type
            volatility_adjustment = self._get_volatility_adjustment(component_name, market_context)
            confidence *= volatility_adjustment
            
            # Factor 3: Text certainty analysis
            certainty_boost = self._analyze_text_certainty(interpretation_text)
            confidence *= (1.0 + certainty_boost * 0.2)  # Up to 20% boost for certain language
            
            # Factor 4: Component reliability in current market conditions
            reliability_factor = self._get_component_reliability(component_name, market_context)
            confidence *= reliability_factor
            
            # Factor 5: Institutional alignment (if smart money agrees, boost confidence)
            if market_context.institutional_bias != 'neutral':
                institutional_alignment = self._assess_institutional_alignment(
                    interpretation_text, 
                    market_context.institutional_bias
                )
                confidence *= (1.0 + institutional_alignment * 0.15)  # Up to 15% boost
            
            # Ensure confidence stays within bounds
            confidence = max(0.1, min(0.95, confidence))
            
            return confidence
            
        except Exception as e:
            self.logger.warning(f"Error calculating dynamic confidence: {e}")
            return base_confidence
    
    def _assess_regime_alignment(
        self, 
        interpretation_text: str, 
        component_name: str, 
        market_context: MarketContext
    ) -> float:
        """Assess how well the interpretation aligns with current market regime."""
        text_lower = interpretation_text.lower()
        regime = market_context.regime
        
        # Define alignment keywords for each regime
        bullish_keywords = ['bullish', 'buy', 'long', 'upward', 'positive', 'strength', 'momentum up']
        bearish_keywords = ['bearish', 'sell', 'short', 'downward', 'negative', 'weakness', 'momentum down']
        neutral_keywords = ['neutral', 'sideways', 'range', 'consolidation', 'balanced']
        
        bullish_score = sum(1 for word in bullish_keywords if word in text_lower)
        bearish_score = sum(1 for word in bearish_keywords if word in text_lower)
        neutral_score = sum(1 for word in neutral_keywords if word in text_lower)
        
        if regime == 'BULLISH':
            return (bullish_score - bearish_score) / max(1, bullish_score + bearish_score + neutral_score)
        elif regime == 'BEARISH':
            return (bearish_score - bullish_score) / max(1, bullish_score + bearish_score + neutral_score)
        elif regime in ['RANGING', 'NEUTRAL']:
            return neutral_score / max(1, bullish_score + bearish_score + neutral_score)
        
        return 0.0
    
    def _get_volatility_adjustment(self, component_name: str, market_context: MarketContext) -> float:
        """Adjust confidence based on volatility and component type."""
        component_type = self._infer_component_type(component_name)
        
        # Different components have different reliability in different volatility regimes
        if market_context.is_high_volatility:
            # High volatility: momentum indicators more reliable, mean reversion less reliable
            if component_type in [ComponentType.TECHNICAL_INDICATOR, ComponentType.VOLUME_ANALYSIS]:
                return 1.1  # Boost technical and volume in high volatility
            elif component_type == ComponentType.SENTIMENT_ANALYSIS:
                return 0.9  # Reduce sentiment reliability in high volatility
            else:
                return 1.0
        elif market_context.is_low_volatility:
            # Low volatility: mean reversion more reliable, momentum less reliable
            if component_type == ComponentType.SENTIMENT_ANALYSIS:
                return 1.1  # Boost sentiment in low volatility
            elif component_type in [ComponentType.TECHNICAL_INDICATOR, ComponentType.VOLUME_ANALYSIS]:
                return 0.9  # Reduce momentum indicators in low volatility
            else:
                return 1.0
        else:
            return 1.0  # Normal volatility, no adjustment
    
    def _analyze_text_certainty(self, text: str) -> float:
        """Analyze text for certainty indicators."""
        text_lower = text.lower()
        
        # High certainty indicators
        high_certainty = ['strong', 'clear', 'definitive', 'confirmed', 'significant', 'obvious']
        # Low certainty indicators
        low_certainty = ['possible', 'potential', 'might', 'could', 'uncertain', 'unclear', 'mixed']
        
        high_score = sum(1 for word in high_certainty if word in text_lower)
        low_score = sum(1 for word in low_certainty if word in text_lower)
        
        # Return certainty boost (-0.3 to +0.3)
        return (high_score - low_score) / max(1, high_score + low_score) * 0.3
    
    def _get_component_reliability(self, component_name: str, market_context: MarketContext) -> float:
        """Get component reliability factor based on current market conditions."""
        component_type = self._infer_component_type(component_name)
        
        # Base reliability scores for different components
        base_reliability = {
            ComponentType.TECHNICAL_INDICATOR: 0.8,
            ComponentType.VOLUME_ANALYSIS: 0.85,
            ComponentType.SENTIMENT_ANALYSIS: 0.7,
            ComponentType.FUNDING_ANALYSIS: 0.9,
            ComponentType.WHALE_ANALYSIS: 0.75,
            ComponentType.PRICE_ANALYSIS: 0.8,
            ComponentType.GENERAL_ANALYSIS: 0.6
        }
        
        reliability = base_reliability.get(component_type, 0.7)
        
        # Adjust based on market conditions
        if market_context.is_trending:
            # In trending markets, momentum indicators are more reliable
            if component_type in [ComponentType.TECHNICAL_INDICATOR, ComponentType.VOLUME_ANALYSIS]:
                reliability *= 1.1
        elif market_context.is_ranging:
            # In ranging markets, mean reversion, sentiment, and range analysis are more reliable
            if component_type == ComponentType.SENTIMENT_ANALYSIS:
                reliability *= 1.1
            elif component_type == ComponentType.PRICE_ANALYSIS and 'range' in component_name.lower():
                reliability *= 1.2  # Range analysis is highly reliable in ranging markets
        
        return reliability
    
    def _assess_institutional_alignment(self, interpretation_text: str, institutional_bias: str) -> float:
        """Assess alignment with institutional/smart money bias."""
        text_lower = interpretation_text.lower()
        
        if institutional_bias == 'bullish':
            bullish_words = ['bullish', 'buy', 'long', 'positive', 'strength']
            return 0.3 if any(word in text_lower for word in bullish_words) else -0.1
        elif institutional_bias == 'bearish':
            bearish_words = ['bearish', 'sell', 'short', 'negative', 'weakness']
            return 0.3 if any(word in text_lower for word in bearish_words) else -0.1
        
        return 0.0
    
    def _enhance_with_market_context(
        self, 
        interpretations: List[ComponentInterpretation],
        market_context: MarketContext
    ) -> List[ComponentInterpretation]:
        """Enhance interpretations with market context-aware language and insights."""
        enhanced_interpretations = []
        
        for interpretation in interpretations:
            try:
                # Create enhanced copy
                enhanced = ComponentInterpretation(
                    component_type=interpretation.component_type,
                    component_name=interpretation.component_name,
                    interpretation_text=self._enhance_interpretation_text(
                        interpretation.interpretation_text,
                        interpretation.component_type,
                        market_context
                    ),
                    severity=interpretation.severity,
                    confidence_score=interpretation.confidence_score,
                    timestamp=interpretation.timestamp,
                    metadata={
                        **interpretation.metadata,
                        'market_regime': market_context.regime,
                        'volatility_regime': 'high' if market_context.is_high_volatility else 'low' if market_context.is_low_volatility else 'normal',
                        'institutional_bias': market_context.institutional_bias,
                        'context_enhanced': True
                    }
                )
                
                enhanced_interpretations.append(enhanced)
                
            except Exception as e:
                self.logger.warning(f"Failed to enhance interpretation: {e}")
                enhanced_interpretations.append(interpretation)  # Use original if enhancement fails
        
        return enhanced_interpretations
    
    def _enhance_interpretation_text(
        self, 
        original_text: str, 
        component_type: ComponentType,
        market_context: MarketContext
    ) -> str:
        """Enhance interpretation text with market context."""
        try:
            # Get regime-specific templates
            regime_template = self._regime_templates.get(market_context.regime, self._regime_templates['NEUTRAL'])
            
            # Add market context prefix based on component type and market conditions
            context_prefix = self._generate_context_prefix(component_type, market_context, regime_template)
            
            # Add volatility context if relevant
            volatility_context = self._generate_volatility_context(market_context)
            
            # Add institutional context if relevant
            institutional_context = self._generate_institutional_context(market_context)
            
            # Combine contexts
            enhanced_text = original_text
            
            if context_prefix:
                enhanced_text = f"{context_prefix} {enhanced_text}"
            
            if volatility_context:
                enhanced_text = f"{enhanced_text} {volatility_context}"
            
            if institutional_context:
                enhanced_text = f"{enhanced_text} {institutional_context}"
            
            return enhanced_text
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance interpretation text: {e}")
            return original_text
    
    def _generate_context_prefix(
        self, 
        component_type: ComponentType, 
        market_context: MarketContext,
        regime_template: Dict[str, str]
    ) -> str:
        """Generate context-aware prefix for interpretations."""
        if component_type == ComponentType.TECHNICAL_INDICATOR:
            return f"In current {regime_template['technical_bias']} conditions:"
        elif component_type == ComponentType.VOLUME_ANALYSIS:
            return f"With {regime_template['volume_emphasis']} evident:"
        elif component_type == ComponentType.SENTIMENT_ANALYSIS:
            return f"Given {regime_template['sentiment_context']}:"
        elif component_type in [ComponentType.FUNDING_ANALYSIS, ComponentType.WHALE_ANALYSIS]:
            return f"In this {regime_template['risk_adjustment']}:"
        else:
            return f"Under {market_context.regime.lower()} market conditions:"
    
    def _generate_volatility_context(self, market_context: MarketContext) -> str:
        """Generate volatility-specific context."""
        if market_context.is_high_volatility:
            return "Note: High volatility environment increases both opportunity and risk."
        elif market_context.is_low_volatility:
            return "Note: Low volatility suggests potential for breakout or continued consolidation."
        return ""
    
    def _generate_institutional_context(self, market_context: MarketContext) -> str:
        """Generate institutional/smart money context."""
        if market_context.institutional_bias == 'bullish':
            return f"Smart money index ({market_context.smart_money_index:.1f}) suggests institutional bullish bias."
        elif market_context.institutional_bias == 'bearish':
            return f"Smart money index ({market_context.smart_money_index:.1f}) suggests institutional bearish bias."
        return ""
    
    def _analyze_component_interactions(
        self,
        interpretations: List[ComponentInterpretation],
        market_context: Optional[MarketContext] = None,
        component_scores: Optional[Dict[str, float]] = None
    ) -> List[ComponentInterpretation]:
        """Analyze interactions between components and detect confluence/divergence.

        Args:
            interpretations: List of component interpretations
            market_context: Optional market context
            component_scores: Optional dict of component names to scores (0-100)
                            Used for accurate confluence detection instead of text keywords
        """
        if len(interpretations) < 2:
            return interpretations

        try:
            # Group components by sentiment using SCORES if available, otherwise text
            bullish_components = []
            bearish_components = []
            neutral_components = []

            if component_scores:
                # Use actual component scores for accurate detection
                for interp in interpretations:
                    comp_name = interp.component_name
                    score = component_scores.get(comp_name, 50)

                    if score > 55:
                        bullish_components.append(interp)
                    elif score < 45:
                        bearish_components.append(interp)
                    else:
                        neutral_components.append(interp)
            else:
                # Fallback to text keyword matching (legacy behavior)
                for interp in interpretations:
                    text_lower = interp.interpretation_text.lower()
                    if any(word in text_lower for word in ['bullish', 'buy', 'long', 'positive', 'strength']):
                        bullish_components.append(interp)
                    elif any(word in text_lower for word in ['bearish', 'sell', 'short', 'negative', 'weakness']):
                        bearish_components.append(interp)
                    else:
                        neutral_components.append(interp)

            # Detect confluence (3+ components agreeing)
            confluence_detected = False
            confluence_direction = None

            if len(bullish_components) >= 3:
                confluence_detected = True
                confluence_direction = 'bullish'
                self._processing_stats['confluence_detections'] += 1
            elif len(bearish_components) >= 3:
                confluence_detected = True
                confluence_direction = 'bearish'
                self._processing_stats['confluence_detections'] += 1
            
            # Add confluence/divergence insights
            enhanced_interpretations = interpretations.copy()
            
            if confluence_detected:
                confluence_insight = ComponentInterpretation(
                    component_type=ComponentType.GENERAL_ANALYSIS,
                    component_name="confluence_analysis",
                    interpretation_text=f"CONFLUENCE DETECTED: Multiple components ({len(bullish_components if confluence_direction == 'bullish' else bearish_components)}) align on {confluence_direction} bias, increasing signal reliability.",
                    severity=InterpretationSeverity.INFO,
                    confidence_score=0.85,
                    timestamp=datetime.now(),
                    metadata={
                        'confluence_type': confluence_direction,
                        'component_count': len(bullish_components if confluence_direction == 'bullish' else bearish_components),
                        'analysis_type': 'confluence'
                    }
                )
                enhanced_interpretations.append(confluence_insight)
            
            # Detect significant divergence
            elif len(bullish_components) >= 1 and len(bearish_components) >= 1:
                divergence_insight = ComponentInterpretation(
                    component_type=ComponentType.GENERAL_ANALYSIS,
                    component_name="divergence_analysis",
                    interpretation_text=f"MIXED SIGNALS: Components show divergence ({len(bullish_components)} bullish vs {len(bearish_components)} bearish), suggesting market uncertainty or transition phase.",
                    severity=InterpretationSeverity.WARNING,
                    confidence_score=0.6,
                    timestamp=datetime.now(),
                    metadata={
                        'bullish_count': len(bullish_components),
                        'bearish_count': len(bearish_components),
                        'analysis_type': 'divergence'
                    }
                )
                enhanced_interpretations.append(divergence_insight)
            
            return enhanced_interpretations
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze component interactions: {e}")
            return interpretations
    
    def _validate_interpretations(
        self, 
        interpretations: List[ComponentInterpretation]
    ) -> List[ComponentInterpretation]:
        """Enhanced validation with market context considerations."""
        validated = []
        
        for interpretation in interpretations:
            try:
                # Validate required fields
                if not interpretation.interpretation_text:
                    self.logger.warning(f"Empty interpretation text for {interpretation.component_name}")
                    continue
                
                # Ensure text is reasonable length
                if len(interpretation.interpretation_text) > 10000:
                    interpretation.interpretation_text = interpretation.interpretation_text[:10000] + "..."
                    self.logger.warning(f"Truncated long interpretation for {interpretation.component_name}")
                
                # Validate confidence score
                if not 0 <= interpretation.confidence_score <= 1:
                    interpretation.confidence_score = max(0, min(1, interpretation.confidence_score))
                
                # Add data freshness warning if timestamp is old
                if interpretation.timestamp < datetime.now() - timedelta(hours=1):
                    interpretation.metadata['freshness_warning'] = True
                    interpretation.interpretation_text += " [Note: Data may be stale]"
                
                validated.append(interpretation)
                
            except Exception as e:
                self.logger.error(f"Failed to validate interpretation: {e}")
                continue
        
        return validated
    
    def _infer_severity_with_context(
        self, 
        severity_input: Union[str, int], 
        market_context: Optional[MarketContext] = None
    ) -> InterpretationSeverity:
        """Enhanced severity inference with market context."""
        base_severity = self._infer_severity(severity_input)
        
        if not market_context:
            return base_severity
        
        # Adjust severity based on market conditions
        if isinstance(severity_input, str):
            text_lower = severity_input.lower()
            
            # In high volatility, warnings become more critical
            if market_context.is_high_volatility:
                if any(word in text_lower for word in ['divergence', 'breakdown', 'reversal']):
                    if base_severity == InterpretationSeverity.INFO:
                        return InterpretationSeverity.WARNING
                    elif base_severity == InterpretationSeverity.WARNING:
                        return InterpretationSeverity.CRITICAL
            
            # In trending markets, counter-trend signals are more critical
            if market_context.is_trending:
                regime_lower = market_context.regime.lower()
                if ('bullish' in regime_lower and any(word in text_lower for word in ['bearish', 'sell', 'short'])) or \
                   ('bearish' in regime_lower and any(word in text_lower for word in ['bullish', 'buy', 'long'])):
                    if base_severity == InterpretationSeverity.INFO:
                        return InterpretationSeverity.WARNING
        
        return base_severity
    
    def _infer_component_type(self, component_name: str) -> ComponentType:
        """Infer component type from component name."""
        name_lower = component_name.lower()
        
        # Handle signal prefix components by extracting the actual component name
        if name_lower.startswith('signal_'):
            # Extract the component type from signal_symbol_number format
            parts = name_lower.split('_')
            if len(parts) >= 3:
                # For signal_btcusdt_0, we need to infer from context or use general
                # But this is typically used for overall signal analysis
                return ComponentType.GENERAL_ANALYSIS
        
        # CRITICAL FIX: Add explicit mapping for exact component names passed by signal generator
        # These are the exact component names used in the signal generation process
        if name_lower == 'technical':
            return ComponentType.TECHNICAL_INDICATOR
        elif name_lower == 'volume':
            return ComponentType.VOLUME_ANALYSIS
        elif name_lower == 'sentiment':
            return ComponentType.SENTIMENT_ANALYSIS
        elif name_lower == 'orderbook':
            return ComponentType.VOLUME_ANALYSIS  # Orderbook is part of volume analysis
        elif name_lower == 'orderflow':
            return ComponentType.VOLUME_ANALYSIS  # Orderflow is part of volume analysis
        elif name_lower == 'price_structure':
            return ComponentType.PRICE_ANALYSIS
        elif name_lower == 'funding':
            return ComponentType.FUNDING_ANALYSIS
        elif name_lower == 'whale':
            return ComponentType.WHALE_ANALYSIS
        elif name_lower == 'futures_premium':
            return ComponentType.FUNDING_ANALYSIS  # Futures premium is part of funding analysis
        
        # Extended exact matches for common variations
        elif name_lower in ['technical_indicator', 'technical_analysis']:
            return ComponentType.TECHNICAL_INDICATOR
        elif name_lower in ['volume_analysis', 'volume_indicator']:
            return ComponentType.VOLUME_ANALYSIS
        elif name_lower in ['sentiment_analysis', 'sentiment_indicator']:
            return ComponentType.SENTIMENT_ANALYSIS
        elif name_lower in ['price', 'price_analysis', 'price_structure_analysis']:
            return ComponentType.PRICE_ANALYSIS
        elif name_lower in ['funding_analysis', 'funding_rate']:
            return ComponentType.FUNDING_ANALYSIS
        elif name_lower in ['whale_analysis', 'whale_activity']:
            return ComponentType.WHALE_ANALYSIS
        elif name_lower in ['overall_analysis', 'general_analysis', 'confluence_analysis', 'divergence_analysis']:
            return ComponentType.GENERAL_ANALYSIS
        
        # Then check for keyword matches within the name (for more complex component names)
        elif any(term in name_lower for term in ['technical', 'rsi', 'macd', 'bollinger', 'sma', 'ema', 'stochastic', 'williams', 'cci', 'atr', 'ao']):
            return ComponentType.TECHNICAL_INDICATOR
        elif any(term in name_lower for term in ['sentiment', 'fear', 'greed', 'social', 'long_short', 'liquidation', 'risk', 'volatility', 'market_activity', 'activity']):
            return ComponentType.SENTIMENT_ANALYSIS
        elif any(term in name_lower for term in ['funding', 'rate', 'premium', 'futures']):
            return ComponentType.FUNDING_ANALYSIS
        elif any(term in name_lower for term in ['volume', 'liquidity', 'buying', 'selling', 'delta', 'cvd', 'obv', 'adl', 'cmf', 'vwap', 'relative_volume', 'volume_profile']):
            return ComponentType.VOLUME_ANALYSIS
        elif any(term in name_lower for term in ['orderbook', 'spread', 'depth', 'imbalance', 'obps', 'bid', 'ask', 'mpi', 'absorption', 'exhaustion', 'dom']):
            return ComponentType.VOLUME_ANALYSIS  # Orderbook is part of volume analysis
        elif any(term in name_lower for term in ['orderflow', 'flow', 'aggressor', 'taker', 'open_interest', 'pressure', 'trade_flow', 'smart_money_flow']):
            return ComponentType.VOLUME_ANALYSIS  # Orderflow is part of volume analysis
        elif any(term in name_lower for term in ['price', 'trend', 'support', 'resistance', 'level', 'structure', 'order_block', 'composite', 'fair_value', 'fvg', 'bos', 'choch', 'swing', 'range']):
            return ComponentType.PRICE_ANALYSIS
        elif any(term in name_lower for term in ['whale', 'large', 'order', 'institutional']):
            return ComponentType.WHALE_ANALYSIS
        else:
            # Only use GENERAL_ANALYSIS as a last resort
            self.logger.debug(f"Component '{component_name}' did not match any specific type, using GENERAL_ANALYSIS")
            return ComponentType.GENERAL_ANALYSIS
    
    def _infer_severity(self, severity_input: Union[str, int]) -> InterpretationSeverity:
        """Convert various severity formats to standard enum."""
        if isinstance(severity_input, str):
            severity_lower = severity_input.lower()
            if severity_lower in ['critical', 'high', 'error']:
                return InterpretationSeverity.CRITICAL
            elif severity_lower in ['warning', 'warn', 'medium']:
                return InterpretationSeverity.WARNING
            elif severity_lower in ['info', 'information', 'low']:
                return InterpretationSeverity.INFO
            else:
                return InterpretationSeverity.INFO
        elif isinstance(severity_input, int):
            if severity_input >= 3:
                return InterpretationSeverity.CRITICAL
            elif severity_input >= 2:
                return InterpretationSeverity.WARNING
            else:
                return InterpretationSeverity.INFO
        else:
            return InterpretationSeverity.INFO
    
    def get_formatted_interpretation(
        self, 
        interpretation_set: MarketInterpretationSet,
        output_format: str = 'text',
        market_context: Optional[MarketContext] = None
    ) -> Union[str, Dict[str, Any], List[str]]:
        """
        Enhanced format interpretations for specific output systems with market context.
        
        Args:
            interpretation_set: The interpretation set to format
            output_format: Target format ('text', 'json', 'alert', 'pdf', 'actionable')
            market_context: Optional market context for enhanced formatting
            
        Returns:
            Formatted interpretation data
        """
        try:
            if output_format == 'text':
                return self._format_as_text(interpretation_set, market_context)
            elif output_format == 'json':
                return self._format_as_json(interpretation_set, market_context)
            elif output_format == 'alert':
                return self._format_for_alerts(interpretation_set, market_context)
            elif output_format == 'pdf':
                return self._format_for_pdf(interpretation_set, market_context)
            elif output_format == 'actionable':
                return self._format_as_actionable_insights(interpretation_set, market_context)
            elif output_format == 'enhanced':
                # Return just the enhanced synthesis for direct use
                return self._generate_enhanced_synthesis(interpretation_set)
            else:
                self.logger.warning(f"Unknown output format: {output_format}")
                return self._format_as_text(interpretation_set, market_context)
                
        except Exception as e:
            self.logger.error(f"Failed to format interpretations: {e}")
            return f"Error formatting interpretations: {e}"
    
    def _format_as_text(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> str:
        """Enhanced format interpretations as plain text with market context."""
        lines = []
        lines.append(f"Market Analysis - {interpretation_set.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Source: {interpretation_set.source_component}")
        
        # Add market context header if available
        if market_context:
            lines.append(f"Market Regime: {market_context.regime} | Volatility: {market_context.volatility:.1f}")
            lines.append(f"Smart Money Index: {market_context.smart_money_index:.1f} | Institutional Bias: {market_context.institutional_bias.title()}")
        
        lines.append("-" * 70)
        
        # Group interpretations by type for better organization
        grouped_interpretations = {}
        for interpretation in interpretation_set.interpretations:
            component_type = interpretation.component_type.value
            if component_type not in grouped_interpretations:
                grouped_interpretations[component_type] = []
            grouped_interpretations[component_type].append(interpretation)
        
        # Display interpretations by type
        for component_type, interpretations in grouped_interpretations.items():
            lines.append(f"\n📊 {component_type.upper().replace('_', ' ')} ANALYSIS:")
            lines.append("-" * 40)
            
            for interpretation in interpretations:
                severity_indicator = {
                    InterpretationSeverity.CRITICAL: "🔴 CRITICAL",
                    InterpretationSeverity.WARNING: "🟡 WARNING", 
                    InterpretationSeverity.INFO: "🔵 INFO"
                }.get(interpretation.severity, "⚪ UNKNOWN")
                
                confidence_indicator = "🟢" if interpretation.confidence_score > 0.7 else "🟡" if interpretation.confidence_score > 0.4 else "🔴"
                
                lines.append(f"\n{severity_indicator} | {interpretation.component_name}")
                lines.append(f"   {interpretation.interpretation_text}")
                lines.append(f"   Confidence: {confidence_indicator} {interpretation.confidence_score:.1%}")
                
                # Add market context metadata if available
                if 'market_regime' in interpretation.metadata:
                    lines.append(f"   Market Context: {interpretation.metadata['market_regime']} | {interpretation.metadata.get('volatility_regime', 'normal')} volatility")
        
        # Add summary insights
        lines.append("\n" + "=" * 70)
        lines.append("SUMMARY INSIGHTS:")
        lines.append(self._generate_enhanced_summary(interpretation_set, market_context))
        
        return "\n".join(lines)
    
    def _format_as_json(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> Dict[str, Any]:
        """Enhanced format interpretations as JSON-serializable dictionary with market context."""
        # Helper function to make datetime objects JSON serializable
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj
        
        # Process metadata to handle datetime objects
        serialized_metadata = {}
        for key, value in interpretation_set.metadata.items():
            serialized_metadata[key] = serialize_datetime(value)
        
        # Add market context to metadata if available
        if market_context:
            serialized_metadata['market_context'] = {
                'regime': market_context.regime,
                'volatility': market_context.volatility,
                'trend_strength': market_context.trend_strength,
                'smart_money_index': market_context.smart_money_index,
                'institutional_bias': market_context.institutional_bias,
                'is_high_volatility': market_context.is_high_volatility,
                'is_trending': market_context.is_trending
            }
        
        return {
            'timestamp': interpretation_set.timestamp.isoformat(),
            'source_component': interpretation_set.source_component,
            'market_context': serialized_metadata.get('market_context'),
            'interpretations': [
                {
                    'component_type': interpretation.component_type.value,
                    'component_name': interpretation.component_name,
                    'interpretation_text': interpretation.interpretation_text,
                    'severity': interpretation.severity.value,
                    'confidence_score': interpretation.confidence_score,
                    'timestamp': interpretation.timestamp.isoformat(),
                    'metadata': {k: serialize_datetime(v) for k, v in interpretation.metadata.items()}
                }
                for interpretation in interpretation_set.interpretations
            ],
            'summary': self._generate_enhanced_summary(interpretation_set, market_context),
            'statistics': self._generate_interpretation_statistics(interpretation_set),
            'metadata': serialized_metadata
        }
    
    def _format_for_alerts(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> List[Dict[str, Any]]:
        """Enhanced format interpretations for alert system with market context."""
        alerts = []
        
        for interpretation in interpretation_set.interpretations:
            # Create alerts for warning and critical interpretations, plus high-confidence info
            should_alert = (
                interpretation.severity in [InterpretationSeverity.WARNING, InterpretationSeverity.CRITICAL] or
                (interpretation.severity == InterpretationSeverity.INFO and interpretation.confidence_score > 0.8)
            )
            
            if should_alert:
                alert_priority = 'high' if interpretation.severity == InterpretationSeverity.CRITICAL else 'medium'
                
                # Enhance alert message with market context
                alert_message = interpretation.interpretation_text
                if market_context:
                    alert_message += f" [Market: {market_context.regime}, Vol: {market_context.volatility:.1f}]"
                
                alerts.append({
                    'title': f"{interpretation.component_name} Alert",
                    'message': alert_message,
                    'severity': interpretation.severity.value,
                    'priority': alert_priority,
                    'confidence': interpretation.confidence_score,
                    'timestamp': interpretation.timestamp.isoformat(),
                    'component': interpretation.component_name,
                    'type': interpretation.component_type.value,
                    'market_context': {
                        'regime': market_context.regime if market_context else 'unknown',
                        'volatility': market_context.volatility if market_context else 0,
                        'institutional_bias': market_context.institutional_bias if market_context else 'neutral'
                    }
                })
        
        return alerts
    
    def _format_for_pdf(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> Dict[str, Any]:
        """Enhanced format interpretations for PDF generation with market context."""
        return {
            'title': f"Market Analysis Report - {interpretation_set.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            'source': interpretation_set.source_component,
            'market_context': {
                'regime': market_context.regime if market_context else 'Unknown',
                'volatility': f"{market_context.volatility:.1f}" if market_context else 'Unknown',
                'trend_strength': f"{market_context.trend_strength:.1%}" if market_context else 'Unknown',
                'smart_money_index': f"{market_context.smart_money_index:.1f}" if market_context else 'Unknown',
                'institutional_bias': market_context.institutional_bias.title() if market_context else 'Unknown'
            },
            'sections': [
                {
                    'component_name': interpretation.component_name,
                    'component_type': interpretation.component_type.value,
                    'content': interpretation.interpretation_text,
                    'severity': interpretation.severity.value,
                    'confidence': interpretation.confidence_score,
                    'market_enhanced': interpretation.metadata.get('context_enhanced', False),
                    'metadata': interpretation.metadata
                }
                for interpretation in interpretation_set.interpretations
            ],
            'summary': self._generate_enhanced_summary(interpretation_set, market_context),
            'statistics': self._generate_interpretation_statistics(interpretation_set),
            'actionable_insights': self._generate_actionable_insights(interpretation_set, market_context),
            'metadata': interpretation_set.metadata
        }
    
    def _format_as_actionable_insights(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> Dict[str, Any]:
        """Generate actionable trading insights from interpretations with enhanced synthesis."""
        try:
            # Generate enhanced synthesis first
            enhanced_synthesis = self._generate_enhanced_synthesis(interpretation_set)
            
            insights = {
                'timestamp': interpretation_set.timestamp.isoformat(),
                'enhanced_synthesis': enhanced_synthesis,
                'market_context': market_context.__dict__ if market_context else None,
                'overall_bias': self._determine_overall_bias(interpretation_set),
                'confidence_level': self._calculate_overall_confidence(interpretation_set),
                'risk_assessment': self._assess_risk_level(interpretation_set, market_context),
                'actionable_recommendations': self._generate_actionable_recommendations(interpretation_set, market_context),
                'position_sizing_guidance': self._generate_position_sizing_guidance(interpretation_set, market_context),
                'time_horizon_analysis': self._analyze_time_horizons(interpretation_set, market_context),
                'key_levels': self._extract_key_levels(interpretation_set),
                'risk_management': self._generate_risk_management_advice(interpretation_set, market_context)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate actionable insights: {e}")
            return {'error': str(e)}
    
    def _determine_overall_bias(self, interpretation_set: MarketInterpretationSet) -> str:
        """Determine overall market bias from interpretations."""
        bullish_score = 0
        bearish_score = 0
        total_weight = 0
        
        for interpretation in interpretation_set.interpretations:
            weight = interpretation.confidence_score
            text_lower = interpretation.interpretation_text.lower()
            
            if any(word in text_lower for word in ['bullish', 'buy', 'long', 'positive', 'strength']):
                bullish_score += weight
            elif any(word in text_lower for word in ['bearish', 'sell', 'short', 'negative', 'weakness']):
                bearish_score += weight
            
            total_weight += weight
        
        if total_weight == 0:
            return 'neutral'
        
        bullish_ratio = bullish_score / total_weight
        bearish_ratio = bearish_score / total_weight
        
        if bullish_ratio > 0.6:
            return 'bullish'
        elif bearish_ratio > 0.6:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_overall_confidence(self, interpretation_set: MarketInterpretationSet) -> float:
        """Calculate overall confidence from all interpretations."""
        if not interpretation_set.interpretations:
            return 0.0
        
        # Weight confidence by severity (critical interpretations have more impact)
        weighted_confidence = 0
        total_weight = 0
        
        for interpretation in interpretation_set.interpretations:
            severity_weight = {
                InterpretationSeverity.CRITICAL: 3.0,
                InterpretationSeverity.WARNING: 2.0,
                InterpretationSeverity.INFO: 1.0
            }.get(interpretation.severity, 1.0)
            
            weighted_confidence += interpretation.confidence_score * severity_weight
            total_weight += severity_weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _assess_risk_level(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> str:
        """Assess overall risk level based on interpretations and market context."""
        risk_score = 0
        
        # Factor 1: Severity of interpretations
        critical_count = sum(1 for i in interpretation_set.interpretations if i.severity == InterpretationSeverity.CRITICAL)
        warning_count = sum(1 for i in interpretation_set.interpretations if i.severity == InterpretationSeverity.WARNING)
        
        risk_score += critical_count * 3 + warning_count * 1
        
        # Factor 2: Market context
        if market_context:
            if market_context.is_high_volatility:
                risk_score += 2
            if market_context.regime in ['BEARISH']:
                risk_score += 1
        
        # Factor 3: Divergence in interpretations
        divergence_interpretations = [i for i in interpretation_set.interpretations if 'divergence' in i.component_name.lower()]
        risk_score += len(divergence_interpretations) * 2
        
        if risk_score >= 8:
            return 'high'
        elif risk_score >= 4:
            return 'medium'
        else:
            return 'low'
    
    def _generate_actionable_recommendations(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> List[str]:
        """Generate specific actionable trading recommendations."""
        recommendations = []
        
        overall_bias = self._determine_overall_bias(interpretation_set)
        confidence = self._calculate_overall_confidence(interpretation_set)
        risk_level = self._assess_risk_level(interpretation_set, market_context)
        
        # Base recommendations on bias and confidence
        if overall_bias == 'bullish' and confidence > 0.7:
            if risk_level == 'low':
                recommendations.append("Consider long positions with standard position sizing")
            elif risk_level == 'medium':
                recommendations.append("Consider long positions with reduced position sizing due to elevated risk")
            else:
                recommendations.append("High risk environment - consider waiting for better entry or use very small positions")
        
        elif overall_bias == 'bearish' and confidence > 0.7:
            if risk_level == 'low':
                recommendations.append("Consider short positions or defensive strategies")
            elif risk_level == 'medium':
                recommendations.append("Consider short positions with tight risk management")
            else:
                recommendations.append("High risk bearish environment - consider protective strategies")
        
        elif overall_bias == 'neutral' or confidence < 0.5:
            recommendations.append("Mixed signals suggest waiting for clearer directional bias")
            recommendations.append("Consider range-trading strategies if in consolidation")
        
        # Add market context specific recommendations
        if market_context:
            if market_context.is_high_volatility:
                recommendations.append("High volatility: Use wider stops and smaller position sizes")
            if market_context.institutional_bias != 'neutral':
                recommendations.append(f"Smart money shows {market_context.institutional_bias} bias - consider alignment")
        
        return recommendations
    
    def _generate_position_sizing_guidance(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> Dict[str, Any]:
        """Generate position sizing guidance based on confidence and risk."""
        confidence = self._calculate_overall_confidence(interpretation_set)
        risk_level = self._assess_risk_level(interpretation_set, market_context)
        
        # Base position size on confidence
        if confidence > 0.8:
            base_size = "Standard (1.0x)"
        elif confidence > 0.6:
            base_size = "Reduced (0.7x)"
        elif confidence > 0.4:
            base_size = "Small (0.5x)"
        else:
            base_size = "Minimal (0.2x)"
        
        # Adjust for risk
        risk_multiplier = {
            'low': 1.0,
            'medium': 0.7,
            'high': 0.4
        }.get(risk_level, 0.5)
        
        # Adjust for volatility
        volatility_adjustment = 1.0
        if market_context:
            if market_context.is_high_volatility:
                volatility_adjustment = 0.6
            elif market_context.is_low_volatility:
                volatility_adjustment = 1.3
        
        return {
            'base_size': base_size,
            'risk_adjustment': f"{risk_multiplier:.1f}x",
            'volatility_adjustment': f"{volatility_adjustment:.1f}x",
            'final_recommendation': f"Use {risk_multiplier * volatility_adjustment:.1f}x of normal position size",
            'rationale': f"Based on {confidence:.1%} confidence, {risk_level} risk, and {'high' if market_context and market_context.is_high_volatility else 'normal'} volatility"
        }
    
    def _analyze_time_horizons(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> Dict[str, str]:
        """Analyze appropriate time horizons for different strategies."""
        horizons = {}
        
        # Determine based on component types and market conditions
        has_technical = any(i.component_type == ComponentType.TECHNICAL_INDICATOR for i in interpretation_set.interpretations)
        has_sentiment = any(i.component_type == ComponentType.SENTIMENT_ANALYSIS for i in interpretation_set.interpretations)
        has_volume = any(i.component_type == ComponentType.VOLUME_ANALYSIS for i in interpretation_set.interpretations)
        
        if has_technical and market_context and market_context.is_high_volatility:
            horizons['scalping'] = "Suitable - high volatility provides opportunities"
        elif has_technical:
            horizons['scalping'] = "Moderate - watch for clear signals"
        
        if has_volume and has_sentiment:
            horizons['swing_trading'] = "Suitable - multiple confirmation factors"
        elif has_sentiment:
            horizons['swing_trading'] = "Moderate - sentiment-driven moves can be sustained"
        
        if market_context and market_context.is_trending:
            horizons['trend_following'] = "Suitable - trending market conditions"
        else:
            horizons['trend_following'] = "Limited - ranging market conditions"
        
        return horizons
    
    def _extract_key_levels(self, interpretation_set: MarketInterpretationSet) -> List[str]:
        """Extract key price levels mentioned in interpretations."""
        levels = []
        
        for interpretation in interpretation_set.interpretations:
            text = interpretation.interpretation_text.lower()
            
            # Look for support/resistance mentions
            if 'support' in text:
                levels.append(f"Support level mentioned in {interpretation.component_name}")
            if 'resistance' in text:
                levels.append(f"Resistance level mentioned in {interpretation.component_name}")
            if 'breakout' in text:
                levels.append(f"Breakout level identified in {interpretation.component_name}")
        
        return levels
    
    def _generate_risk_management_advice(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> List[str]:
        """Generate risk management advice based on current conditions."""
        advice = []
        
        risk_level = self._assess_risk_level(interpretation_set, market_context)
        
        if risk_level == 'high':
            advice.append("Use tight stop losses due to high risk environment")
            advice.append("Consider reducing overall portfolio exposure")
            advice.append("Monitor positions more frequently")
        elif risk_level == 'medium':
            advice.append("Use standard stop loss levels with close monitoring")
            advice.append("Consider partial profit taking on winning positions")
        else:
            advice.append("Standard risk management protocols apply")
        
        if market_context and market_context.is_high_volatility:
            advice.append("Widen stop losses to account for increased volatility")
            advice.append("Consider using volatility-based position sizing")
        
        # Check for divergence warnings
        divergence_count = sum(1 for i in interpretation_set.interpretations if 'divergence' in i.interpretation_text.lower())
        if divergence_count > 0:
            advice.append("Mixed signals detected - use extra caution with new positions")
        
        return advice
    
    def _generate_enhanced_summary(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> str:
        """Generate enhanced summary with market context."""
        total_interpretations = len(interpretation_set.interpretations)
        critical_count = sum(1 for i in interpretation_set.interpretations 
                           if i.severity == InterpretationSeverity.CRITICAL)
        warning_count = sum(1 for i in interpretation_set.interpretations 
                          if i.severity == InterpretationSeverity.WARNING)
        
        avg_confidence = sum(i.confidence_score for i in interpretation_set.interpretations) / total_interpretations if total_interpretations > 0 else 0
        
        overall_bias = self._determine_overall_bias(interpretation_set)
        risk_level = self._assess_risk_level(interpretation_set, market_context)
        
        summary_parts = [
            f"Analysis Summary: {total_interpretations} interpretations processed",
            f"{critical_count} critical alerts, {warning_count} warnings",
            f"Average confidence: {avg_confidence:.1%}",
            f"Overall bias: {overall_bias.upper()}",
            f"Risk level: {risk_level.upper()}"
        ]
        
        if market_context:
            summary_parts.append(f"Market regime: {market_context.regime}")
            summary_parts.append(f"Volatility: {'HIGH' if market_context.is_high_volatility else 'LOW' if market_context.is_low_volatility else 'NORMAL'}")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_interpretation_statistics(self, interpretation_set: MarketInterpretationSet) -> Dict[str, Any]:
        """Generate statistical summary of interpretations."""
        if not interpretation_set.interpretations:
            return {}
        
        # Component type distribution
        component_types = {}
        for interpretation in interpretation_set.interpretations:
            comp_type = interpretation.component_type.value
            component_types[comp_type] = component_types.get(comp_type, 0) + 1
        
        # Severity distribution
        severity_dist = {
            'critical': sum(1 for i in interpretation_set.interpretations if i.severity == InterpretationSeverity.CRITICAL),
            'warning': sum(1 for i in interpretation_set.interpretations if i.severity == InterpretationSeverity.WARNING),
            'info': sum(1 for i in interpretation_set.interpretations if i.severity == InterpretationSeverity.INFO)
        }
        
        # Confidence statistics
        confidences = [i.confidence_score for i in interpretation_set.interpretations]
        
        return {
            'total_interpretations': len(interpretation_set.interpretations),
            'component_type_distribution': component_types,
            'severity_distribution': severity_dist,
            'confidence_statistics': {
                'mean': np.mean(confidences),
                'median': np.median(confidences),
                'std': np.std(confidences),
                'min': np.min(confidences),
                'max': np.max(confidences)
            },
            'enhanced_interpretations': sum(1 for i in interpretation_set.interpretations if i.metadata.get('context_enhanced', False)),
            'confluence_detected': any('confluence' in i.component_name for i in interpretation_set.interpretations),
            'divergence_detected': any('divergence' in i.component_name for i in interpretation_set.interpretations)
        }
    
    def _generate_actionable_insights(
        self, 
        interpretation_set: MarketInterpretationSet,
        market_context: Optional[MarketContext] = None
    ) -> List[ActionableInsight]:
        """Generate actionable insights from interpretations."""
        insights = []
        
        try:
            overall_bias = self._determine_overall_bias(interpretation_set)
            confidence = self._calculate_overall_confidence(interpretation_set)
            risk_level = self._assess_risk_level(interpretation_set, market_context)
            
            # Generate primary insight
            if confidence > 0.7:
                if overall_bias == 'bullish':
                    insights.append(ActionableInsight(
                        insight_type="directional_bias",
                        description=f"Strong bullish bias detected with {confidence:.1%} confidence",
                        action_items=[
                            "Consider long positions",
                            f"Use {risk_level} risk management protocols",
                            "Monitor for continuation signals"
                        ],
                        confidence_score=confidence,
                        time_horizon="short_to_medium_term",
                        risk_level=risk_level
                    ))
                elif overall_bias == 'bearish':
                    insights.append(ActionableInsight(
                        insight_type="directional_bias",
                        description=f"Strong bearish bias detected with {confidence:.1%} confidence",
                        action_items=[
                            "Consider short positions or defensive strategies",
                            f"Use {risk_level} risk management protocols",
                            "Monitor for reversal signals"
                        ],
                        confidence_score=confidence,
                        time_horizon="short_to_medium_term",
                        risk_level=risk_level
                    ))
            
            # Generate market context insights
            if market_context:
                if market_context.is_high_volatility:
                    insights.append(ActionableInsight(
                        insight_type="volatility_regime",
                        description=f"High volatility environment ({market_context.volatility:.1f})",
                        action_items=[
                            "Use wider stop losses",
                            "Reduce position sizes",
                            "Increase monitoring frequency"
                        ],
                        confidence_score=0.9,
                        time_horizon="immediate",
                        risk_level="elevated"
                    ))
                
                if market_context.institutional_bias != 'neutral':
                    insights.append(ActionableInsight(
                        insight_type="institutional_flow",
                        description=f"Smart money shows {market_context.institutional_bias} bias ({market_context.smart_money_index:.1f})",
                        action_items=[
                            f"Consider alignment with institutional {market_context.institutional_bias} bias",
                            "Monitor for institutional flow changes",
                            "Use institutional sentiment as confirmation"
                        ],
                        confidence_score=0.8,
                        time_horizon="medium_term",
                        risk_level="standard"
                    ))
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Failed to generate actionable insights: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get enhanced processing statistics."""
        return {
            **self._processing_stats,
            'cache_size': len(self._interpretation_cache),
            'enhancement_rate': self._processing_stats['context_enhancements'] / max(1, self._processing_stats['total_processed']),
            'confluence_detection_rate': self._processing_stats['confluence_detections'] / max(1, self._processing_stats['total_processed'])
        }
    
    def clear_cache(self):
        """Clear the interpretation cache."""
        self._interpretation_cache.clear()
        self.logger.info("Interpretation cache cleared")
    
    def get_cached_interpretation(self, cache_key: str) -> Optional[MarketInterpretationSet]:
        """Retrieve cached interpretation set."""
        return self._interpretation_cache.get(cache_key)
    
    def _generate_enhanced_synthesis(self, interpretation_set: MarketInterpretationSet) -> str:
        """
        Generate enhanced synthesis that resolves conflicts and provides actionable insights.
        
        Args:
            interpretation_set: The processed interpretation set
            
        Returns:
            Enhanced synthesis with conflict resolution and actionable recommendations
        """
        try:
            interpretations = interpretation_set.interpretations
            if not interpretations:
                return "No market data available for synthesis."
            
            # Analyze component impacts and conflicts
            component_analysis = self._analyze_component_relationships(interpretations)
            market_state = self._classify_market_state(interpretations, component_analysis)
            
            # Generate synthesis based on market state
            synthesis_parts = []
            
            # Market state headline
            synthesis_parts.append(f"**MARKET STATE: {market_state['classification'].upper()}**")
            
            # Primary narrative (highest impact components)
            primary_narrative = self._generate_primary_narrative(interpretations, component_analysis)
            synthesis_parts.append(primary_narrative)
            
            # Conflict resolution (if any)
            if component_analysis['conflicts']:
                conflict_analysis = self._generate_conflict_analysis(component_analysis['conflicts'])
                synthesis_parts.append(conflict_analysis)
            
            # Actionable recommendations
            recommendations = self._generate_actionable_recommendations(market_state, component_analysis)
            synthesis_parts.append(recommendations)
            
            # Risk assessment
            risk_assessment = self._generate_risk_assessment(interpretations, component_analysis)
            synthesis_parts.append(risk_assessment)
            
            return "\n\n".join(synthesis_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced synthesis: {str(e)}")
            return "Enhanced synthesis temporarily unavailable."
    
    def _analyze_component_relationships(self, interpretations: List[ComponentInterpretation]) -> Dict[str, Any]:
        """Analyze relationships and conflicts between components."""
        try:
            # Calculate component impacts and directions
            component_data = {}
            total_impact = 0
            
            for interp in interpretations:
                # Determine directional bias
                confidence = interp.confidence_score
                text = interp.interpretation_text.lower()
                
                # Simple sentiment analysis of interpretation text
                bullish_words = ['bullish', 'strong', 'buying', 'support', 'accumulation', 'positive', 'upward']
                bearish_words = ['bearish', 'weak', 'selling', 'resistance', 'distribution', 'negative', 'downward']
                
                bullish_count = sum(1 for word in bullish_words if word in text)
                bearish_count = sum(1 for word in bearish_words if word in text)
                
                # Calculate directional bias (-1 to 1)
                if bullish_count + bearish_count > 0:
                    bias = (bullish_count - bearish_count) / (bullish_count + bearish_count)
                else:
                    bias = 0  # Neutral
                
                component_data[interp.component_name] = {
                    'confidence': confidence,
                    'bias': bias,
                    'impact': confidence * 0.1,  # Simple impact calculation
                    'text': interp.interpretation_text
                }
                total_impact += confidence * 0.1
            
            # Detect conflicts (components with opposing biases)
            conflicts = []
            components = list(component_data.keys())
            
            for i, comp1 in enumerate(components):
                for comp2 in components[i+1:]:
                    bias1 = component_data[comp1]['bias']
                    bias2 = component_data[comp2]['bias']
                    impact1 = component_data[comp1]['impact']
                    impact2 = component_data[comp2]['impact']
                    
                    # Conflict if biases are opposite and both have significant impact
                    if (bias1 * bias2 < -0.3 and  # Opposite directions
                        min(impact1, impact2) > total_impact * 0.1):  # Both have meaningful impact
                        conflicts.append({
                            'component1': comp1,
                            'component2': comp2,
                            'bias1': bias1,
                            'bias2': bias2,
                            'severity': abs(bias1 - bias2) * min(impact1, impact2)
                        })
            
            # Sort components by impact
            sorted_components = sorted(component_data.items(), 
                                     key=lambda x: x[1]['impact'], 
                                     reverse=True)
            
            return {
                'component_data': component_data,
                'sorted_components': sorted_components,
                'conflicts': conflicts,
                'total_impact': total_impact,
                'overall_bias': sum(data['bias'] * data['impact'] for data in component_data.values()) / total_impact if total_impact > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing component relationships: {str(e)}")
            return {'component_data': {}, 'sorted_components': [], 'conflicts': [], 'total_impact': 0, 'overall_bias': 0}
    
    def _classify_market_state(self, interpretations: List[ComponentInterpretation], component_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Classify the current market state based on component analysis."""
        try:
            overall_bias = component_analysis['overall_bias']
            conflicts = component_analysis['conflicts']
            total_impact = component_analysis['total_impact']
            
            # Determine market state
            if len(conflicts) > 2:
                classification = "conflicted"
                description = "Mixed signals across components suggest market uncertainty"
                strategy = "Wait for clearer direction or use neutral strategies"
            elif abs(overall_bias) > 0.6:
                if overall_bias > 0:
                    classification = "trending_bullish"
                    description = "Strong bullish alignment across major components"
                    strategy = "Consider trend-following long positions"
                else:
                    classification = "trending_bearish"
                    description = "Strong bearish alignment across major components"
                    strategy = "Consider trend-following short positions"
            elif abs(overall_bias) > 0.3:
                if overall_bias > 0:
                    classification = "leaning_bullish"
                    description = "Moderate bullish bias with some mixed signals"
                    strategy = "Consider selective long positions with tight stops"
                else:
                    classification = "leaning_bearish"
                    description = "Moderate bearish bias with some mixed signals"
                    strategy = "Consider selective short positions with tight stops"
            else:
                # Check if we have strong range analysis signals
                range_components = [i for i in interpretations if 'range' in i.component_name.lower()]
                if range_components:
                    classification = "ranging_confirmed"
                    description = "Range analysis confirms sideways consolidation with defined boundaries"
                    strategy = "Focus on range-trading strategies with clear support/resistance levels"
                else:
                    classification = "ranging"
                    description = "Balanced forces suggest sideways consolidation"
                    strategy = "Consider range-trading or breakout strategies"
            
            return {
                'classification': classification,
                'description': description,
                'strategy': strategy,
                'confidence': min(total_impact / len(interpretations), 1.0) if interpretations else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error classifying market state: {str(e)}")
            return {
                'classification': 'unknown',
                'description': 'Unable to classify market state',
                'strategy': 'Exercise caution',
                'confidence': 0
            }
    
    def _generate_primary_narrative(self, interpretations: List[ComponentInterpretation], component_analysis: Dict[str, Any]) -> str:
        """Generate primary narrative focusing on highest impact components."""
        try:
            sorted_components = component_analysis['sorted_components']
            if not sorted_components:
                return "No significant market signals detected."
            
            # Focus on top 2-3 components by impact
            primary_components = sorted_components[:3]
            
            narrative_parts = []
            narrative_parts.append("**PRIMARY MARKET DRIVERS:**")
            
            for i, (comp_name, comp_data) in enumerate(primary_components):
                impact_pct = (comp_data['impact'] / component_analysis['total_impact']) * 100 if component_analysis['total_impact'] > 0 else 0
                bias_desc = "bullish" if comp_data['bias'] > 0.2 else "bearish" if comp_data['bias'] < -0.2 else "neutral"
                
                # Clean up the interpretation text to be more concise
                clean_text = self._clean_interpretation_for_synthesis(comp_data['text'])
                
                narrative_parts.append(
                    f"• **{comp_name.replace('_', ' ').title()}** ({impact_pct:.1f}% impact, {bias_desc}): {clean_text}"
                )
            
            return "\n".join(narrative_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating primary narrative: {str(e)}")
            return "Primary narrative temporarily unavailable."
    
    def _generate_conflict_analysis(self, conflicts: List[Dict[str, Any]]) -> str:
        """Generate analysis of component conflicts."""
        try:
            if not conflicts:
                return ""
            
            analysis_parts = []
            analysis_parts.append("**⚠️ SIGNAL CONFLICTS DETECTED:**")
            
            # Sort conflicts by severity
            sorted_conflicts = sorted(conflicts, key=lambda x: x['severity'], reverse=True)
            
            for conflict in sorted_conflicts[:2]:  # Show top 2 conflicts
                comp1 = conflict['component1'].replace('_', ' ').title()
                comp2 = conflict['component2'].replace('_', ' ').title()
                
                if conflict['bias1'] > 0:
                    analysis_parts.append(f"• {comp1} signals bullish while {comp2} signals bearish - suggests market indecision or transition phase")
                else:
                    analysis_parts.append(f"• {comp1} signals bearish while {comp2} signals bullish - suggests market indecision or transition phase")
            
            analysis_parts.append("**Recommendation:** Exercise increased caution and wait for signal alignment before taking large positions.")
            
            return "\n".join(analysis_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating conflict analysis: {str(e)}")
            return ""
    
    def _generate_risk_assessment(self, interpretations: List[ComponentInterpretation], component_analysis: Dict[str, Any]) -> str:
        """Generate comprehensive risk assessment."""
        try:
            risk_parts = []
            risk_parts.append("**⚠️ RISK ASSESSMENT:**")
            
            # Calculate risk factors
            conflicts = len(component_analysis['conflicts'])
            confidence_scores = [interp.confidence_score for interp in interpretations]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            confidence_variance = sum((x - avg_confidence) ** 2 for x in confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Overall risk level
            if conflicts > 2 or avg_confidence < 0.4 or confidence_variance > 0.3:
                risk_level = "HIGH"
                risk_color = "🔴"
            elif conflicts > 0 or avg_confidence < 0.6 or confidence_variance > 0.2:
                risk_level = "MODERATE"
                risk_color = "🟡"
            else:
                risk_level = "LOW"
                risk_color = "🟢"
            
            risk_parts.append(f"• **Overall Risk Level:** {risk_color} {risk_level}")
            
            # Specific risk factors
            if conflicts > 0:
                risk_parts.append(f"• **Signal Conflicts:** {conflicts} detected - increases uncertainty")
            
            if confidence_variance > 0.2:
                risk_parts.append("• **Confidence Variance:** High disagreement between components")
            
            if avg_confidence < 0.5:
                risk_parts.append("• **Low Confidence:** Average signal strength below optimal threshold")
            
            # Risk mitigation
            risk_parts.append("• **Mitigation:** Monitor for signal alignment before increasing exposure")
            
            return "\n".join(risk_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating risk assessment: {str(e)}")
            return "**⚠️ RISK ASSESSMENT:** Standard risk protocols recommended."
    
    def _clean_interpretation_for_synthesis(self, text: str) -> str:
        """Clean interpretation text for synthesis narrative."""
        try:
            # Remove redundant phrases and clean up for synthesis
            import re
            
            # Remove market context prefixes that are redundant in synthesis
            text = re.sub(r'^(In current|Under|Given|With)\s+[^:]+:\s*', '', text)
            
            # Remove redundant "indicating" phrases
            text = re.sub(r',\s*indicating[^,\.]+', '', text)
            
            # Remove analysis probability statements for synthesis
            text = re.sub(r'\.\s*Analysis suggests[^\.]+\.', '.', text)
            
            # Limit length for synthesis
            sentences = text.split('.')
            if len(sentences) > 2:
                text = '. '.join(sentences[:2]) + '.'
            
            # Clean up extra spaces
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error cleaning interpretation text: {str(e)}")
            return text

    def _generate_actionable_recommendations(self, market_state: Dict[str, Any], component_analysis: Dict[str, Any]) -> str:
        """Generate specific, actionable trading recommendations."""
        try:
            recommendations = []
            recommendations.append("**🎯 ACTIONABLE RECOMMENDATIONS:**")
            
            # Primary strategy
            recommendations.append(f"• **Primary Strategy:** {market_state['strategy']}")
            
            # Position sizing based on confidence and conflicts
            confidence = market_state['confidence']
            conflicts = len(component_analysis['conflicts'])
            
            if confidence > 0.8 and conflicts == 0:
                position_size = "Normal to aggressive position sizing appropriate"
            elif confidence > 0.6 and conflicts <= 1:
                position_size = "Moderate position sizing recommended"
            elif confidence > 0.4 and conflicts <= 2:
                position_size = "Reduced position sizing advised"
            else:
                position_size = "Minimal position sizing or paper trading only"
            
            recommendations.append(f"• **Position Sizing:** {position_size}")
            
            # Time horizon
            if market_state['classification'] in ['trending_bullish', 'trending_bearish']:
                time_horizon = "Medium-term holds (days to weeks) may be appropriate"
            elif market_state['classification'] in ['leaning_bullish', 'leaning_bearish']:
                time_horizon = "Short-term trades (hours to days) preferred"
            else:
                time_horizon = "Intraday or scalping strategies most suitable"
            
            recommendations.append(f"• **Time Horizon:** {time_horizon}")
            
            # Risk management
            if conflicts > 2:
                risk_mgmt = "Tight stops essential due to conflicting signals"
            elif confidence < 0.5:
                risk_mgmt = "Conservative stops recommended due to low confidence"
            else:
                risk_mgmt = "Standard risk management protocols apply"
            
            recommendations.append(f"• **Risk Management:** {risk_mgmt}")
            
            return "\n".join(recommendations)
            
        except Exception as e:
            self.logger.error(f"Error generating actionable recommendations: {str(e)}")
            return "**🎯 ACTIONABLE RECOMMENDATIONS:** Exercise standard risk management."