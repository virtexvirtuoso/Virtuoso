#!/usr/bin/env python3
"""
Test script for market reporter webhook functionality.
This will verify that the market report can be generated and sent via Discord webhook.
"""

import asyncio
import logging
import sys
import os
import yaml
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_market_reporter_webhook")

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import necessary modules
try:
    from src.monitoring.alert_manager import AlertManager
    from src.monitoring.market_reporter import MarketReporter
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

async def test_webhook_directly():
    """Test sending a webhook message directly via AlertManager."""
    try:
        logger.info("=== Testing Direct Webhook Send ===")
        
        # Load config
        config_path = os.path.join("src", "config", "config.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join("config", "config.yaml")
            
        if not os.path.exists(config_path):
            logger.error(f"Config file not found at {config_path}")
            return False
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize AlertManager
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config)
        
        # Check if Discord webhook is configured
        if alert_manager.discord_webhook_url:
            logger.info(f"Discord webhook URL is configured (length: {len(alert_manager.discord_webhook_url)})")
        else:
            logger.error("No Discord webhook URL configured")
            return False
            
        # Create a simple test message
        test_message = {
            "content": f"🧪 Test webhook message from market reporter test script at {datetime.now().isoformat()}",
            "embeds": [
                {
                    "title": "Test Embed",
                    "description": "This is a test embed to verify webhook functionality",
                    "color": 5814783,  # Green color
                    "fields": [
                        {
                            "name": "Test Field",
                            "value": "Test Value",
                            "inline": True
                        },
                        {
                            "name": "Time",
                            "value": datetime.now().strftime("%H:%M:%S"),
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "Test Footer"
                    }
                }
            ]
        }
        
        # Send the test message
        logger.info("Sending test webhook message")
        result, response = await alert_manager.send_discord_webhook_message(test_message)
        
        if result:
            logger.info("✅ Direct webhook test successful")
            return True
        else:
            logger.error(f"❌ Direct webhook test failed: {response}")
            return False
    
    except Exception as e:
        logger.error(f"Error in direct webhook test: {e}")
        return False

async def test_market_reporter():
    """Test generating and sending a market report via MarketReporter."""
    try:
        logger.info("=== Testing Market Reporter ===")
        
        # Load config
        config_path = os.path.join("src", "config", "config.yaml")
        if not os.path.exists(config_path):
            config_path = os.path.join("config", "config.yaml")
            
        if not os.path.exists(config_path):
            logger.error(f"Config file not found at {config_path}")
            return False
            
        logger.info(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize AlertManager
        logger.info("Initializing AlertManager")
        alert_manager = AlertManager(config)
        
        # Check if Discord webhook is configured
        if alert_manager.discord_webhook_url:
            logger.info(f"Discord webhook URL is configured (length: {len(alert_manager.discord_webhook_url)})")
        else:
            logger.error("No Discord webhook URL configured")
            return False
        
        # Initialize MarketReporter with mocked market data
        logger.info("Initializing MarketReporter")
        market_reporter = MarketReporter(exchange=None, logger=logger, alert_manager=alert_manager)
        
        # Create a simple mock report
        mock_report = {
            'market_overview': {
                'regime': 'BULLISH_STABLE',
                'trend_strength': '75.5%',
                'volatility': 2.3,
                'total_volume': 12500000,
                'btc_support': '35000',
                'btc_resistance': '37500',
                'sentiment': 'Bullish',
                'timestamp': int(time.time() * 1000)
            },
            'smart_money_index': {
                'index': 72.5,
                'sentiment': 'BULLISH',
                'signals': [],
                'timestamp': int(time.time() * 1000)
            },
            'whale_activity': {
                'whale_activity': {},
                'timestamp': int(time.time() * 1000)
            },
            'futures_premium': {
                'premiums': {
                    'BTC/USDT:USDT': {
                        'premium': '0.25%',
                        'premium_value': 0.25,
                        'mark_price': 36500,
                        'index_price': 36410
                    }
                },
                'timestamp': int(time.time() * 1000)
            }
        }
        
        # Format the report
        logger.info("Formatting market report")
        formatted_report = await market_reporter.format_market_report(
            overview=mock_report['market_overview'],
            top_pairs=['BTC/USDT:USDT', 'ETH/USDT:USDT'],
            smart_money=mock_report['smart_money_index'],
            whale_activity=mock_report['whale_activity']
        )
        
        # Check report structure
        if 'embeds' in formatted_report and isinstance(formatted_report['embeds'], list):
            logger.info(f"Report has {len(formatted_report['embeds'])} embeds")
            
            # Add test marker to content
            formatted_report['content'] = f"🧪 TEST MARKET REPORT ({datetime.now().strftime('%H:%M:%S')})\n{formatted_report.get('content', '')}"
            
            # Send the report
            logger.info("Sending formatted market report")
            result, response = await alert_manager.send_discord_webhook_message(formatted_report)
            
            if result:
                logger.info("✅ Market report test successful")
                return True
            else:
                logger.error(f"❌ Market report test failed: {response}")
                return False
        else:
            logger.error("Invalid report format - missing embeds")
            return False
    
    except Exception as e:
        logger.error(f"Error in market reporter test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all tests."""
    direct_test = await test_webhook_directly()
    reporter_test = await test_market_reporter()
    
    if direct_test and reporter_test:
        logger.info("All tests passed successfully! 🎉")
    else:
        logger.error("Some tests failed. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(main()) 