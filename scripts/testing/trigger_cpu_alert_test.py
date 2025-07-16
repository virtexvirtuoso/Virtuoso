"""
Test script to send a CPU usage alert directly to the system webhook.
This simulates the exact format shown in the screenshot.
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

def send_cpu_alert():
    """Send a CPU usage alert in the exact format from the screenshot."""
    # Get webhook URLs
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    if not system_webhook_url:
        logger.error("SYSTEM_ALERTS_WEBHOOK_URL not found in environment variables")
        return False
    
    logger.info(f"Using system webhook URL: {system_webhook_url[:20]}...{system_webhook_url[-10:]}")
    
    # Create payload exactly like the screenshot
    payload = {
        'username': 'Virtuoso Signals',
        'avatar_url': 'https://i.imgur.com/4M34hi2.png',  # Optional: Set avatar
        'embeds': [{
            'title': 'WARNING Alert',
            'description': 'High cpu_usage',
            'color': 0xf39c12,  # Orange
            'fields': [
                {
                    'name': 'value',
                    'value': '97.5',
                    'inline': True
                },
                {
                    'name': 'threshold',
                    'value': '90.0',
                    'inline': True
                }
            ],
            'footer': {
                'text': f'Today at {datetime.now().strftime("%I:%M %p")}'
            }
        }]
    }
    
    # Send the webhook
    logger.info("Sending CPU alert to system webhook...")
    try:
        response = requests.post(
            system_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"✅ Successfully sent CPU alert to system webhook (Status: {response.status_code})")
            return True
        else:
            logger.error(f"❌ Failed to send CPU alert: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending CPU alert: {str(e)}")
        return False

if __name__ == "__main__":
    # Send the CPU alert
    send_cpu_alert()
    
    # Remind the user to check the channels
    print("\n✅ Test completed!")
    print("Please verify:")
    print("1. The CPU alert appears in the SYSTEM alerts channel")
    print("2. No duplicate alert appears in the MAIN alerts channel") 