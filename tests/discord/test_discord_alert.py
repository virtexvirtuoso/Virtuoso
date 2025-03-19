#!/usr/bin/env python3
"""
Test Discord Alert Functionality with Confluence Scores

This script tests the AlertManager's ability to send Discord alerts when
a confluence score meets the buy or sell threshold.
"""

import asyncio
import logging
import os
import yaml
import time
from typing import Dict, Any
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Import local modules
from src.monitoring.alert_manager import AlertManager
from src.signal_generation.signal_generator import SignalGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def load_config() -> Dict[str, Any]:
    """Load configuration from YAML files."""
    try:
        with open('config/alert_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        # Fall back to default config if file not found
        return {
            "monitoring": {
                "alerts": {
                    "max_alerts_per_minute": 10,
                    "history_size": 1000,
                    "throttle_interval": 60,
                    "min_interval": 5,
                    "discord": {
                        "enabled": True,
                        "webhook_url": os.getenv("DISCORD_WEBHOOK_URL", "")
                    }
                }
            },
            "analysis": {
                "confluence_thresholds": {
                    "buy": 60,
                    "sell": 40
                }
            },
            # Add required configuration for SignalGenerator and TechnicalIndicators
            "timeframes": {
                "1m": {"interval": 60, "periods": 30},
                "5m": {"interval": 300, "periods": 30},
                "15m": {"interval": 900, "periods": 30},
                "1h": {"interval": 3600, "periods": 24},
                "4h": {"interval": 14400, "periods": 24},
                "1d": {"interval": 86400, "periods": 30}
            },
            "indicators": {
                "technical": {
                    "rsi": {"period": 14, "overbought": 70, "oversold": 30},
                    "macd": {"fast_period": 12, "slow_period": 26, "signal_period": 9}
                },
                "volume": {
                    "vwap": {"period": 14}
                },
                "orderflow": {
                    "imbalance_threshold": 1.5
                },
                "orderbook": {
                    "depth": 10
                }
            },
            "signal": {
                "weights": {
                    "volume": 0.2,
                    "technical": 0.2,
                    "orderflow": 0.2,
                    "orderbook": 0.15,
                    "sentiment": 0.1,
                    "price_structure": 0.15
                }
            }
        }

async def test_bullish_alert():
    """Test sending a bullish alert when confluence score is high."""
    config = await load_config()
    
    # Verify Discord webhook URL is set
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        logger.info("Please set it in your .env file or environment variables")
        return
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    
    # Initialize the discord webhook
    alert_manager._init_discord_webhook()
    
    # Check if Discord is properly configured
    if not alert_manager._has_discord_config():
        logger.error("Discord webhook is not properly configured!")
        return
    
    # Skip SignalGenerator and directly send a confluence alert for a bullish scenario
    symbol = "BTC/USDT"
    confluence_score = 75.0  # High score (above buy threshold)
    
    components = {
        'volume': 80.0,
        'technical': 70.0,
        'orderflow': 65.0,
        'orderbook': 75.0,
        'sentiment': 80.0,
        'price_structure': 75.0
    }
    
    results = {
        'volume': {
            'score': 80.0,
            'components': {'volume_change': 2.3, 'relative_volume': 1.5},
            'interpretation': 'Strong buying volume detected'
        },
        'technical': {
            'score': 70.0,
            'components': {'rsi': 62, 'macd': 'bullish'},
            'interpretation': 'Bullish momentum indicators'
        },
        'orderflow': {
            'score': 65.0,
            'components': {'buy_pressure': 1.2},
            'interpretation': 'Moderate buying pressure'
        },
        'orderbook': {
            'score': 75.0,
            'components': {'bid_ask_ratio': 1.3},
            'interpretation': 'More bids than asks, bullish bias'
        },
        'sentiment': {
            'score': 80.0,
            'components': {'social_sentiment': 0.75},
            'interpretation': 'Very positive market sentiment'
        },
        'price_structure': {
            'score': 75.0,
            'components': {'support_strength': 0.85},
            'interpretation': 'Price holding above key support'
        }
    }
    
    # Send confluence alert directly
    logger.info(f"Sending bullish confluence alert for {symbol} with score {confluence_score}")
    
    # This should trigger the Discord alert
    await alert_manager.send_confluence_alert(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        reliability=0.85
    )
    
    logger.info("Bullish confluence alert sent. Please check your Discord channel.")
    
    # Allow some time for async operations to complete
    await asyncio.sleep(2)

async def test_bearish_alert():
    """Test sending a bearish alert when confluence score is low."""
    config = await load_config()
    
    # Verify Discord webhook URL is set
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        return
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    
    # Initialize the discord webhook
    alert_manager._init_discord_webhook()
    
    # Check if Discord is properly configured
    if not alert_manager._has_discord_config():
        logger.error("Discord webhook is not properly configured!")
        return
    
    # Skip SignalGenerator and directly send a confluence alert for a bearish scenario
    symbol = "BTC/USDT"
    confluence_score = 25.0  # Low score (below sell threshold)
    
    components = {
        'volume': 30.0,
        'technical': 20.0,
        'orderflow': 35.0,
        'orderbook': 25.0,
        'sentiment': 20.0,
        'price_structure': 30.0
    }
    
    results = {
        'volume': {
            'score': 30.0,
            'components': {'volume_change': -1.8, 'relative_volume': 1.2},
            'interpretation': 'Increasing selling volume detected'
        },
        'technical': {
            'score': 20.0,
            'components': {'rsi': 30, 'macd': 'bearish'},
            'interpretation': 'Strong bearish momentum indicators'
        },
        'orderflow': {
            'score': 35.0,
            'components': {'buy_pressure': 0.7},
            'interpretation': 'Increased selling pressure'
        },
        'orderbook': {
            'score': 25.0,
            'components': {'bid_ask_ratio': 0.75},
            'interpretation': 'More asks than bids, bearish bias'
        },
        'sentiment': {
            'score': 20.0,
            'components': {'social_sentiment': -0.6},
            'interpretation': 'Negative market sentiment'
        },
        'price_structure': {
            'score': 30.0,
            'components': {'resistance_strength': 0.8},
            'interpretation': 'Price struggling below resistance'
        }
    }
    
    # Send confluence alert directly
    logger.info(f"Sending bearish confluence alert for {symbol} with score {confluence_score}")
    
    # This should trigger the Discord alert
    await alert_manager.send_confluence_alert(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        reliability=0.80
    )
    
    logger.info("Bearish confluence alert sent. Please check your Discord channel.")
    
    # Allow some time for async operations to complete
    await asyncio.sleep(2)

async def test_direct_confluence_alert():
    """Test sending a confluence alert directly through the AlertManager."""
    config = await load_config()
    
    # Verify Discord webhook URL is set
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
        return
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    
    # Initialize the discord webhook
    alert_manager._init_discord_webhook()
    
    # Check if Discord is properly configured
    if not alert_manager._has_discord_config():
        logger.error("Discord webhook is not properly configured!")
        return
    
    # Create test data
    symbol = "ETH/USDT"
    confluence_score = 80.0
    
    components = {
        'volume': 85.0,
        'technical': 75.0,
        'orderflow': 80.0,
        'orderbook': 70.0,
        'sentiment': 85.0,
        'price_structure': 80.0
    }
    
    results = {
        'volume': {
            'score': 85.0,
            'components': {'volume_change': 2.5, 'relative_volume': 1.8},
            'interpretation': 'Strong buying volume detected'
        },
        'technical': {
            'score': 75.0,
            'components': {'rsi': 65, 'macd': 'bullish'},
            'interpretation': 'Bullish momentum indicators'
        },
        'orderflow': {
            'score': 80.0,
            'components': {'buy_pressure': 1.4},
            'interpretation': 'Strong buying pressure'
        },
        'orderbook': {
            'score': 70.0,
            'components': {'bid_ask_ratio': 1.2},
            'interpretation': 'More bids than asks, bullish bias'
        },
        'sentiment': {
            'score': 85.0,
            'components': {'social_sentiment': 0.8},
            'interpretation': 'Very positive market sentiment'
        },
        'price_structure': {
            'score': 80.0,
            'components': {'support_strength': 0.9},
            'interpretation': 'Price holding above key support'
        }
    }
    
    # Send confluence alert directly
    logger.info(f"Sending direct confluence alert for {symbol} with score {confluence_score}")
    
    # This should trigger the Discord alert
    await alert_manager.send_confluence_alert(
        symbol=symbol,
        confluence_score=confluence_score,
        components=components,
        results=results,
        reliability=0.9
    )
    
    logger.info("Direct confluence alert sent. Please check your Discord channel.")
    
    # Allow some time for async operations to complete
    await asyncio.sleep(2)

async def main():
    """Run all tests."""
    try:
        # Check if the webhook URL is set
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            logger.error("DISCORD_WEBHOOK_URL environment variable is not set!")
            logger.info("Please set it in your .env file or environment variables")
            logger.info("Example: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url")
            return
            
        logger.info(f"Using Discord webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
            
        # Test bullish alert via direct AlertManager call
        logger.info("\n=== Testing Bullish Alert ===")
        await test_bullish_alert()
        
        # Short pause between tests
        await asyncio.sleep(2)
        
        # Test bearish alert via direct AlertManager call
        logger.info("\n=== Testing Bearish Alert ===")
        await test_bearish_alert()
        
        # Short pause between tests
        await asyncio.sleep(2)
        
        # Test direct confluence alert via AlertManager
        logger.info("\n=== Testing Direct Confluence Alert ===")
        await test_direct_confluence_alert()
        
        logger.info("\n=== All tests completed ===")
        logger.info("Please check your Discord channel for the test alerts.")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main()) 