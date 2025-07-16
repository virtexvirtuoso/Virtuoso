"""
Test script to verify the routing of CPU alerts to the system webhook.
"""

import os
import time
import requests
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def send_to_system_webhook(message, alert_type="cpu", cpu_value=95.5, threshold=90.0):
    """Send a CPU alert to the system webhook."""
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    if not system_webhook_url:
        logger.error("Cannot send system alert: webhook URL not set")
        return False
    
    # Create CPU alert payload
    payload = {
        'username': 'Virtuoso System Monitor',
        'content': '⚠️ **SYSTEM ALERT** ⚠️',
        'embeds': [{
            'title': 'WARNING Alert',
            'color': 0xf39c12,  # Orange
            'description': message,
            'fields': [
                {
                    'name': 'value',
                    'value': f"{cpu_value}",
                    'inline': True
                },
                {
                    'name': 'threshold',
                    'value': f"{threshold}",
                    'inline': True
                },
                {
                    'name': 'Timestamp',
                    'value': f"<t:{int(time.time())}:F>",
                    'inline': False
                }
            ],
            'footer': {
                'text': 'Virtuoso System Monitoring'
            }
        }]
    }
    
    # Send webhook request
    try:
        response = requests.post(
            system_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code >= 400:
            logger.error(f"Error sending system webhook: status {response.status_code}")
            return False
        else:
            logger.info(f"System webhook sent successfully: {response.status_code}")
            return True
    except Exception as e:
        logger.error(f"Error sending system webhook request: {str(e)}")
        return False

def test_cpu_alert_routing():
    """Test that CPU alerts are routed correctly to the system webhook."""
    logger.info("Testing CPU alert routing to system webhook")
    
    # Verify webhooks are set
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    main_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not system_webhook_url:
        logger.error("SYSTEM_ALERTS_WEBHOOK_URL not set in environment variables")
        return False
    
    if not main_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL not set in environment variables")
        return False
    
    logger.info(f"System webhook URL: {system_webhook_url[:20]}...{system_webhook_url[-10:]}")
    logger.info(f"Main webhook URL: {main_webhook_url[:20]}...{main_webhook_url[-10:]}")
    
    # Send CPU alert to system webhook
    logger.info("Sending CPU alert to system webhook")
    cpu_value = 97.5
    threshold = 90.0
    result = send_to_system_webhook(
        message=f"High cpu_usage",
        cpu_value=cpu_value,
        threshold=threshold
    )
    
    if result:
        logger.info("✅ Successfully sent CPU alert to system webhook")
        logger.info("Please check the system alerts channel to verify the CPU alert was received")
        logger.info("Also verify that the alert does NOT appear in the main alerts channel")
    else:
        logger.error("❌ Failed to send CPU alert to system webhook")
    
    return result

if __name__ == "__main__":
    test_cpu_alert_routing() 