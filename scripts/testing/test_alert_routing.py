"""
Test script to verify the AlertManager's routing of market report alerts.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Try multiple import paths for AlertManager
try:
    from src.monitoring.alert_manager import AlertManager
except ImportError:
    try:
        # Try absolute import
        sys.path.insert(0, str(Path(__file__).parent.absolute()))
        from src.monitoring.alert_manager import AlertManager
    except ImportError:
        try:
            # Try relative import
            from .src.monitoring.alert_manager import AlertManager
        except ImportError:
            try:
                # Try with different path structure
                import os
                sys.path.insert(0, os.getcwd())
                from src.monitoring.alert_manager import AlertManager
            except ImportError:
                logger.error("Failed to import AlertManager. Make sure you're running from the project root.")
                sys.exit(1)

async def test_market_report_routing():
    """Test the routing of market report alerts to system webhook."""
    logger.info("Testing market report alert routing...")
    
    # Create a test configuration
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
                        'enabled': False,  # Disable mirroring to test system-only routing
                        'types': {'market_report': False}
                    }
                }
            }
        }
    }
    
    # Initialize AlertManager with test config
    alert_manager = AlertManager(config)
    
    # Create market report details
    details = {
        'type': 'market_report',
        'report_time': '2025-06-03T09:45:00+00:00',
        'report_type': 'market_report',
        'symbols_covered': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        'timeframe': '1d'
    }
    
    # Send test alert - This should go ONLY to the system webhook
    logger.info("Sending market report alert (system webhook only)...")
    await alert_manager.send_alert(
        level="info",
        message="Market report generated for system webhook test",
        details=details
    )
    
    # Allow time for webhook to process
    logger.info("Waiting for webhook processing...")
    await asyncio.sleep(2)
    
    # Now test with mirroring enabled
    logger.info("Testing market report mirroring to both webhooks...")
    
    # Update config to enable mirroring
    config['monitoring']['alerts']['system_alerts']['mirror_alerts']['enabled'] = True
    config['monitoring']['alerts']['system_alerts']['mirror_alerts']['types']['market_report'] = True
    
    # Create new AlertManager with updated config
    mirror_alert_manager = AlertManager(config)
    
    # Update details for mirrored test
    details['report_time'] = '2025-06-03T09:50:00+00:00'
    
    # Send test alert - This should go to BOTH webhooks
    logger.info("Sending market report alert (mirrored to both webhooks)...")
    await mirror_alert_manager.send_alert(
        level="info",
        message="Market report generated for mirrored webhook test",
        details=details
    )
    
    # Allow time for webhook to process
    logger.info("Waiting for webhook processing...")
    await asyncio.sleep(2)
    
    logger.info("Tests completed - Check both Discord channels to verify routing")

if __name__ == "__main__":
    asyncio.run(test_market_report_routing()) 