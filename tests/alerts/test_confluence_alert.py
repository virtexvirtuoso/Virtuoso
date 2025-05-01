#!/usr/bin/env python3
"""
Test script to verify that confluence alerts with PDF reports are working correctly.
This script will:
1. Create a sample trading signal
2. Generate a confluence alert
3. Generate a PDF report
4. Send the alert and PDF to Discord
5. Log the results

Usage:
  export DISCORD_WEBHOOK_URL="your_webhook_url_here"
  python test_confluence_alert.py
"""

import os
import sys
import json
import logging
import asyncio
import numpy as np
import random
import time
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the Python path
sys.path.append(os.getcwd())

# Import project modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.core.reporting.report_manager import ReportManager
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running from the project root directory")
    sys.exit(1)

def create_sample_ohlcv_data(periods=100):
    """Create sample OHLCV price data for testing."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=periods/24)  # Hourly data
    
    dates = pd.date_range(start=start_date, end=end_date, periods=periods)
    
    # Create a trending price series with some volatility
    base_price = 95000
    trend = np.linspace(0, 0.05, periods)  # 5% uptrend
    volatility = 0.02  # 2% volatility
    
    # Generate price data
    random.seed(42)  # For reproducibility
    
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    
    # Generate OHLCV with random walk
    price = base_price
    for i in range(periods):
        # Calculate change with trend and volatility
        change = trend[i] + random.uniform(-volatility, volatility)
        
        # Calculate OHLC
        open_price = price
        if random.random() > 0.5:  # 50% chance of close being higher than open
            close_price = open_price * (1 + change)
            high_price = close_price * (1 + random.uniform(0, volatility/2))
            low_price = open_price * (1 - random.uniform(0, volatility/2))
        else:
            close_price = open_price * (1 - change)
            high_price = open_price * (1 + random.uniform(0, volatility/2))
            low_price = close_price * (1 - random.uniform(0, volatility/2))
        
        # Add some volume variability
        volume = random.uniform(800, 1200)
        
        # Store values
        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        volumes.append(volume)
        
        # Update price for next iteration
        price = close_price
    
    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df

def create_component_scores():
    """Create sample component scores for testing."""
    return {
        "RSI": 75.5,
        "MACD": 65.2,
        "Bollinger Bands": 72.1,
        "Volume Profile": 68.5,
        "Support/Resistance": 80.0,
        "Moving Averages": 78.3
    }

def create_component_weights():
    """Create sample component weights for testing."""
    return {
        "RSI": 1.0,
        "MACD": 1.0,
        "Bollinger Bands": 0.8,
        "Volume Profile": 0.8,
        "Support/Resistance": 1.2,
        "Moving Averages": 1.0
    }

def create_component_results():
    """Create sample component results with interpretations."""
    components = create_component_scores()
    
    results = {}
    for name, score in components.items():
        impact = abs(score - 50) / 10.0  # Higher deviation from neutral = higher impact
        
        interpretation = ""
        if name == "RSI":
            interpretation = "Strong bullish momentum with RSI above 70, indicating buying pressure."
        elif name == "MACD":
            interpretation = "Bullish crossover with MACD line above signal line and histogram expanding."
        elif name == "Bollinger Bands":
            interpretation = "Price testing upper band with expanding bandwidth, suggesting trend strength."
        elif name == "Volume Profile":
            interpretation = "Increasing volume on up moves, decreasing on down moves. Bull volume dominance."
        elif name == "Support/Resistance":
            interpretation = "Price recently broke key resistance at $94,500 and is now testing it as support."
        elif name == "Moving Averages":
            interpretation = "Price above all major moving averages, with 50 EMA crossing above 200 EMA (golden cross)."
        
        results[name] = {
            "score": score,
            "impact": impact,
            "interpretation": interpretation
        }
    
    return results

async def test_confluence_alert():
    """Test sending a confluence alert with PDF attachment."""
    alert_manager = None
    report_manager = None
    
    try:
        # Get webhook URL from environment
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        
        if not webhook_url:
            logger.error("DISCORD_WEBHOOK_URL environment variable not set")
            logger.error("Please set the webhook URL: export DISCORD_WEBHOOK_URL='your_webhook_url'")
            return False
        
        logger.info(f"Using webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
        
        # Create configuration
        config = {
            "monitoring": {
                "alerts": {
                    "enabled": True,
                    "levels": ["info", "warning", "error", "critical"],
                    "handlers": ["discord"],
                    "discord": {
                        "enabled": True,
                        "webhook_url": webhook_url,
                        "username": "Virtuoso Trading Bot",
                        "avatar_url": "",
                        "embed_color": {
                            "info": 3447003,
                            "warning": 16776960,
                            "error": 15158332,
                            "critical": 10038562
                        }
                    }
                }
            },
            "reporting": {
                "enabled": True,
                "attach_pdf": True,
                "template_dir": "src/core/reporting/templates",
                "base_url": str(Path(os.getcwd()).absolute().as_uri()) + "/"
            }
        }
        
        # Initialize managers
        alert_manager = AlertManager(config)
        report_manager = ReportManager(config)
        
        # Start sessions
        await alert_manager._init_client_session()
        await report_manager.start()
        
        # Create sample data
        symbol = "BTCUSDT"
        components = create_component_scores()
        weights = create_component_weights()
        results = create_component_results()
        
        # Calculate confluence score
        total_weight = sum(weights.values())
        weighted_sum = sum(score * weights.get(comp, 1.0) for comp, score in components.items())
        confluence_score = weighted_sum / total_weight
        
        logger.info(f"Created sample data for {symbol} with confluence score {confluence_score:.2f}")
        
        # Create signal data
        signal_data = {
            "symbol": symbol,
            "exchange": "Bybit",
            "timestamp": datetime.now().isoformat(),
            "signal": "BUY" if confluence_score >= 60 else "SELL" if confluence_score <= 40 else "NEUTRAL",
            "score": confluence_score,
            "reliability": 0.85,
            "price": 95423.50,
            "components": results,
            "insights": [
                "Multiple technical indicators showing bullish alignment",
                "Recent break of key resistance level with increasing volume",
                "Momentum indicators confirming uptrend continuation"
            ],
            "actionable_insights": [
                "Consider entering long positions with defined risk parameters",
                "Initial target at $98,500 (previous resistance level)",
                "Set stop loss at $92,800 (below recent support)"
            ],
            "entry_price": 95423.50,
            "stop_loss": 92800.00,
            "targets": {
                "T1": {"price": 98500.00, "percent": 3.22, "size": 50},
                "T2": {"price": 100000.00, "percent": 4.80, "size": 30},
                "T3": {"price": 103000.00, "percent": 7.94, "size": 20}
            }
        }
        
        # Generate OHLCV data
        ohlcv_data = create_sample_ohlcv_data()
        
        # Ensure exports directory exists
        exports_dir = Path("exports")
        exports_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate PDF report
        logger.info("Generating PDF report...")
        success, pdf_path, json_path = await report_manager.generate_and_attach_report(
            signal_data=signal_data,
            ohlcv_data=ohlcv_data,
            output_path=f"exports/{symbol}_{timestamp_str}.pdf"
        )
        
        if not success or not pdf_path:
            logger.error("Failed to generate PDF report")
            return False
        
        # Verify the PDF exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file does not exist at: {pdf_path}")
            return False
        
        logger.info(f"PDF generated successfully: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
        
        # Create a formatted alert message
        signal_type = signal_data["signal"]
        color = 0x4CAF50 if signal_type == "BUY" else 0xF44336 if signal_type == "SELL" else 0xFFC107
        
        # Create message content
        message_content = f"🚨 **Confluence Alert for {symbol}**\n"
        message_content += f"Signal Type: {signal_type}\n"
        message_content += f"Confluence Score: {confluence_score:.2f}/100\n"
        message_content += f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message_content += f"PDF Report Attached 📎"
        
        # Create components text
        components_text = ""
        for name, comp_data in results.items():
            score_val = comp_data["score"]
            impact = comp_data["impact"]
            components_text += f"• **{name}**: {score_val:.1f} (impact: {impact:.1f})\n"
        
        # Create webhook message
        webhook_message = {
            "content": message_content,
            "embeds": [
                {
                    "title": f"{signal_type} Signal for {symbol}",
                    "description": "Confluence alert with detailed component breakdown.",
                    "color": color,
                    "fields": [
                        {
                            "name": "Confluence Score",
                            "value": f"{confluence_score:.2f}/100",
                            "inline": True
                        },
                        {
                            "name": "Price",
                            "value": f"${signal_data.get('price', 0):,.2f}",
                            "inline": True
                        },
                        {
                            "name": "Reliability",
                            "value": f"{signal_data.get('reliability', 0)*100:.0f}%",
                            "inline": True
                        },
                        {
                            "name": "Component Breakdown",
                            "value": components_text or "No components available",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • PDF Report Attached"
                    }
                }
            ]
        }
        
        # Prepare file attachment
        files = [
            {
                "path": pdf_path,
                "filename": os.path.basename(pdf_path),
                "description": f"Trading signal report for {symbol}"
            }
        ]
        
        # Send the webhook message with PDF attachment using updated AlertManager
        logger.info(f"Sending Discord webhook with PDF attachment: {pdf_path}")
        success, response = await alert_manager.send_discord_webhook_message(
            webhook_message=webhook_message,
            files=files
        )
        
        if success:
            logger.info("✅ Successfully sent Discord webhook with PDF attachment")
            if response:
                logger.info(f"Response status: {response.get('id', 'Unknown message ID')}")
            return True
        else:
            logger.error(f"Failed to send Discord webhook: {response}")
            return False
        
    except Exception as e:
        logger.error(f"Error in test_confluence_alert: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        # Clean up
        if alert_manager:
            try:
                await alert_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping AlertManager: {e}")
                
        if report_manager:
            try:
                await report_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping ReportManager: {e}")

async def main():
    """Main function to run the test."""
    logger.info("=" * 80)
    logger.info("Starting Confluence Alert Test")
    logger.info("=" * 80)
    
    # Run the test
    success = await test_confluence_alert()
    
    if success:
        logger.info("=" * 80)
        logger.info("✅ TEST SUCCESSFUL - Check Discord for the confluence alert with PDF attachment!")
        logger.info("=" * 80)
    else:
        logger.error("=" * 80)
        logger.error("❌ TEST FAILED - See logs above for details")
        logger.error("=" * 80)
    
    return success

if __name__ == "__main__":
    # Run the main function
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 