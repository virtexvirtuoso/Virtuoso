#!/usr/bin/env python3
"""
Test script to demonstrate the new component breakdown formatting
"""

import logging
import sys
from src.core.formatting import AnalysisFormatter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def create_sample_analysis_result():
    """Create a sample analysis result for testing"""
    return {
        'score': 52.63,
        'confluence_score': 52.63,
        'reliability': 1.0,
        'components': {
            'technical': 31.61,
            'volume': 62.68,
            'orderbook': 74.60,
            'orderflow': 71.32,
            'sentiment': 51.32,
            'price_structure': 52.52
        },
        'results': {
            'technical': {
                'score': 31.61,
                'components': {
                    'rsi': 49.45,
                    'macd': 24.86,
                    'ao': 0.0,
                    'williams_r': 41.76,
                    'atr': 42.0,
                    'cci': 36.15
                }
            },
            'sentiment': {
                'interpretation': {
                    'signal': 'neutral',
                    'bias': 'neutral',
                    'risk_level': 'unfavorable',
                    'summary': 'Market sentiment is neutral with unfavorable risk conditions'
                }
            }
        }
    }

def main():
    """Main function to test the formatter"""
    # Create a sample analysis result
    analysis_result = create_sample_analysis_result()
    
    # Create an instance of the formatter
    formatter = AnalysisFormatter()
    
    # Format the component breakdown
    components = analysis_result.get('components', {})
    component_breakdown = formatter.format_component_breakdown(components, analysis_result.get('results', {}))
    
    # Log the formatted component breakdown
    logger.info(f"\nComponent Breakdown:\n{component_breakdown}")
    
    # Format the full analysis result
    formatted_result = formatter.format_analysis_result(analysis_result, "BTCUSDT")
    
    # Log the formatted analysis result
    logger.info(f"\n{formatted_result}")

if __name__ == "__main__":
    main() 