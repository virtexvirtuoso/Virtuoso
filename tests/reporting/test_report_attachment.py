#!/usr/bin/env python3
"""
Test script to verify that PDF report generation and Discord attachment works correctly.
This script will:
1. Create sample signal data
2. Generate a PDF report
3. Attach the PDF report to a Discord message
4. Send the message to a Discord webhook

Usage:
  python test_report_attachment.py [webhook_url]
  
If webhook_url is not provided, the script will:
  1. Check for DISCORD_WEBHOOK_URL environment variable
  2. Prompt the user to enter a webhook URL
  3. Generate the PDF report without sending to Discord if no URL is provided
"""

import os
import sys
import json
import logging
import random
import asyncio
import pandas as pd
from datetime import datetime, timedelta

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import necessary modules
try:
    from src.core.reporting.report_manager import ReportManager
except ImportError as e:
    logger.error(f"Could not import ReportManager: {e}")
    logger.error("Make sure you're in the correct directory.")
    sys.exit(1)

def create_sample_signal_data():
    """Create sample trading signal data for testing."""
    return {
        'symbol': 'BTCUSDT',
        'signal': 'BULLISH',
        'score': 75.5,
        'reliability': 0.85,
        'price': 54321.98,
        'timestamp': datetime.now(),
        'components': {
            'RSI': {'score': 82, 'impact': 3.2, 'interpretation': 'Overbought conditions indicating potential reversal'},
            'MACD': {'score': 71, 'impact': 2.5, 'interpretation': 'Bullish crossover suggesting upward momentum'},
            'Bollinger Bands': {'score': 68, 'impact': 1.8, 'interpretation': 'Price near upper band with expanding volatility'},
            'Volume': {'score': 65, 'impact': 1.5, 'interpretation': 'Above average volume supporting the move'},
            'Moving Averages': {'score': 80, 'impact': 3.0, 'interpretation': 'Price above all major MAs in a bullish alignment'},
            'Support/Resistance': {'score': 60, 'impact': 1.2, 'interpretation': 'Trading above recent resistance turned support'},
            'Ichimoku Cloud': {'score': 72, 'impact': 2.0, 'interpretation': 'Price above the cloud in a bullish trend'}
        },
        'interpretations': {
            'RSI': 'Overbought conditions indicating potential reversal',
            'MACD': 'Bullish crossover suggesting upward momentum',
            'Bollinger Bands': 'Price near upper band with expanding volatility',
            'Volume': 'Above average volume supporting the move',
            'Moving Averages': 'Price above all major MAs in a bullish alignment'
        },
        'insights': [
            'Strong bullish momentum supported by multiple indicators',
            'Recent breakout above key resistance level at $52,000',
            'Increased institutional buying detected in on-chain data',
            'Reduced selling pressure from miners over the past week'
        ],
        'actionable_insights': [
            'Consider entering long positions with tight stop losses',
            'Target the previous high at $58,500 for first take profit',
            'Monitor volume for confirmation of continued uptrend',
            'Watch for potential resistance at $56,000 psychological level'
        ],
        'entry_price': 54300,
        'stop_loss': 51500,
        'targets': {
            'T1': {'price': 56800, 'size': 0.5},
            'T2': {'price': 58500, 'size': 0.3},
            'T3': {'price': 60000, 'size': 0.2}
        }
    }

def create_sample_ohlcv_data(symbol='BTCUSDT', periods=50):
    """Create sample OHLCV price data for testing."""
    base_price = 50000
    volatility = 0.02
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods/24)  # Assuming hourly data
    
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # Initialize with random price movements
    df = pd.DataFrame({
        'timestamp': dates,
        'open': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)],
        'close': [base_price * (1 + random.uniform(-volatility/2, volatility/2)) for _ in range(periods)],
        'volume': [random.uniform(100, 1000) for _ in range(periods)]
    })
    
    # Add high and low values
    for i in range(periods):
        if df.loc[i, 'open'] > df.loc[i, 'close']:
            df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + random.uniform(0, volatility/4))
            df.loc[i, 'low'] = df.loc[i, 'close'] * (1 - random.uniform(0, volatility/4))
        else:
            df.loc[i, 'high'] = df.loc[i, 'close'] * (1 + random.uniform(0, volatility/4))
            df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - random.uniform(0, volatility/4))
    
    # Make the last price match the signal price
    df.loc[periods-1, 'close'] = 54321.98
    
    return df

