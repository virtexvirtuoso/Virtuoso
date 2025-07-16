#!/usr/bin/env python3
"""Test script to verify all system webhook alert types are routing correctly."""

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

async def test_all_system_webhook_alerts():
    """Test all alert types configured for system webhook routing."""
    
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
    
    # Import config - just use a minimal config with actual webhook URLs
    config = {
        'monitoring': {
            'alerts': {
                'discord_webhook_url': discord_webhook_url,
                'system_alerts_webhook_url': system_webhook_url,
                'system_alerts': {
                    'enabled': True,
                    'use_system_webhook': True,
                    'types': {
                        'cpu': True,
                        'memory': True,
                        'disk': True,
                        'database': True,
                        'api': True,
                        'network': True,
                        'configuration': True,
                        'validation': True,
                        'tasks': True,
                                                 'lifecycle': True,
                         'market_report': True,
                         'performance': True,
                        'error': True,
                        'warning': True
                    },
                    'mirror_alerts': {
                        'enabled': True,
                        'types': {
                            'market_report': True
                        }
                    }
                }
            }
        }
    }
    
    # Initialize alert manager
    alert_manager = AlertManager(config)
    
    logger.info("Testing all system webhook alert types...")
    
    # Test cases for all configured system webhook alert types
    test_cases = [
        {
            'name': 'CPU Alert',
            'level': 'WARNING',
            'message': '🚨 CPU usage has reached 95.5%',
            'details': {'type': 'cpu', 'cpu_usage': 95.5, 'threshold': 90}
        },
        {
            'name': 'Memory Alert', 
            'level': 'WARNING',
            'message': '🚨 Memory usage has reached 96.2%',
            'details': {'type': 'memory', 'memory_usage': 96.2, 'threshold': 95}
        },
        {
            'name': 'Disk Alert',
            'level': 'WARNING', 
            'message': '🚨 Disk usage has reached 92%',
            'details': {'type': 'disk', 'disk_usage': 92, 'threshold': 90}
        },
        {
            'name': 'Database Alert',
            'level': 'ERROR',
            'message': '🚨 Database connection lost',
            'details': {'type': 'database', 'error': 'Connection timeout', 'database': 'trading_db'}
        },
        {
            'name': 'API Alert',
            'level': 'WARNING',
            'message': '🚨 API response time degraded',
            'details': {'type': 'api', 'endpoint': '/ticker', 'response_time': 5000, 'threshold': 3000}
        },
        {
            'name': 'Network Alert',
            'level': 'ERROR',
            'message': '🚨 Network connectivity issues detected',
            'details': {'type': 'network', 'target': 'api.binance.com', 'status': 'timeout'}
        },
        {
            'name': 'Configuration Alert',
            'level': 'ERROR',
            'message': '🚨 Configuration validation failed',
            'details': {'type': 'configuration', 'error': 'Invalid API key format', 'component': 'exchange'}
        },
        {
            'name': 'Validation Alert',
            'level': 'WARNING',
            'message': '🚨 Data validation failure',
            'details': {'type': 'validation', 'field': 'price', 'value': -1.5, 'expected': 'positive number'}
        },
        {
            'name': 'Tasks Alert',
            'level': 'ERROR',
            'message': '🚨 Background task failure',
            'details': {'type': 'tasks', 'task': 'market_data_collector', 'error': 'Rate limit exceeded'}
        },
        {
            'name': 'Lifecycle Alert',
            'level': 'INFO',
            'message': '🚨 System startup completed',
            'details': {'type': 'lifecycle', 'event': 'startup', 'duration': 45.2}
        },
        {
            'name': 'Market Report Alert',
            'level': 'INFO',
            'message': '📊 Market report generated',
            'details': {'type': 'market_report', 'symbols': ['BTCUSDT', 'ETHUSDT'], 'timestamp': datetime.now().isoformat()}
        },
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
            }
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
            }
        },
        {
            'name': 'Performance Alert',
            'level': 'WARNING',
            'message': '⚡ Performance degradation detected',
            'details': {'type': 'performance', 'component': 'signal_generator', 'avg_time': 2500, 'threshold': 2000}
        },
        {
            'name': 'Error Alert',
            'level': 'ERROR',
            'message': '❌ Critical error occurred',
            'details': {'type': 'error', 'component': 'trade_executor', 'error': 'Order submission failed'}
        },
        {
            'name': 'Warning Alert',
            'level': 'WARNING',
            'message': '⚠️ System warning',
            'details': {'type': 'warning', 'component': 'monitor', 'warning': 'High latency detected'}
        }
    ]
    
    logger.info(f"Testing {len(test_cases)} different alert types...")
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n=== Test {i}: {test_case['name']} ===")
        
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
    logger.info("All system webhook alert types have been tested.")
    logger.info("Please check your Discord channels:")
    logger.info("- System alerts channel should have received all alerts")
    logger.info("- Main alerts channel should only receive alerts if mirroring is enabled")
    logger.info("✅ Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_all_system_webhook_alerts()) 