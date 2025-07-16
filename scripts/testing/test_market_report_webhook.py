"""
Simple test script to send a market report alert to the system webhook.
"""

import os
import json
import requests
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_market_report_webhook():
    """Send a test market report notification to the system webhook."""
    # Get the system webhook URL from environment
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')

    if not webhook_url:
        print("Error: SYSTEM_ALERTS_WEBHOOK_URL not found in .env file")
        return False

    print(f"Using system webhook URL: {webhook_url[:20]}...{webhook_url[-10:]}")
    
    # Get current timestamp
    timestamp = datetime.now(timezone.utc)
    formatted_date = timestamp.strftime("%B %d, %Y - %H:%M UTC")
    
    # Create webhook payload for market report
    payload = {
        'username': 'Virtuoso Market Intelligence',
        'content': '📊 **MARKET REPORT NOTIFICATION** 📊',
        'embeds': [{
            'title': 'Market Report Generated',
            'color': 0x3498db,  # Blue
            'description': f'A new market report has been generated for {formatted_date}. See main channel for the full report with attachments.',
            'fields': [
                {
                    'name': 'Timestamp',
                    'value': f'<t:{int(time.time())}:F>',
                    'inline': True
                },
                {
                    'name': 'Report Type',
                    'value': 'market_report',
                    'inline': True
                },
                {
                    'name': 'Symbols Covered',
                    'value': 'BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, XRPUSDT',
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Virtuoso Market Intelligence'
            }
        }]
    }
    
    print("Sending market report notification...")
    
    # Send webhook request
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        # Check response status
        if response.status_code >= 200 and response.status_code < 300:
            print(f"Success! Webhook delivered (Status: {response.status_code})")
            return True
        else:
            print(f"Error: Webhook failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending webhook: {str(e)}")
        return False

if __name__ == "__main__":
    test_market_report_webhook() 