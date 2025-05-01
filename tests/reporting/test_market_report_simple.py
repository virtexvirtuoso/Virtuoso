#!/usr/bin/env python3
"""
Simplified test script for generating a market report without Discord integration.

This script will generate sample market data and create a PDF report without requiring
a Discord webhook URL.
"""

import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_simple')

async def generate_sample_market_data() -> Dict[str, Any]:
    """Generate sample market data for testing."""
    
    # Create a sample market report data structure
    market_data = {
        'timestamp': int(time.time() * 1000),
        'market_overview': {
            'total_market_cap': '$1.92T',
            'btc_dominance': '49.2%',
            'daily_volume': '$78.5B',
            'market_trend': 'Bullish',
            'volatility': 'Moderate',
            'risk_level': 'Medium'
        },
        'market_sentiment': {
            'overall_sentiment': 'Bullish',
            'fear_greed_index': 72,
            'social_sentiment': 'Positive',
            'institutional_activity': 'Accumulation'
        },
        'top_performers': [
            {'symbol': 'ETH/USDT', 'price': 3245.78, 'change_percent': '+5.2%', 'volume': '$2.1B'},
            {'symbol': 'SOL/USDT', 'price': 132.45, 'change_percent': '+4.7%', 'volume': '$1.5B'},
            {'symbol': 'BNB/USDT', 'price': 447.32, 'change_percent': '+3.8%', 'volume': '$1.1B'}
        ],
        'trading_signals': [
            {'symbol': 'BTC/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '4h'},
            {'symbol': 'ETH/USDT', 'direction': 'Buy', 'strength': 'Moderate', 'timeframe': '1h'}
        ]
    }
    
    return market_data

async def test_simple_market_report():
    """
    Generate a basic market report without Discord integration.
    """
    try:
        # Import required modules
        sys.path.append('.')
        from src.core.reporting.pdf_generator import ReportGenerator
        
        logger.info("Starting simple market report test")
        
        # Generate sample market data
        logger.info("Generating sample market data")
        market_data = await generate_sample_market_data()
        
        # Save the market data to JSON for reference
        logger.info("Saving market data to JSON")
        with open('simple_market_report.json', 'w') as f:
            json.dump(market_data, f, indent=2)
        
        # Create an exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Generate timestamp for filename
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"simple_market_report_{timestamp_str}.pdf"
        pdf_path = os.path.join('exports', pdf_filename)
        
        # Create PDF generator directly
        logger.info("Creating PDF generator")
        pdf_generator = ReportGenerator()
        
        # Generate the PDF report
        logger.info("Generating PDF report")
        success = await pdf_generator.generate_market_report(market_data, output_path=pdf_path)
        
        if success:
            logger.info(f"Successfully generated PDF report: {pdf_path}")
            print(f"Market report PDF generated successfully at: {pdf_path}")
            print(f"JSON data saved to: simple_market_report.json")
            return True
        else:
            logger.error("Failed to generate PDF report")
            print("Error: Failed to generate PDF report")
            return False
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_simple_market_report()) 