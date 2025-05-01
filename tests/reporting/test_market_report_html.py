#!/usr/bin/env python3
"""
Test script to verify the HTML-based market report generation.

This script will:
1. Create sample market data
2. Generate an HTML-based PDF report
3. Optionally attach the PDF report to a Discord message
"""

import os
import sys
import json
import logging
import random
import asyncio
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# Import necessary modules
try:
    from src.core.reporting.report_manager import ReportManager
except ImportError as e:
    logger.error(f"Could not import ReportManager: {e}")
    logger.error("Make sure you're in the correct directory.")
    sys.exit(1)

def create_sample_market_data():
    """Create sample market report data for testing."""
    timestamp = int(time.time() * 1000)
    
    return {
        'timestamp': timestamp,
        'market_overview': {
            'regime': 'BULLISH',
            'trend_strength': '72.5%',
            'volatility': 'MODERATE',
            'average_change': '+1.8%',
            'market_cap': '$1.42T',
            'btc_dominance': '46.2%',
            'metrics': {
                'buy_signals': 18,
                'sell_signals': 7,
                'neutral_signals': 12
            }
        },
        'top_performers': [
            {
                'symbol': 'ETHUSDT',
                'price': 3245.75,
                'change_percent': 4.8,
                'volume': '1.2B'
            },
            {
                'symbol': 'SOLUSDT',
                'price': 142.30,
                'change_percent': 6.2,
                'volume': '825M'
            },
            {
                'symbol': 'AVAXUSDT',
                'price': 36.80,
                'change_percent': 5.5,
                'volume': '540M'
            },
            {
                'symbol': 'BNBUSDT',
                'price': 572.40,
                'change_percent': 3.1,
                'volume': '720M'
            },
            {
                'symbol': 'ADAUSDT',
                'price': 0.58,
                'change_percent': 3.8,
                'volume': '485M'
            }
        ],
        'market_sentiment': {
            'overall': 'BULLISH',
            'fear_greed_index': 72,
            'sentiment_change': '+5',
            'social_sentiment': 'POSITIVE',
            'funding_rates': 'POSITIVE',
            'institutional_flows': 'INCREASING'
        },
        'trading_signals': [
            {
                'symbol': 'BTCUSDT',
                'direction': 'BULLISH',
                'strength': 75,
                'price': 54321.98
            },
            {
                'symbol': 'ETHUSDT',
                'direction': 'BULLISH',
                'strength': 82,
                'price': 3245.75
            },
            {
                'symbol': 'SOLUSDT',
                'direction': 'BULLISH',
                'strength': 80,
                'price': 142.30
            },
            {
                'symbol': 'XRPUSDT',
                'direction': 'NEUTRAL',
                'strength': 55,
                'price': 0.58
            },
            {
                'symbol': 'DOGEUSDT',
                'direction': 'BEARISH',
                'strength': 35,
                'price': 0.12
            }
        ],
        'notable_news': [
            {
                'title': 'Federal Reserve Maintains Interest Rates, Hints at Future Cuts',
                'source': 'Financial Times',
                'impact': 'HIGH',
                'summary': 'The Federal Reserve kept interest rates unchanged but indicated potential cuts later this year, boosting market sentiment.'
            },
            {
                'title': 'Major Bank Announces Bitcoin Custody Services',
                'source': 'Bloomberg',
                'impact': 'MEDIUM',
                'summary': 'A top-tier global bank has announced plans to offer Bitcoin custody services to institutional clients starting next quarter.'
            },
            {
                'title': 'New Ethereum Upgrade Successfully Implemented',
                'source': 'CoinDesk',
                'impact': 'MEDIUM',
                'summary': 'The latest Ethereum upgrade has been successfully implemented, improving network efficiency and reducing gas fees.'
            }
        ],
        'smart_money_index': {
            'index': 68.5,
            'trend': 'INCREASING',
            'change': '+3.2',
            'institutional_activity': 'BUYING',
            'whale_transaction_count': 145,
            'analysis': 'Smart money investors showing increased accumulation over the past week.'
        },
        'futures_premium': {
            'average_premium': 2.8,
            'trend': 'STABLE',
            'contango': 'MODERATE',
            'data': [
                {
                    'symbol': 'BTCUSDT',
                    'spot_price': 54321.98,
                    'futures_price': 55642.50,
                    'premium_percent': 2.43
                },
                {
                    'symbol': 'ETHUSDT',
                    'spot_price': 3245.75,
                    'futures_price': 3348.25,
                    'premium_percent': 3.16
                },
                {
                    'symbol': 'SOLUSDT',
                    'spot_price': 142.30,
                    'futures_price': 146.80,
                    'premium_percent': 3.16
                }
            ]
        },
        'technical_levels': {
            'btc_key_levels': {
                'resistance_1': 56000,
                'resistance_2': 58500,
                'support_1': 52000,
                'support_2': 50000
            },
            'eth_key_levels': {
                'resistance_1': 3400,
                'resistance_2': 3600,
                'support_1': 3100,
                'support_2': 2900
            }
        },
        'market_recommendations': [
            'Consider increasing allocation to large-cap cryptocurrencies',
            'Watch for potential breakout in Ethereum above $3400',
            'Monitor funding rates for signs of excessive leverage',
            'Be cautious with smaller altcoins as market sentiment could shift quickly',
            'Maintain appropriate stop losses despite bullish outlook'
        ]
    }

