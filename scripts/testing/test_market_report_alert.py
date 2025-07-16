"""
Test script to simulate a market report alert that should go to both webhooks.
"""

import asyncio
import os
import sys
import time
import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.monitoring.alert_manager import AlertManager
except ImportError:
    logger.error("Failed to import AlertManager. Make sure you're running from the project root.")
    sys.exit(1)

async def test_market_report_alert():
    """Test the market report alert functionality."""
    logger.info("Testing market report alert...")
    
    # Load configuration
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        logger.error(f"Config file not found at {config_path}")
        return
    
    # Create a simple config for testing
    config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
                'system_alerts_webhook_url': os.getenv('SYSTEM_ALERTS_WEBHOOK_URL'),
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {'market_report': True},
                    'mirror_alerts': {
                        'enabled': True,
                        'types': {'market_report': True}
                    }
                }
            }
        }
    }
    
    # Verify webhooks are configured
    main_webhook = config['monitoring']['alerts']['discord_webhook_url']
    system_webhook = config['monitoring']['alerts']['system_alerts_webhook_url']
    
    if not main_webhook:
        logger.error("Main Discord webhook URL not configured")
        return
    
    if not system_webhook:
        logger.error("System alerts webhook URL not configured")
        return
    
    logger.info(f"Main webhook: {main_webhook[:20]}...{main_webhook[-10:]}")
    logger.info(f"System webhook: {system_webhook[:20]}...{system_webhook[-10:]}")
    
    # Initialize alert manager
    alert_manager = AlertManager(config)
    
    # Simulate market report generation
    timestamp = datetime.now(timezone.utc)
    formatted_date = timestamp.strftime("%B %d, %Y - %H:%M UTC")
    
    # Create a fake PDF filename
    pdf_filename = f"market_report_{int(time.time())}.pdf"
    
    # Prepare market report details
    details = {
        'type': 'market_report',
        'title': f'Market Intelligence Report, {formatted_date}',
        'report_type': 'market_report',
        'report_time': timestamp.isoformat(),
        'pdf_filename': pdf_filename,
        'pdf_size': '68.30 KB',
        'symbols_covered': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT'],
        'timeframe': '1d'
    }
    
    # Send the alert (this should trigger mirroring)
    await alert_manager.send_alert(
        level="info",
        message=f"Market report generated for {formatted_date}",
        details=details
    )
    
    logger.info("Market report alert sent. Check both Discord channels for the notifications.")
    
    # Allow time for webhooks to process
    await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_market_report_alert()) 