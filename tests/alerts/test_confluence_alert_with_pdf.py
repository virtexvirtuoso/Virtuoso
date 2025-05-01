#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Confluence Alert with PDF Attachment

This script tests sending a confluence alert with a PDF report attachment
to Discord webhook. It creates a sample signal, generates a PDF report,
and explicitly sets up the file attachment parameter for the webhook.
"""

import os
import sys
import json
import logging
import asyncio
import numpy as np
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import matplotlib.pyplot as plt
from pathlib import Path
import aiohttp
import aiofiles

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import necessary modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.core.reporting.report_manager import ReportManager
    from src.core.reporting.pdf_generator import ReportGenerator
except ImportError:
    logger.error("Failed to import required modules. Make sure you're running from the project root.")
    sys.exit(1)

def create_sample_ohlcv_data(periods=100):
    """Create sample OHLCV price data for testing."""
    # Create sample historical data
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=periods)
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # Start with a price and generate fake OHLCV data
    start_price = 93000.0  # BTC price
    price = start_price
    data = []
    
    for i in range(periods):
        # Random price movement with some trend
        price_change = np.random.normal(0, 1) * price * 0.01  # 1% standard deviation
        
        # Add some upward trend for the recent candles
        if i > periods * 0.8:  # Last 20% of candles
            price_change += price * 0.002  # Small upward bias
        
        open_price = price
        close_price = max(0, price + price_change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 1) * 0.005))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 1) * 0.005))
        volume = abs(np.random.normal(0, 1) * 100) + 100  # Random volume
        
        data.append([
            dates[i],
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])
        
        price = close_price
    
    # Create DataFrame
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def create_sample_signal_data():
    """Create a detailed sample signal with components for testing."""
    current_price = 93452.0  # BTC price
    
    # Create components with numpy.float64 values to test the fix
    components = {
        'technical': np.float64(75.5),
        'volume': np.float64(68.2),
        'orderbook': np.float64(72.8),
        'orderflow': np.float64(70.3),
        'sentiment': np.float64(65.9),
        'price_structure': np.float64(78.4)
    }
    
    # Calculate weighted score
    weights = {
        'technical': 0.25,
        'volume': 0.15,
        'orderbook': 0.20,
        'orderflow': 0.20,
        'sentiment': 0.10,
        'price_structure': 0.10
    }
    
    score = sum(components[key] * weights[key] for key in components)
    
    # Create interpretations for each component
    interpretations = [
        "Technical indicators showing strong bullish momentum with RSI at 68",
        "Volume analysis indicates accumulation pattern over the last 3 days",
        "Orderbook depth showing stronger support than resistance levels",
        "Order flow ratio at 1.35 (buy/sell) indicating buying pressure",
        f"Current price of ${current_price} above all major moving averages",
        "Recent price action testing previous resistance as support"
    ]
    
    # Create detailed results for PDF report
    results = {
        "price": current_price,
        "24h_high": current_price * 1.02,
        "24h_low": current_price * 0.98,
        "24h_volume": 7500000000,  # 7.5B
        "open_interest": 52000,
        "funding_rate": 0.00004124,
        "volume_ratio": 1.35,
        "volatility": 0.025,
        "rsi": 68,
        "macd": {
            "macd": 45.2,
            "signal": 42.8,
            "histogram": 2.4
        },
        "moving_averages": {
            "ma_20": current_price * 0.97,
            "ma_50": current_price * 0.95,
            "ma_100": current_price * 0.92,
            "ma_200": current_price * 0.88
        }
    }
    
    # Create signal data
    return {
        'symbol': 'BTCUSDT',
        'score': score,
        'signal': 'BUY',
        'strength': 'Strong',
        'emoji': '🚀',
        'timestamp': int(time.time() * 1000),  # Current time in milliseconds
        'price': current_price,
        'components': components,
        'buy_threshold': 60.0,
        'sell_threshold': 40.0,
        'reliability': 85.0,
        'results': results,
        'interpretations': interpretations,
        'metadata': {
            'exchange': 'bybit',
            'timeframe': '1h',
            'market_type': 'futures'
        },
        'targets': {
            'entry': current_price,
            'stop_loss': current_price * 0.95,
            'take_profit_1': current_price * 1.05,
            'take_profit_2': current_price * 1.08,
            'take_profit_3': current_price * 1.12,
        }
    }

def create_test_config() -> Dict[str, Any]:
    """Create a test configuration with the Discord webhook URL."""
    # Get Discord webhook URL from environment
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
    
    if not discord_webhook_url:
        logger.error("No DISCORD_WEBHOOK_URL environment variable found.")
        logger.error("Please set the DISCORD_WEBHOOK_URL environment variable.")
        sys.exit(1)
    
    # Print the webhook URL (masked for security)
    if discord_webhook_url and len(discord_webhook_url) > 20:
        logger.info(f"Using Discord webhook URL from environment: {discord_webhook_url[:15]}...{discord_webhook_url[-10:]}")
    
    # Configuration with webhook URL
    return {
        "monitoring": {
            "alerts": {
                "discord": {
                    "webhook_url": discord_webhook_url
                },
                "thresholds": {
                    "buy": 60,
                    "sell": 40
                }
            }
        },
        "reporting": {
            "enabled": True,
            "attach_pdf": True,
            "attach_json": True,
            "template_dir": "templates",
            "base_url": str(Path(os.getcwd()).absolute().as_uri()) + "/"  # Add base URL for resolving relative paths
        }
    }

def create_sample_charts(ohlcv_data, signal_data):
    """Create sample charts for the PDF report."""
    # Ensure exports directory exists
    exports_dir = Path("exports")
    exports_dir.mkdir(exist_ok=True)
    
    # Create price chart
    plt.figure(figsize=(10, 6))
    plt.plot(ohlcv_data['timestamp'].iloc[-30:], ohlcv_data['close'].iloc[-30:], 'b-')
    plt.title(f"{signal_data['symbol']} Price Chart")
    plt.grid(True)
    plt.tight_layout()
    price_chart_path = exports_dir / "btcusdt_chart.png"
    plt.savefig(price_chart_path)
    plt.close()
    
    # Create component chart
    plt.figure(figsize=(10, 6))
    components = signal_data['components']
    labels = list(components.keys())
    values = [float(components[k]) for k in labels]
    
    # Create bar chart
    plt.bar(labels, values, color='blue')
    plt.axhline(y=60, color='green', linestyle='--', label='Buy Threshold')
    plt.axhline(y=40, color='red', linestyle='--', label='Sell Threshold')
    plt.title('Component Scores')
    plt.ylabel('Score')
    plt.ylim(0, 100)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    
    component_chart_path = exports_dir / "component_chart.png"
    plt.savefig(component_chart_path)
    plt.close()
    
    return {
        'price_chart': str(price_chart_path.absolute()),
        'component_chart': str(component_chart_path.absolute())
    }

async def send_file_to_discord(webhook_url, filepath, message):
    """Send a file directly to Discord webhook."""
    logger.info(f"Preparing to send file: {filepath}")
    
    # Verify file exists
    if not os.path.exists(filepath):
        logger.error(f"File doesn't exist: {filepath}")
        return False, None
    
    file_size = os.path.getsize(filepath)
    logger.info(f"File size: {file_size} bytes")
    
    try:
        # Prepare form data with file
        form = aiohttp.FormData()
        
        # Add the payload_json field
        form.add_field(
            name='payload_json',
            value=json.dumps(message),
            content_type='application/json'
        )
        
        # Open and add the file
        async with aiofiles.open(filepath, 'rb') as f:
            file_content = await f.read()
            
            form.add_field(
                name='file',
                value=file_content,
                filename=os.path.basename(filepath),
                content_type='application/octet-stream'
            )
        
        logger.info("File added to form data")
        
        # Send request to Discord
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Virtuoso-Trading-Bot/1.0'
            }
            
            logger.info(f"Sending POST request to Discord webhook...")
            async with session.post(webhook_url, data=form, headers=headers) as response:
                status = response.status
                logger.info(f"Response status: {status}")
                
                if response.content_type == 'application/json':
                    response_data = await response.json()
                else:
                    response_text = await response.text()
                    response_data = {'text': response_text}
                
                return status in (200, 204), response_data
    
    except Exception as e:
        logger.error(f"Error sending file to Discord: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, None

async def test_confluence_alert_with_pdf():
    """Test sending a confluence alert with PDF attachment."""
    try:
        # Create test configuration
        config = create_test_config()
        webhook_url = config["monitoring"]["alerts"]["discord"]["webhook_url"]
        
        if not webhook_url:
            logger.error("No Discord webhook URL configured. Cannot proceed with test.")
            logger.error("Please set the DISCORD_WEBHOOK_URL environment variable.")
            return False
        
        # Import alert manager
        alert_manager = AlertManager(config)
        logger.info(f"Initialized AlertManager with webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
        
        # Create sample data
        signal_data = create_sample_signal_data()
        ohlcv_data = create_sample_ohlcv_data()
        
        logger.info(f"Created sample signal data for {signal_data['symbol']} with score {signal_data['score']:.2f}")
        
        # Create sample charts
        chart_paths = create_sample_charts(ohlcv_data, signal_data)
        logger.info(f"Created sample charts at {chart_paths}")
        
        # Create the Discord message format
        symbol = signal_data.get("symbol", "Unknown")
        score = signal_data.get("score", 0)
        signal_type = signal_data.get("signal", "UNKNOWN")
        
        # Create message content
        message_content = f"🚨 [TEST] Confluence Alert for {symbol}\n"
        message_content += f"Signal Type: {signal_type}\n"
        message_content += f"Confluence Score: {score:.2f}/100\n"
        message_content += f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Create Discord webhook message
        webhook_message = {
            "content": message_content,
            "embeds": [
                {
                    "title": f"{signal_type} Signal for {symbol}",
                    "description": "This is a test of the PDF report attachment functionality",
                    "color": 5814783 if signal_type == "BUY" else 15548997,
                    "fields": [
                        {
                            "name": "Confluence Score",
                            "value": f"{score:.2f}/100",
                            "inline": True
                        },
                        {
                            "name": "Price",
                            "value": f"${signal_data.get('price', 0):.2f}",
                            "inline": True
                        }
                    ]
                }
            ]
        }
        
        # Initialize ReportManager separately
        report_manager = ReportManager(config)
        logger.info("Created ReportManager for PDF generation")
        
        # Generate the PDF report first
        # Use a different directory path for the test
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.getcwd(), "exports")
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_filename = f"{symbol}_{timestamp_str}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        logger.info(f"Generating PDF report to: {pdf_path}")
        
        # Generate the report directly
        success = await report_manager.pdf_generator.generate_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_path=pdf_path
        )
            
        if not success:
            logger.error("Failed to generate PDF report")
            return False
            
        logger.info(f"PDF report generated successfully: {pdf_path}")
        
        # Check if the file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist at path: {pdf_path}")
            return False
            
        logger.info(f"PDF file exists at: {pdf_path}")
        
        # Send the message with the file attachment
        success, response = await send_file_to_discord(
            webhook_url=webhook_url,
            filepath=pdf_path,
            message=webhook_message
        )
        
        if success:
            logger.info("Successfully sent Discord webhook with PDF attachment")
            logger.info(f"Response: {response}")
            return True
        else:
            logger.error(f"Failed to send Discord webhook: {response}")
            return False
        
    except Exception as e:
        logger.error(f"Error in test_confluence_alert_with_pdf: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main function to run the test."""
    logger.info("Starting test of confluence alert with PDF attachment")
    
    # Run the test
    success = await test_confluence_alert_with_pdf()
    
    if success:
        logger.info("✅ Test completed successfully! Check Discord for the message with PDF attachment.")
    else:
        logger.error("❌ Test failed. See logs for details.")
    
    return success

if __name__ == "__main__":
    # Run the main function
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 