async def main():
    """Main test function to verify the HTML market report generation."""
    logger.info("Starting HTML market report generation test")
    
    # Get webhook URL from command-line arguments or environment
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("No DISCORD_WEBHOOK_URL environment variable found.")
        webhook_url = input("Please enter your Discord webhook URL (press Enter to generate PDF without sending to Discord): ")
    
    # Create sample market data
    market_data = create_sample_market_data()
    logger.info("Created sample market data")
    
    # Create ReportManager instance with explicit template directory
    template_dir = os.path.join(os.getcwd(), 'templates')
    logger.info(f"Using template directory: {template_dir}")
    logger.info(f"Market report template file exists: {os.path.exists(os.path.join(template_dir, 'market_report_dark.html'))}")
    
    config = {
        'template_dir': template_dir,
        'base_dir': os.path.join(os.getcwd(), 'reports')
    }
    
    report_manager = ReportManager(config=config)
    logger.info("Initialized ReportManager")
    
    try:
        # Start the report manager session
        await report_manager.start()
        logger.info("Started ReportManager session")
        
        # Generate output path
        output_dir = os.path.join(os.getcwd(), 'reports', 'pdf')
        os.makedirs(output_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"market_report_{timestamp_str}.pdf")
        
        if webhook_url:
            # Create a basic webhook message for market report
            webhook_message = {
                "username": "Virtuoso Market Reports",
                "content": "📊 **Market Summary Report**",
                "embeds": [{
                    "title": "Crypto Market Overview",
                    "description": f"Market regime: {market_data['market_overview']['regime']} | Trend strength: {market_data['market_overview']['trend_strength']}",
                    "color": 0x4CAF50,  # Green for bullish
                    "footer": {
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Virtuoso Trading System"
                    }
                }]
            }
            
            # Generate and attach report
            logger.info("Generating and attaching market report PDF to Discord...")
            success, pdf_path, json_path = await report_manager.generate_and_attach_report(
                signal_data=market_data,
                webhook_message=webhook_message,
                webhook_url=webhook_url,
                signal_type='market_report'
            )
        else:
            # Just generate the report without sending to Discord
            logger.info("Generating market report PDF without sending to Discord...")
            success = await report_manager.pdf_generator.generate_market_html_report(
                market_data=market_data,
                output_path=output_path
            )
            pdf_path = output_path if success else None
            json_path = None
        
        # Report results
        if success:
            logger.info("✅ Successfully generated market report PDF!")
            logger.info(f"📄 PDF report: {pdf_path}")
            if json_path:
                logger.info(f"📊 JSON data: {json_path}")
        else:
            logger.error("❌ Failed to generate market report PDF")
            if pdf_path:
                logger.info(f"📄 PDF report (may be incomplete): {pdf_path}")
            if json_path:
                logger.info(f"📊 JSON data: {json_path}")
        
        # Clean up
        await report_manager.stop()
        logger.info("Stopped ReportManager session")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
    
    logger.info("Test completed")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 