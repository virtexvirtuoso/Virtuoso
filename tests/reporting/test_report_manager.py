#!/usr/bin/env python3
"""
Test script for ReportManager functionality without Discord integration.

This script tests the ReportManager class for generating PDF and JSON reports
without requiring a Discord webhook URL.
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
logger = logging.getLogger('test_report_manager')

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
            'institutional_activity': 'Accumulation',
            'futures_sentiment': 'Long-biased'
        },
        'top_performers': [
            {'symbol': 'ETH/USDT', 'price': 3245.78, 'change_percent': '+5.2%', 'volume': '$2.1B'},
            {'symbol': 'SOL/USDT', 'price': 132.45, 'change_percent': '+4.7%', 'volume': '$1.5B'},
            {'symbol': 'BNB/USDT', 'price': 447.32, 'change_percent': '+3.8%', 'volume': '$1.1B'},
            {'symbol': 'MATIC/USDT', 'price': 0.91, 'change_percent': '+3.5%', 'volume': '$325M'},
            {'symbol': 'AVAX/USDT', 'price': 34.56, 'change_percent': '+3.1%', 'volume': '$412M'}
        ],
        'trading_signals': [
            {'symbol': 'BTC/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '4h'},
            {'symbol': 'ETH/USDT', 'direction': 'Buy', 'strength': 'Moderate', 'timeframe': '1h'},
            {'symbol': 'SOL/USDT', 'direction': 'Buy', 'strength': 'Strong', 'timeframe': '1d'},
            {'symbol': 'XRP/USDT', 'direction': 'Sell', 'strength': 'Weak', 'timeframe': '4h'}
        ],
        'notable_news': [
            {
                'title': 'SEC Approves Spot Ethereum ETF Applications',
                'source': 'Bloomberg',
                'impact': 'Highly Bullish'
            },
            {
                'title': 'Federal Reserve Signals No Rate Hikes in Next Meeting',
                'source': 'Wall Street Journal',
                'impact': 'Moderately Bullish'
            }
        ]
    }
    
    return market_data

async def format_market_report(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the market data into a simple message structure.
    
    Args:
        market_data: The market data to format
    
    Returns:
        Formatted message
    """
    # Create the message structure without Discord-specific formatting
    message = {
        "title": f"Market Summary Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "sections": []
    }
    
    # Add market overview section
    if 'market_overview' in market_data:
        message["sections"].append({
            "name": "Market Overview",
            "data": market_data['market_overview']
        })
    
    # Add other sections
    for section_name in ['market_sentiment', 'top_performers', 'trading_signals', 'notable_news']:
        if section_name in market_data:
            message["sections"].append({
                "name": section_name.replace('_', ' ').title(),
                "data": market_data[section_name]
            })
    
    return message

async def test_report_manager():
    """
    Test ReportManager functionality without Discord integration.
    """
    try:
        # Import required modules
        sys.path.append('.')
        from src.core.reporting.report_manager import ReportManager
        
        logger.info("Starting ReportManager test")
        
        # Initialize ReportManager
        logger.info("Initializing ReportManager")
        report_manager = ReportManager()
        
        # Generate sample market data
        logger.info("Generating sample market data")
        market_data = await generate_sample_market_data()
        
        # Create a simple formatted report (not Discord-specific)
        logger.info("Formatting market report")
        formatted_report = await format_market_report(market_data)
        
        # Create an exports directory if it doesn't exist
        os.makedirs('exports', exist_ok=True)
        
        # Generate timestamp for filename
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"report_manager_test_{timestamp_str}.pdf"
        pdf_path = os.path.join('exports', pdf_filename)
        
        # Format for reporting
        logger.info("Saving formatted report to JSON")
        with open(f'report_manager_test_{timestamp_str}.json', 'w') as f:
            json.dump(formatted_report, f, indent=2)
        
        # Generate the PDF report using ReportManager
        logger.info("Generating PDF report using ReportManager")
        success, pdf_path, json_path = await report_manager.generate_and_attach_report(
            signal_data=market_data,
            webhook_message=formatted_report,  # Note: This won't be used for Discord since we don't have a webhook URL
            signal_type='market_report',
            output_path=pdf_path
        )
        
        if success:
            logger.info(f"Successfully generated PDF report: {pdf_path}")
            logger.info(f"Successfully generated JSON report: {json_path}")
            print(f"Market report PDF generated successfully at: {pdf_path}")
            print(f"JSON data saved to: {json_path}")
            
            # Also show file sizes to confirm they were created properly
            pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
            json_size = os.path.getsize(json_path) if os.path.exists(json_path) else 0
            print(f"PDF size: {pdf_size} bytes")
            print(f"JSON size: {json_size} bytes")
            
            return True
        else:
            logger.error("Failed to generate reports")
            print("Error: Failed to generate reports")
            return False
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if 'report_manager' in locals():
            await report_manager.stop()
        logger.info("Test completed")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_report_manager()) 