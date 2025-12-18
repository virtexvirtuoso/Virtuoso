import os
import sys
import logging
import yaml
import asyncio
import json
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import AlertManager
from src.monitoring.alert_manager import AlertManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("discord_handler_test")

async def test_discord_handler():
    """Test the discord handler configuration and alert sending"""
    # Check for discord webhook in environment
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    logger.info(f"Discord webhook URL exists in environment: {bool(discord_webhook_url)}")
    if discord_webhook_url:
        logger.info(f"Discord webhook URL begins with: {discord_webhook_url[:20]}...")
    
    # Load config
    config_path = 'config/config.yaml'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
    else:
        config = {}
        logger.warning(f"No config found at {config_path}, using empty config")
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    logger.info(f"Initial handlers: {alert_manager.get_handlers()}")
    
    # Register the Discord handler directly
    alert_manager.register_discord_handler()
    logger.info(f"Handlers after registration: {alert_manager.get_handlers()}")
    
    # Set webhook URL from environment if it exists
    if discord_webhook_url and not alert_manager.discord_webhook_url:
        alert_manager.discord_webhook_url = discord_webhook_url
        logger.info("Set discord_webhook_url from environment variable")
    
    # Check if Discord is properly configured now
    has_discord_config = hasattr(alert_manager, '_has_discord_config') and alert_manager._has_discord_config()
    logger.info(f"Has Discord config: {has_discord_config}")
    logger.info(f"Discord webhook URL is set: {bool(alert_manager.discord_webhook_url)}")
    
    # Try to send a test alert
    if alert_manager.discord_webhook_url:
        # Create a test embed
        test_embed = {
            "title": "🔵 TEST ALERT",
            "description": "This is a test alert to verify Discord notifications are working",
            "color": 3447003,  # Blue
            "fields": [
                {
                    "name": "Test Field",
                    "value": "Test Value",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Discord Handler Test"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create webhook message
        webhook_message = {
            "embeds": [test_embed]
        }
        
        logger.info(f"Sending test webhook message: {json.dumps(webhook_message, indent=2)}")
        
        # Send the message
        try:
            await alert_manager.send_discord_webhook_message(webhook_message)
            logger.info("Test webhook message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send test webhook message: {str(e)}")
    else:
        logger.error("Cannot send test alert: Discord webhook URL not set")
    
    # Try to send a signal alert
    signal = {
        'symbol': 'BTCUSDT',
        'signal': 'BUY',
        'confluence_score': 75.0,
        'price': 60000.0,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'components': {
            'technical': 70.0,
            'volume': 80.0,
            'orderbook': 75.0,
            'orderflow': 80.0,
            'sentiment': 70.0,
            'price_structure': 75.0
        }
    }
    
    logger.info(f"Sending test signal alert for {signal['symbol']}")
    success = await alert_manager.send_signal_alert(signal)
    logger.info(f"Signal alert sending result: {success}")
    
    # Print final status
    logger.info(f"Final handlers: {alert_manager.get_handlers()}")
    logger.info(f"Discord webhook URL: {bool(alert_manager.discord_webhook_url)}")

async def main():
    await test_discord_handler()

if __name__ == "__main__":
    asyncio.run(main()) 