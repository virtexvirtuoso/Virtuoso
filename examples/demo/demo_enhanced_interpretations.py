"""
Demo script for enhanced market interpretations.

This script demonstrates how to use the new InterpretationGenerator and EnhancedFormatter
to generate rich, context-aware market interpretations.
"""

import logging
import json
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("demo_enhanced_interpretations")

# Import the necessary modules
from src.core.analysis.interpretation_generator import InterpretationGenerator
from src.core.formatting.formatter import EnhancedFormatter
from src.core.formatting import LogFormatter

def load_sample_data(file_path: str = "sample_analysis_result.json") -> Dict[str, Any]:
    """Load sample analysis data from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Sample data file not found: {file_path}")
        # Return a minimal sample if file not found
        return {
            "symbol": "BTCUSDT",
            "confluence_score": 55.5,
            "components": {
                "technical": 60,
                "volume": 45,
                "orderbook": 58,
                "orderflow": 52,
                "sentiment": 48,
                "price_structure": 62
            },
            "results": {
                "technical": {
                    "score": 60,
                    "components": {"rsi": 65, "macd": 58, "ema": 62},
                    "signals": {"trend": "bullish", "strength": 0.4}
                },
                "volume": {
                    "score": 45,
                    "components": {"volume_change": 40, "vwap": 48},
                    "signals": {"volume_trend": {"signal": "decreasing"}}
                },
                "orderbook": {
                    "score": 58,
                    "components": {"imbalance": 55, "liquidity": 60, "spread": 58}
                },
                "orderflow": {
                    "score": 52,
                    "components": {"cvd": 54, "trade_flow_score": 50}
                },
                "sentiment": {
                    "score": 48,
                    "components": {"funding_rate": 45, "long_short_ratio": 50}
                },
                "price_structure": {
                    "score": 62,
                    "components": {"market_structure": 65, "vwap": 60},
                    "signals": {
                        "trend": {"signal": "uptrend", "value": 65},
                        "support_resistance": {"signal": "strong_level", "bias": "bullish", "value": 70}
                    }
                }
            }
        }

def demo_enhanced_interpretations():
    """Demonstrate the enhanced market interpretations."""
    # Load sample data
    sample_data = load_sample_data()
    
    # Extract key information
    symbol = sample_data.get("symbol", "UNKNOWN")
    confluence_score = sample_data.get("confluence_score", 50)
    components = sample_data.get("components", {})
    results = sample_data.get("results", {})
    
    # Create an interpretation generator
    interpretation_generator = InterpretationGenerator()
    
    # Generate and display component interpretations
    logger.info("\n=== COMPONENT INTERPRETATIONS ===")
    for component_name, component_data in results.items():
        try:
            interpretation = interpretation_generator.get_component_interpretation(
                component_name, component_data
            )
            logger.info(f"{component_name.replace('_', ' ').title()}: {interpretation}")
        except Exception as e:
            logger.error(f"Error generating interpretation for {component_name}: {str(e)}")
    
    # Generate and display cross-component insights
    cross_insights = interpretation_generator.generate_cross_component_insights(results)
    if cross_insights:
        logger.info("\n=== CROSS-COMPONENT INSIGHTS ===")
        for insight in cross_insights:
            logger.info(f"• {insight}")
    
    # Generate and display actionable trading insights
    buy_threshold = 65
    sell_threshold = 35
    actionable_insights = interpretation_generator.generate_actionable_insights(
        results, confluence_score, buy_threshold, sell_threshold
    )
    if actionable_insights:
        logger.info("\n=== ACTIONABLE TRADING INSIGHTS ===")
        for insight in actionable_insights:
            logger.info(f"• {insight}")
    
    # Display formatted table with enhanced interpretations
    logger.info("\n=== FORMATTED TABLE WITH ENHANCED INTERPRETATIONS ===")
    formatted_table = EnhancedFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results
    )
    logger.info(formatted_table)
    
    # Show how to use the enhanced formatter through LogFormatter
    logger.info("\n=== USING LOGFORMATTER WITH ENHANCED INTERPRETATIONS ===")
    formatted_table_via_log_formatter = LogFormatter.format_enhanced_confluence_score_table(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results
    )
    logger.info(formatted_table_via_log_formatter)
    
    logger.info("\n=== DEMO COMPLETED ===")
    logger.info("To use enhanced interpretations in MarketMonitor, update the _process_analysis_result method:")
    logger.info("1. Import InterpretationGenerator at the top of monitor.py")
    logger.info("2. Change LogFormatter.format_confluence_score_table to LogFormatter.format_enhanced_confluence_score_table")
    logger.info("3. Remove the existing market interpretations section as it's now included in the enhanced table")

if __name__ == "__main__":
    demo_enhanced_interpretations() 