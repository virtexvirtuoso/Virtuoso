"""
Demo script for showing the improved analysis formatting utilities.

This script:
1. Shows the basic market analysis dashboard
2. Demonstrates trend indicators comparing current and previous values
3. Showcases detailed component breakdowns in table format
"""

import sys
import logging
import random
from datetime import datetime

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Import the formatting utility
try:
    from core.formatting import AnalysisFormatter
except ImportError:
    print("Error: Could not import formatting utilities. Make sure the path is correct.")
    sys.exit(1)

def generate_sample_data(is_previous=False):
    """Generate sample analysis data for demonstration"""
    # Generate random scores for components with some consistency
    # For previous data, we'll generate slightly different values
    base_variation = 0.2 if is_previous else 0.0
    
    # Component scores
    components = {
        'technical': random.uniform(65, 85) - base_variation * 10,
        'volume': random.uniform(55, 75) - base_variation * 7,
        'orderbook': random.uniform(25, 45) + base_variation * 5,  # Improving
        'orderflow': random.uniform(45, 65) - base_variation * 3,
        'sentiment': random.uniform(45, 55) + base_variation * 8,  # Improving
        'price_structure': random.uniform(40, 60) - base_variation * 4
    }
    
    # Calculate overall score (weighted average)
    weights = {
        'technical': 0.3,
        'volume': 0.15,
        'orderbook': 0.15,
        'orderflow': 0.15,
        'sentiment': 0.15,
        'price_structure': 0.1
    }
    
    overall_score = sum(components[k] * weights[k] for k in components)
    
    # Generate detailed component breakdowns
    detailed_components = {
        'technical': {
            'rsi': random.uniform(50, 90),
            'macd': random.uniform(60, 85),
            'ao': random.uniform(55, 95),
            'williams_r': random.uniform(40, 80),
            'atr': random.uniform(30, 60),
            'cci': random.uniform(60, 90)
        },
        'volume': {
            'volume_delta': random.uniform(40, 80),
            'adl': random.uniform(45, 70),
            'cmf': random.uniform(50, 85),
            'relative_volume': random.uniform(40, 75),
            'obv': random.uniform(45, 70)
        },
        'orderbook': {
            'imbalance': random.uniform(20, 40),
            'liquidity': random.uniform(30, 60),
            'price_impact': random.uniform(40, 70),
            'depth': random.uniform(25, 55),
            'support_resistance': random.uniform(30, 60)
        }
    }
    
    # Create complete analysis result structure
    result = {
        'score': overall_score,
        'reliability': random.uniform(0.8, 1.0),
        'components': components,
        'results': {
            'technical': {'components': detailed_components['technical'], 'score': components['technical']},
            'volume': {'components': detailed_components['volume'], 'score': components['volume']},
            'orderbook': {'components': detailed_components['orderbook'], 'score': components['orderbook']}
        },
        'overall_interpretation': "Moderate bullish bias with technical indicators showing strength, but orderbook suggesting caution. Recent volume patterns indicate growing interest."
    }
    
    return result

def main():
    """Main function to demonstrate the formatting"""
    logger = logging.getLogger("demo_formatting")
    
    # Generate sample data
    logger.info("="*80)
    logger.info("MARKET ANALYSIS FORMATTING DEMO")
    logger.info("="*80)
    
    # Generate current and previous data
    previous_data = generate_sample_data(is_previous=True)
    current_data = generate_sample_data(is_previous=False)
    
    symbol = "BTCUSDT"
    
    # 1. First show basic formatting
    logger.info("\n1. BASIC ANALYSIS DASHBOARD:")
    basic_output = AnalysisFormatter.format_analysis_result(current_data, symbol)
    logger.info(basic_output)
    
    # 2. Show formatting with trend indicators
    logger.info("\n2. DASHBOARD WITH TREND INDICATORS:")
    trend_output = AnalysisFormatter.format_analysis_result(current_data, symbol, previous_data)
    logger.info(trend_output)
    
    # 3. Demonstrate individual feature: gauge
    logger.info("\n3. COMPONENT EXAMPLES:")
    for score in [30, 50, 75]:
        gauge = AnalysisFormatter.create_gauge(score)
        color = AnalysisFormatter.get_color_for_value(score)
        logger.info(f"Score {score}: {color}{score}{AnalysisFormatter.RESET} {gauge}")
    
    # 4. Demonstrate trend indicators
    logger.info("\n4. TREND INDICATOR EXAMPLES:")
    pairs = [
        (50, 40, "Rising"),
        (50, 50, "Unchanged"),
        (50, 60, "Falling")
    ]
    
    for current, previous, label in pairs:
        trend = AnalysisFormatter.get_trend_indicator(current, previous)
        logger.info(f"{label}: {current} vs {previous} → {trend}")
    
    logger.info("\nDemonstration complete! You can customize the formatting further by modifying src/core/formatting.py")

if __name__ == "__main__":
    main() 