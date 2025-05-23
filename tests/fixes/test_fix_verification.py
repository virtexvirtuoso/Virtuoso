#!/usr/bin/env python
"""
Test script to verify the fixes for:
1. Confluence score thresholds being used from config.yaml
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# Add the project root to sys.path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from src.core.config.config_manager import ConfigManager
from src.core.formatting.formatter import LogFormatter

async def test_confluence_score_thresholds():
    """Test that formatter properly uses thresholds from config."""
    print("Testing confluence score thresholds...")
    
    # Get thresholds from config
    config_manager = ConfigManager()
    thresholds = config_manager.get_value('confluence.thresholds', {})
    buy_threshold = float(thresholds.get('buy', 60.0))
    sell_threshold = float(thresholds.get('sell', 40.0))
    
    print(f"Config thresholds: buy={buy_threshold}, sell={sell_threshold}")
    
    # Test cases with different scores
    test_scores = [
        {"score": 75.0, "expected": "BULLISH"},
        {"score": buy_threshold + 0.1, "expected": "BULLISH"},
        {"score": buy_threshold - 0.1, "expected": "NEUTRAL"},
        {"score": (buy_threshold + sell_threshold) / 2, "expected": "NEUTRAL"},
        {"score": sell_threshold + 0.1, "expected": "NEUTRAL"},
        {"score": sell_threshold - 0.1, "expected": "BEARISH"},
        {"score": 30.0, "expected": "BEARISH"},
    ]
    
    # Create mock data
    symbol = "BTCUSDT"
    components = {
        "orderbook": 70.0,
        "volume": 65.0,
        "technical": 60.0,
        "sentiment": 55.0,
        "orderflow": 75.0,
        "price_structure": 65.0
    }
    results = {
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold
    }
    
    success = True
    for test in test_scores:
        score = test["score"]
        expected = test["expected"]
        
        # Format the table with our score
        table = LogFormatter.format_confluence_score_table(
            symbol=symbol,
            confluence_score=score,
            components=components,
            results=results,
            reliability=0.9
        )
        
        # Extract the actual status from the table (this is a simple text extraction)
        status_line = [line for line in table.split('\n') if "OVERALL SCORE" in line][0]
        actual_status = status_line.split("(")[1].split(")")[0]
        
        if actual_status != expected:
            print(f"❌ FAILED: Score {score} -> Expected {expected}, Got {actual_status}")
            success = False
        else:
            print(f"✅ PASSED: Score {score} -> {actual_status}")
    
    if success:
        print("✅ All confluence score threshold tests passed!")
    else:
        print("❌ Some confluence score threshold tests failed!")

async def main():
    """Run all tests."""
    print("Starting verification tests...\n")
    
    await test_confluence_score_thresholds()
    
    print("\nTests completed.")

if __name__ == "__main__":
    asyncio.run(main()) 