"""
Test script to verify that the AlertManager properly routes CPU alerts to the system webhook.
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
sys.path.insert(0, os.getcwd())

# Try different import paths
try:
    from src.monitoring.alert_manager import AlertManager
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.monitoring.alert_manager import AlertManager
    except ImportError:
        try:
            sys.path.insert(0, str(Path(__file__).parent.absolute()))
            from src.monitoring.alert_manager import AlertManager
        except ImportError:
            try:
                # One more attempt with a direct import
                from monitoring.alert_manager import AlertManager
            except ImportError:
                logger.error("Failed to import AlertManager. Make sure you're running from the project root.")
                sys.exit(1)

async def test_cpu_alert_with_alert_manager():
    """Test the routing of CPU alerts using the AlertManager directly."""
    logger.info("Testing CPU alert routing with AlertManager")
    
    # Create a configuration that routes CPU alerts to the system webhook
    config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL'),
                'system_alerts_webhook_url': os.getenv('SYSTEM_ALERTS_WEBHOOK_URL'),
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {
                        'cpu': True,
                        'market_report': True
                    },
                    'mirror_alerts': {
                        'enabled': False
                    }
                },
                'cpu_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'threshold': 90.0,
                    'cooldown': 600
                }
            }
        }
    }
    
    # Initialize AlertManager with the configuration
    alert_manager = AlertManager(config)
    
    # Create CPU alert details
    cpu_value = 97.5
    threshold = 90.0
    details = {
        'type': 'cpu',
        'value': cpu_value,
        'threshold': threshold,
        'host': 'test-server'
    }
    
    # Send the CPU alert - should go ONLY to system webhook
    logger.info(f"Sending CPU alert (value: {cpu_value}, threshold: {threshold})")
    try:
        await alert_manager.send_alert(
            level="WARNING",
            message=f"High cpu_usage",
            details=details
        )
        logger.info("CPU alert sent successfully")
    except Exception as e:
        logger.error(f"Error sending CPU alert: {str(e)}")
    
    # Allow time for webhook to process
    await asyncio.sleep(2)
    
    # Now test with mirroring enabled - should go to BOTH webhooks
    logger.info("Testing CPU alert with mirroring enabled")
    
    # Update config to enable mirroring
    config['monitoring']['alerts']['system_alerts']['mirror_alerts']['enabled'] = True
    config['monitoring']['alerts']['system_alerts']['mirror_alerts']['types'] = {'cpu': True}
    
    # Create new AlertManager with updated config
    mirror_alert_manager = AlertManager(config)
    
    # Send test alert - should go to BOTH webhooks
    logger.info("Sending CPU alert with mirroring enabled")
    try:
        await mirror_alert_manager.send_alert(
            level="WARNING",
            message=f"High cpu_usage (mirrored)",
            details=details
        )
        logger.info("Mirrored CPU alert sent successfully")
    except Exception as e:
        logger.error(f"Error sending mirrored CPU alert: {str(e)}")
    
    # Allow time for webhook to process
    await asyncio.sleep(2)
    
    logger.info("Tests completed - Check both Discord channels to verify routing")

if __name__ == "__main__":
    asyncio.run(test_cpu_alert_with_alert_manager()) 