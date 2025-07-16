"""
Final webhook test script to simulate the AlertManager's behavior with market reports.
"""

import os
import sys
import json
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

def send_to_system_webhook(message, details=None):
    """Send an alert to the system webhook."""
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    if not system_webhook_url:
        logger.error("Cannot send system alert: webhook URL not set")
        return False
    
    # Determine alert type and format accordingly
    alert_type = details.get('type', 'general') if details else 'general'
    
    # For market reports, customize the message
    if alert_type == 'market_report':
        # Get formatted timestamp
        timestamp = details.get('report_time', None)
        if timestamp and isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_date = dt.strftime("%B %d, %Y - %H:%M UTC")
            except (ValueError, TypeError):
                formatted_date = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        else:
            formatted_date = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
        
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
                        'value': details.get('report_type', 'market_report'),
                        'inline': True
                    }
                ],
                'footer': {
                    'text': 'Virtuoso Market Intelligence'
                }
            }]
        }
        
        # Add symbols covered if available
        symbols_covered = details.get('symbols_covered', None)
        if symbols_covered and isinstance(symbols_covered, list) and len(symbols_covered) > 0:
            symbols_str = ', '.join(symbols_covered[:5])
            if len(symbols_covered) > 5:
                symbols_str += f' and {len(symbols_covered) - 5} more'
            
            payload['embeds'][0]['fields'].append({
                'name': 'Symbols Covered',
                'value': symbols_str,
                'inline': True
            })
    else:
        # Default alert format
        payload = {
            'username': 'Virtuoso System Monitor',
            'content': '⚠️ **SYSTEM ALERT** ⚠️',
            'embeds': [{
                'title': 'System Alert',
                'color': 0x3498db,  # Blue
                'description': message,
                'fields': [
                    {
                        'name': 'Timestamp',
                        'value': f'<t:{int(time.time())}:F>',
                        'inline': True
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

def send_to_main_webhook(message, details=None):
    """Send an alert to the main webhook."""
    main_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not main_webhook_url:
        logger.error("Cannot send main alert: webhook URL not set")
        return False
    
    # Create webhook payload
    payload = {
        'username': 'Virtuoso Alerts',
        'content': '📊 **MARKET REPORT** 📊',
        'embeds': [{
            'title': 'Market Report Alert',
            'color': 0x00ff00,  # Green
            'description': message,
            'fields': [
                {
                    'name': 'Timestamp',
                    'value': f'<t:{int(time.time())}:F>',
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Virtuoso Alerts'
            }
        }]
    }
    
    # Send webhook request
    try:
        response = requests.post(
            main_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code >= 400:
            logger.error(f"Error sending main webhook: status {response.status_code}")
            return False
        else:
            logger.info(f"Main webhook sent successfully: {response.status_code}")
            return True
    except Exception as e:
        logger.error(f"Error sending main webhook request: {str(e)}")
        return False

def test_system_only_routing():
    """Test routing market report only to system webhook."""
    logger.info("Testing market report routing to system webhook only")
    
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
    
    # Send to system webhook only
    logger.info("Sending market report alert to system webhook only")
    result = send_to_system_webhook(f"Market report generated at {formatted_time}", details)
    
    if result:
        logger.info("✅ Successfully sent to system webhook - check system channel")
    else:
        logger.error("❌ Failed to send to system webhook")
    
    # Simulate the behavior of our fix - NOT sending to main webhook
    logger.info("Message should NOT appear in main webhook channel")
    
    return result

def test_mirrored_routing():
    """Test routing market report to both webhooks."""
    logger.info("Testing market report routing to both webhooks (mirrored)")
    
    # Create market report details
    report_time = datetime.now(timezone.utc)
    formatted_time = report_time.strftime("%Y-%m-%d %H:%M:%S")
    details = {
        'type': 'market_report',
        'report_time': report_time.isoformat(),
        'report_type': 'market_report',
        'symbols_covered': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT'],
        'timeframe': '1d'
    }
    
    # Send to system webhook
    logger.info("Sending market report alert to system webhook")
    system_result = send_to_system_webhook(f"Market report generated at {formatted_time} (mirrored)", details)
    
    if system_result:
        logger.info("✅ Successfully sent to system webhook - check system channel")
    else:
        logger.error("❌ Failed to send to system webhook")
    
    # Also send to main webhook
    logger.info("Sending market report alert to main webhook")
    main_result = send_to_main_webhook(f"Market report generated at {formatted_time} (mirrored)", details)
    
    if main_result:
        logger.info("✅ Successfully sent to main webhook - check main channel")
    else:
        logger.error("❌ Failed to send to main webhook")
    
    return system_result and main_result

if __name__ == "__main__":
    # Verify webhooks are set
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    main_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not system_webhook_url:
        logger.error("SYSTEM_ALERTS_WEBHOOK_URL not set in environment variables")
        sys.exit(1)
    
    if not main_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL not set in environment variables")
        sys.exit(1)
    
    logger.info(f"System webhook URL: {system_webhook_url[:20]}...{system_webhook_url[-10:]}")
    logger.info(f"Main webhook URL: {main_webhook_url[:20]}...{main_webhook_url[-10:]}")
    
    # Run the tests
    logger.info("=== RUNNING TEST 1: SYSTEM WEBHOOK ONLY ===")
    system_only_result = test_system_only_routing()
    
    # Give some time between tests
    time.sleep(2)
    
    logger.info("=== RUNNING TEST 2: MIRRORED TO BOTH WEBHOOKS ===")
    mirrored_result = test_mirrored_routing()
    
    # Print final summary
    logger.info("=== TEST SUMMARY ===")
    if system_only_result:
        logger.info("✅ Test 1 (System Only): PASSED")
    else:
        logger.error("❌ Test 1 (System Only): FAILED")
    
    if mirrored_result:
        logger.info("✅ Test 2 (Mirrored): PASSED")
    else:
        logger.error("❌ Test 2 (Mirrored): FAILED")
    
    logger.info("Test complete - Please check Discord channels to verify messages appeared in the expected channels") 