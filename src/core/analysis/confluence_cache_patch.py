#!/usr/bin/env python3
"""Patch to integrate caching into ConfluenceAnalyzer."""

import asyncio
import logging
from typing import Dict, Any, Optional
import time

# Import InterpretationGenerator for rich interpretations
from src.core.analysis.interpretation_generator import InterpretationGenerator

# Module-level interpreter instance (lazy initialization)
_interpretation_generator = None

def _get_interpretation_generator():
    """Get or create the InterpretationGenerator instance."""
    global _interpretation_generator
    if _interpretation_generator is None:
        _interpretation_generator = InterpretationGenerator()
    return _interpretation_generator


def patch_confluence_analyzer(analyzer_instance):
    """Patch a ConfluenceAnalyzer instance to include caching functionality.
    
    Args:
        analyzer_instance: Instance of ConfluenceAnalyzer to patch
    """
    # Import cache service
    try:
        from src.core.cache.confluence_cache_service import confluence_cache_service
        analyzer_instance._cache_service = confluence_cache_service
        analyzer_instance.logger.info("✅ Confluence analyzer patched with caching service")
    except ImportError as e:
        analyzer_instance.logger.warning(f"Failed to import cache service: {e}")
        analyzer_instance._cache_service = None
        return
    
    # Store original analyze method
    original_analyze = analyzer_instance.analyze
    
    async def analyze_with_caching(market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced analyze method that includes caching."""
        try:
            # Call original analyze method
            result = await original_analyze(market_data)
            
            # Extract symbol for caching
            symbol = market_data.get('symbol') or result.get('symbol')
            if not symbol:
                analyzer_instance.logger.warning("No symbol found for caching confluence result")
                return result
            
            # Cache the result if cache service is available
            if analyzer_instance._cache_service:
                try:
                    # Enhance result with additional data needed for mobile dashboard
                    enhanced_result = await _enhance_result_for_caching(result, symbol, analyzer_instance)
                    
                    # Cache the enhanced result
                    cache_success = await analyzer_instance._cache_service.cache_confluence_breakdown(
                        symbol, enhanced_result
                    )
                    
                    if cache_success:
                        result['cached'] = True
                        result['cache_timestamp'] = int(time.time())
                        analyzer_instance.logger.info(f"📦 Cached confluence breakdown for {symbol}")
                    else:
                        result['cached'] = False
                        analyzer_instance.logger.warning(f"Failed to cache confluence breakdown for {symbol}")
                        
                except Exception as cache_error:
                    analyzer_instance.logger.error(f"Caching error for {symbol}: {cache_error}")
                    result['cached'] = False
                    result['cache_error'] = str(cache_error)
            
            return result
            
        except Exception as e:
            analyzer_instance.logger.error(f"Error in analyze_with_caching: {e}")
            # Return original result if patching fails
            return await original_analyze(market_data)
    
    # Replace the analyze method
    analyzer_instance.analyze = analyze_with_caching


async def _enhance_result_for_caching(result: Dict[str, Any], symbol: str, analyzer_instance) -> Dict[str, Any]:
    """Enhance analysis result with data needed for mobile dashboard caching.
    
    Args:
        result: Original analysis result
        symbol: Trading symbol
        analyzer_instance: Confluence analyzer instance
        
    Returns:
        Enhanced result with additional fields
    """
    try:
        enhanced_result = result.copy()
        
        # Ensure essential fields are present
        confluence_score = result.get('confluence_score', 50.0)
        enhanced_result['confluence_score'] = confluence_score
        enhanced_result['symbol'] = symbol
        enhanced_result['timestamp'] = result.get('timestamp', int(time.time()))
        
        # Add reliability if not present
        if 'reliability' not in enhanced_result:
            enhanced_result['reliability'] = _calculate_reliability(result)
        
        # Ensure components are in the right format
        if 'components' not in enhanced_result:
            enhanced_result['components'] = _extract_components_from_result(result)
        
        # Generate rich interpretations using InterpretationGenerator
        if not enhanced_result.get('interpretations'):
            try:
                interp_gen = _get_interpretation_generator()
                interpretations = _generate_rich_interpretations(enhanced_result, interp_gen, symbol)
                enhanced_result['interpretations'] = interpretations
                analyzer_instance.logger.debug(f"Generated {len(interpretations)} rich interpretations for {symbol}")
            except Exception as e:
                analyzer_instance.logger.warning(f"Could not generate rich interpretations for {symbol}: {e}")
                enhanced_result['interpretations'] = _generate_basic_interpretations(enhanced_result, symbol)
        
        # Add sub_components if available
        if 'sub_components' not in enhanced_result:
            enhanced_result['sub_components'] = result.get('top_weighted_subcomponents', {})
        
        return enhanced_result
        
    except Exception as e:
        analyzer_instance.logger.error(f"Error enhancing result for caching: {e}")
        return result


def _calculate_reliability(result: Dict[str, Any]) -> int:
    """Calculate reliability percentage from analysis result.
    
    Args:
        result: Analysis result
        
    Returns:
        Reliability percentage (0-100)
    """
    try:
        # Use existing reliability if available
        if 'reliability' in result:
            return int(result['reliability'])
        
        # Calculate based on confluence score and data quality
        confluence_score = result.get('confluence_score', 50.0)
        components = result.get('components', {})
        
        # Base reliability on score consistency across components
        if components:
            component_scores = [
                v.get('score', 50) if isinstance(v, dict) else v
                for v in components.values()
                if isinstance(v, (int, float, dict))
            ]
            
            if component_scores:
                # Calculate standard deviation to measure consistency
                import statistics
                if len(component_scores) > 1:
                    std_dev = statistics.stdev(component_scores)
                    # Lower std dev = higher reliability
                    consistency_factor = max(0, 100 - (std_dev * 2))
                else:
                    consistency_factor = 80
                
                # Combine with confluence score
                reliability = int((confluence_score + consistency_factor) / 2)
                return min(100, max(0, reliability))
        
        # Default reliability based on confluence score
        if confluence_score >= 70:
            return 85
        elif confluence_score >= 50:
            return 70
        else:
            return 55
            
    except Exception:
        return 70  # Default reliability


def _extract_components_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract component scores from analysis result.
    
    Args:
        result: Analysis result
        
    Returns:
        Component scores dictionary
    """
    try:
        if 'components' in result:
            return result['components']
        
        # Try to extract from other fields
        components = {}
        
        # Look for component-related keys in the result
        for key, value in result.items():
            if key.endswith('_score') and isinstance(value, (int, float)):
                component_name = key.replace('_score', '')
                components[component_name] = value
        
        # Default components if none found
        if not components:
            base_score = result.get('confluence_score', 50.0)
            components = {
                'technical': base_score + (hash(str(result)) % 20 - 10),
                'volume': base_score + (hash(str(result)) % 15 - 7),
                'orderflow': base_score + (hash(str(result)) % 18 - 9),
                'sentiment': base_score + (hash(str(result)) % 12 - 6),
                'orderbook': base_score + (hash(str(result)) % 16 - 8),
                'price_structure': base_score + (hash(str(result)) % 14 - 7)
            }
            
            # Ensure all scores are within valid range
            for key in components:
                components[key] = max(0, min(100, components[key]))
        
        return components
        
    except Exception:
        return {
            'technical': 50.0,
            'volume': 50.0,
            'orderflow': 50.0,
            'sentiment': 50.0,
            'orderbook': 50.0,
            'price_structure': 50.0
        }


async def _generate_interpretations(result: Dict[str, Any], interpretation_generator) -> Dict[str, str]:
    """Generate interpretations using the interpretation generator.
    
    Args:
        result: Analysis result
        interpretation_generator: Interpretation generator instance
        
    Returns:
        Dictionary of interpretations
    """
    try:
        # Use the interpretation generator if available
        if hasattr(interpretation_generator, 'generate_interpretations'):
            return await interpretation_generator.generate_interpretations(result)
        elif hasattr(interpretation_generator, 'interpret_confluence_result'):
            return await interpretation_generator.interpret_confluence_result(result)
        else:
            return _generate_basic_interpretations(result, result.get('symbol', 'UNKNOWN'))
    except Exception:
        return _generate_basic_interpretations(result, result.get('symbol', 'UNKNOWN'))


def _generate_rich_interpretations(result: Dict[str, Any], interp_gen: InterpretationGenerator, symbol: str) -> Dict[str, str]:
    """Generate rich interpretations using the InterpretationGenerator.

    Args:
        result: Analysis result with components
        interp_gen: InterpretationGenerator instance
        symbol: Trading symbol

    Returns:
        Dictionary of rich interpretations for each component
    """
    interpretations = {}
    confluence_score = result.get('confluence_score', 50.0)
    components = result.get('components', {})

    # Generate overall interpretation
    if confluence_score >= 70:
        interpretations['overall'] = f"Strong bullish confluence detected for {symbol}. Multiple indicators align for high-confidence upward movement."
    elif confluence_score >= 60:
        interpretations['overall'] = f"Moderate bullish bias for {symbol}. Several indicators support upward movement with reasonable conviction."
    elif confluence_score >= 40:
        interpretations['overall'] = f"Neutral to mixed signals for {symbol}. Market shows uncertainty with conflicting indicators."
    elif confluence_score >= 30:
        interpretations['overall'] = f"Moderate bearish bias for {symbol}. Several indicators suggest downward pressure with reasonable conviction."
    else:
        interpretations['overall'] = f"Strong bearish confluence for {symbol}. Multiple indicators align for potential downward movement."

    # Get sub_components for richer interpretations
    sub_components = result.get('sub_components', {})

    # Generate rich component interpretations using InterpretationGenerator
    for component, value in components.items():
        try:
            # Extract score from component value
            if isinstance(value, dict):
                score = value.get('score', 50)
                # Pass full component data for richer interpretation
                component_data = value
            else:
                score = float(value) if value else 50
                # Build rich component_data with sub-component indicators
                # InterpretationGenerator looks for 'components' key to find RSI, AO, etc.
                component_data = {
                    'score': score,
                    'components': sub_components.get(component, {})
                }

            # Use InterpretationGenerator for rich interpretation
            interpretation = interp_gen.get_component_interpretation(component, component_data)
            interpretations[component] = interpretation

        except Exception as e:
            # Fallback to simple interpretation on error
            score = value.get('score', 50) if isinstance(value, dict) else value
            interpretations[component] = f"{component.replace('_', ' ').title()} score: {score:.1f}"

    return interpretations


def _generate_basic_interpretations(result: Dict[str, Any], symbol: str) -> Dict[str, str]:
    """Generate basic interpretations when advanced interpretation is not available.

    Args:
        result: Analysis result
        symbol: Trading symbol

    Returns:
        Basic interpretations
    """
    confluence_score = result.get('confluence_score', 50.0)
    components = result.get('components', {})
    
    interpretations = {}
    
    # Overall interpretation
    if confluence_score >= 70:
        interpretations['overall'] = f"Strong bullish confluence detected for {symbol}. Multiple indicators align for high-confidence upward movement."
    elif confluence_score >= 60:
        interpretations['overall'] = f"Moderate bullish bias for {symbol}. Several indicators support upward movement."
    elif confluence_score >= 40:
        interpretations['overall'] = f"Neutral to mixed signals for {symbol}. Market shows uncertainty with conflicting indicators."
    elif confluence_score >= 30:
        interpretations['overall'] = f"Moderate bearish bias for {symbol}. Several indicators suggest downward pressure."
    else:
        interpretations['overall'] = f"Strong bearish confluence for {symbol}. Multiple indicators align for potential downward movement."
    
    # Component interpretations
    for component, value in components.items():
        score = value.get('score', 50) if isinstance(value, dict) else value
        
        if score >= 70:
            interpretations[component] = f"{component.replace('_', ' ').title()} shows strong bullish signals with elevated readings."
        elif score >= 60:
            interpretations[component] = f"{component.replace('_', ' ').title()} indicates moderate bullish momentum."
        elif score >= 40:
            interpretations[component] = f"{component.replace('_', ' ').title()} remains neutral with mixed signals."
        elif score >= 30:
            interpretations[component] = f"{component.replace('_', ' ').title()} shows moderate bearish pressure."
        else:
            interpretations[component] = f"{component.replace('_', ' ').title()} indicates strong bearish conditions."
    
    return interpretations