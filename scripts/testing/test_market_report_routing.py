"""
Test script to verify the AlertManager's routing of market report alerts.
This simplified version uses direct imports of the AlertManager class.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import the AlertManager directly
sys.path.insert(0, os.getcwd())
from src.monitoring.alert_manager import AlertManager

async def test_market_report_routing():
    """Test the routing of market report alerts."""
    logger.info("Testing market report alert routing")
    
    # Create a configuration for routing market reports to the system webhook only
    system_only_config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
                'system_alerts_webhook_url': os.getenv('SYSTEM_ALERTS_WEBHOOK_URL'),
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {'market_report': True},
                    'mirror_alerts': {
                        'enabled': False  # Don't mirror, send ONLY to system webhook
                    }
                }
            }
        }
    }
    
    # Create an AlertManager with this configuration
    logger.info("Creating AlertManager for system-only routing")
    system_alert_manager = AlertManager(system_only_config)
    
    # Create market report details
    report_time = datetime.now(timezone.utc)
    formatted_time = report_time.strftime("%Y-%m-%d %H:%M:%S")
    details = {
        'type': 'market_report',
        'report_time': report_time.isoformat(),
        'report_type': 'market_report',
        'symbols_covered': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        'timeframe': '1d'
    }
    
    # Send the test alert - should go ONLY to system webhook
    logger.info("Sending market report alert (system webhook only)")
    try:
        await system_alert_manager.send_alert(
            level="info",
            message=f"Market report generated at {formatted_time}",
            details=details
        )
        logger.info("Alert sent successfully, check system webhook channel")
    except Exception as e:
        logger.error(f"Error sending alert: {str(e)}")
    
    # Allow time for webhook to process
    await asyncio.sleep(2)
    
    # Now test with mirroring enabled - alert should go to BOTH webhooks
    logger.info("Testing market report mirroring to both webhooks")
    
    # Create a configuration for mirroring market reports to both webhooks
    mirror_config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
                'system_alerts_webhook_url': os.getenv('SYSTEM_ALERTS_WEBHOOK_URL'),
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {'market_report': True},
                    'mirror_alerts': {
                        'enabled': True,  # Mirror to both webhooks
                        'types': {'market_report': True}
                    }
                }
            }
        }
    }
    
    # Create a new AlertManager with mirroring enabled
    logger.info("Creating AlertManager for mirrored routing")
    mirror_alert_manager = AlertManager(mirror_config)
    
    # Update report time for mirrored test
    report_time = datetime.now(timezone.utc)
    formatted_time = report_time.strftime("%Y-%m-%d %H:%M:%S")
    details['report_time'] = report_time.isoformat()
    
    # Send the test alert - should go to BOTH webhooks
    logger.info("Sending market report alert (mirrored to both webhooks)")
    try:
        await mirror_alert_manager.send_alert(
            level="info",
            message=f"Market report generated at {formatted_time} (mirrored)",
            details=details
        )
        logger.info("Alert sent successfully, check both webhook channels")
    except Exception as e:
        logger.error(f"Error sending mirrored alert: {str(e)}")
    
    # Allow time for webhook to process
    await asyncio.sleep(2)
    
    # Test completion
    logger.info("All tests completed. Please check Discord channels to verify routing.")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_market_report_routing()) 