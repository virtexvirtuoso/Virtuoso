#!/usr/bin/env python3
"""Test script to verify market report webhook routing to system webhook."""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from monitoring.alert_manager import AlertManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_market_report_routing():
    """Test that market report alerts are routed to the correct webhook."""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    if not discord_webhook_url:
        logger.error("DISCORD_WEBHOOK_URL not found in environment variables")
        return False
    
    if not system_webhook_url:
        logger.error("SYSTEM_ALERTS_WEBHOOK_URL not found in environment variables")
        return False
        
    logger.info(f"Discord webhook: {discord_webhook_url[:50]}...")
    logger.info(f"System webhook: {system_webhook_url[:50]}...")
    
    # Create test configuration with system webhook routing enabled
    config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': discord_webhook_url,
                'system_alerts_webhook_url': system_webhook_url,
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,  # Enable system webhook routing
                    'types': {
                        'market_report': True,  # Route market reports to system webhook
                        'cpu': True,
                        'memory': True
                    },
                    'cooldown': {
                        'market_report': 60
                    },
                    'mirror_alerts': {
                        'enabled': False,  # Disable mirroring for this test
                        'types': {
                            'market_report': False
                        }
                    }
                }
            }
        }
    }
    
    # Initialize AlertManager with test config
    alert_manager = AlertManager(config)
    
    logger.info("Testing market report webhook routing...")
    
    # Test 1: Simple alert call (should go to system webhook)
    logger.info("\n=== Test 1: Simple market report alert ===")
    await alert_manager.send_alert(
        level="info",
        message="Test market report generated",
        details={"type": "market_report", "report_type": "test_report"}
    )
    
    # Test 2: Rich Discord message with alert_type (should go to system webhook)
    logger.info("\n=== Test 2: Rich Discord message with market_report alert_type ===")
    rich_message = {
        'content': '📊 **TEST MARKET REPORT** 📊',
        'username': 'Virtuoso Market Intelligence',
        'embeds': [{
            'title': 'Test Market Report',
            'color': 5763719,  # Green
            'description': 'This is a test market report to verify webhook routing.',
            'fields': [
                {
                    'name': 'Test Field',
                    'value': 'This should go to system webhook',
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Virtuoso Test Market Intelligence'
            }
        }]
    }
    
    await alert_manager.send_discord_webhook_message(
        rich_message, 
        alert_type='market_report'  # This should route to system webhook
    )
    
    # Test 3: Rich Discord message without alert_type (should go to main webhook)
    logger.info("\n=== Test 3: Rich Discord message without alert_type (should go to main webhook) ===")
    regular_message = {
        'content': '🔔 **REGULAR ALERT** 🔔',
        'username': 'Virtuoso Regular Alert',
        'embeds': [{
            'title': 'Regular Alert',
            'color': 15158332,  # Red
            'description': 'This is a regular alert that should go to main webhook.',
            'fields': [
                {
                    'name': 'Alert Type',
                    'value': 'Regular (no alert_type specified)',
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Virtuoso Regular Alerts'
            }
        }]
    }
    
    await alert_manager.send_discord_webhook_message(regular_message)  # No alert_type specified
    
    logger.info("\n=== Test completed ===")
    logger.info("Check your Discord channels:")
    logger.info("- System alerts channel should have received Test 1 and Test 2")
    logger.info("- Main alerts channel should have received Test 3")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_market_report_routing())
        if success:
            logger.info("✅ Test completed successfully")
        else:
            logger.error("❌ Test failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        sys.exit(1) 