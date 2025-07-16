#!/usr/bin/env python3
"""Test script to verify that trading alerts go to the main Discord webhook."""

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

async def test_trading_webhook_alerts():
    """Test that trading alerts go to the main Discord webhook."""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check webhook URLs
    discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    system_webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    logger.info(f"Discord webhook: {discord_webhook_url[:50]}...")
    logger.info(f"System webhook: {system_webhook_url[:50]}...")
    
    if not discord_webhook_url or not system_webhook_url:
        logger.error("Missing webhook URLs in environment variables")
        return
    
    # Import config - minimal config with actual webhook URLs
    config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': discord_webhook_url,
                'system_alerts_webhook_url': system_webhook_url,
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {
                        # Trading alerts should NOT be in this list
                        'cpu': True,
                        'memory': True,
                        'market_report': True,
                        # large_aggressive_order and whale_activity are NOT here
                    },
                    'mirror_alerts': {
                        'enabled': False,  # Disable mirroring for this test
                        'types': {}
                    }
                }
            }
        }
    }
    
    # Initialize alert manager
    alert_manager = AlertManager(config)
    
    logger.info("Testing trading alerts that should go to MAIN Discord webhook...")
    
    # Test cases for trading alerts that should go to main Discord webhook
    test_cases = [
        {
            'name': 'Large Order Alert',
            'level': 'WARNING',
            'message': '💥 Large aggressive order detected',
            'details': {
                'type': 'large_aggressive_order',
                'symbol': 'BTCUSDT',
                'data': {
                    'side': 'BUY',
                    'size': 15.5,
                    'price': 42500.0,
                    'usd_value': 658750.0
                }
            },
            'expected_webhook': 'MAIN'
        },
        {
            'name': 'Whale Activity Alert',
            'level': 'INFO',
            'message': '🐋 Whale accumulation detected',
            'details': {
                'type': 'whale_activity',
                'symbol': 'BTCUSDT',
                'subtype': 'accumulation',
                'data': {
                    'net_whale_volume': 25.8,
                    'net_usd_value': 1097000.0,
                    'whale_bid_orders': 12,
                    'whale_ask_orders': 3,
                    'imbalance': 0.75
                }
            },
            'expected_webhook': 'MAIN'
        },
        {
            'name': 'CPU Alert (for comparison)',
            'level': 'WARNING',
            'message': '🚨 CPU usage has reached 95.5%',
            'details': {'type': 'cpu', 'cpu_usage': 95.5, 'threshold': 90},
            'expected_webhook': 'SYSTEM'
        }
    ]
    
    logger.info(f"Testing {len(test_cases)} different alert types...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n=== Test {i}: {test_case['name']} ===")
        logger.info(f"Expected to go to: {test_case['expected_webhook']} webhook")
        
        try:
            await alert_manager.send_alert(
                level=test_case['level'],
                message=test_case['message'],
                details=test_case['details']
            )
            logger.info(f"✅ {test_case['name']} sent successfully")
            
            # Small delay between alerts
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ Failed to send {test_case['name']}: {str(e)}")
    
    logger.info("\n=== Test Summary ===")
    logger.info("Trading webhook alert routing test completed.")
    logger.info("Please check your Discord channels:")
    logger.info("- MAIN Discord channel should have received:")
    logger.info("  * Large Order Alert")
    logger.info("  * Whale Activity Alert")
    logger.info("- SYSTEM alerts channel should have received:")
    logger.info("  * CPU Alert (for comparison)")
    logger.info("✅ Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_trading_webhook_alerts()) 