def create_discord_message(signal_data):
    """Create a sample Discord message with the signal data."""
    # Determine color based on signal type
    if signal_data.get('signal', '').upper() == 'BULLISH':
        color = 0x4CAF50  # Green
        emoji = "💹"
    elif signal_data.get('signal', '').upper() == 'BEARISH':
        color = 0xF44336  # Red
        emoji = "📉"
    else:
        color = 0xFFC107  # Amber/yellow for neutral
        emoji = "📊"
    
    # Create Discord message with embed
    return {
        'content': f"🚨 **New Trading Signal Detected!**",
        'embeds': [{
            'title': f"{emoji} {signal_data['symbol']}: {signal_data.get('signal', 'SIGNAL')} (Score: {signal_data['score']})",
            'description': signal_data.get('insights', [""])[0],
            'color': color,
            'fields': [
                {
                    'name': "Current Price",
                    'value': f"${signal_data['price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Reliability",
                    'value': f"{signal_data['reliability']*100:.0f}%",
                    'inline': True
                },
                {
                    'name': "Entry Price",
                    'value': f"${signal_data['entry_price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Stop Loss",
                    'value': f"${signal_data['stop_loss']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Target 1",
                    'value': f"${signal_data['targets']['T1']['price']:,.2f}",
                    'inline': True
                },
                {
                    'name': "Risk/Reward",
                    'value': "1:2.5",
                    'inline': True
                }
            ],
            'footer': {
                'text': f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} • Virtuoso Trading Bot"
            }
        }]
    }

async def main():
    """Main test function to verify the report generation and attachment."""
    logger.info("Starting PDF report and Discord attachment test")
    
    # Get webhook URL from command-line arguments or environment
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        logger.warning("No DISCORD_WEBHOOK_URL environment variable found.")
        webhook_url = input("Please enter your Discord webhook URL (press Enter to generate PDF without sending to Discord): ")
    
    # Create sample data
    signal_data = create_sample_signal_data()
    ohlcv_data = create_sample_ohlcv_data(symbol=signal_data['symbol'])
    webhook_message = create_discord_message(signal_data)
    
    logger.info(f"Created sample data for {signal_data['symbol']}")
    
    # Create ReportManager instance with explicit template directory
    template_dir = os.path.join(os.getcwd(), 'templates')
    logger.info(f"Using template directory: {template_dir}")
    logger.info(f"Template file exists: {os.path.exists(os.path.join(template_dir, 'trading_report_dark.html'))}")
    
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
        
        if webhook_url:
            # Generate and attach report
            logger.info("Generating and attaching PDF report to Discord...")
            success, pdf_path, json_path = await report_manager.generate_and_attach_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                webhook_message=webhook_message,
                webhook_url=webhook_url
            )
        else:
            # Just generate the report without sending to Discord
            logger.info("Generating PDF report without sending to Discord...")
            output_dir = os.path.join(os.getcwd(), 'reports', 'pdf')
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"{signal_data['symbol'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            success = await report_manager.pdf_generator.generate_report(
                signal_data=signal_data,
                ohlcv_data=ohlcv_data,
                output_path=pdf_path
            )
            json_path = None
        
        # Report results
        if success:
            logger.info("✅ Successfully generated and attached report!")
            logger.info(f"📄 PDF report: {pdf_path}")
            logger.info(f"📊 JSON data: {json_path}")
        else:
            logger.error("❌ Failed to generate and attach report")
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