#!/usr/bin/env python3
"""
Test script for enhanced whale alerts
Tests the new market intelligence features in whale activity monitoring
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.monitoring.alert_manager import AlertManager
from src.core.config.config_manager import ConfigManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_enhanced_whale_alerts():
    """Test the enhanced whale alert system with market intelligence."""
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager._config
        
        # Initialize alert manager
        alert_manager = AlertManager(config)
        await alert_manager.start()
        
        logger.info("🧪 Testing Simplified Whale Alert System (EXECUTING & CONFLICTING only)")
        
        # Test Case 1: EXECUTING Whale Accumulation
        logger.info("\n⚡ Test Case 1: EXECUTING Whale Accumulation")
        
        executing_whale_data = {
            'net_whale_volume': 125.50,
            'net_usd_value': 8750000,  # $8.75M
            'whale_bid_orders': 12,
            'whale_ask_orders': 4,
            'bid_percentage': 0.45,
            'ask_percentage': 0.15,
            'imbalance': 0.62,
            'whale_trades_count': 8,  # Active trades
            'whale_buy_volume': 95.2,
            'whale_sell_volume': 22.1,
            'trade_imbalance': 0.73,
            'trade_confirmation': True,  # Will be EXECUTING since trades > 0
            'whale_bid_usd': 6200000,
            'whale_ask_usd': 2550000,
            'whale_bid_volume': 89.2,
            'whale_ask_volume': 36.3,
            'total_market_volume': 280.5,
            'whale_market_share': 0.447,
            'orderbook_depth': 145,
            'volume_velocity': 0.85,
            'price': 69750.25,
            # Individual whale trades
            'top_whale_trades': [
                {'side': 'buy', 'size': 32.5, 'price': 69745.0, 'value': 2266712.50, 'time': time.time() - 300},
                {'side': 'buy', 'size': 28.3, 'price': 69752.0, 'value': 1973901.60, 'time': time.time() - 180},
                {'side': 'buy', 'size': 19.7, 'price': 69748.0, 'value': 1374015.60, 'time': time.time() - 60}
            ],
            # Large orders on book
            'top_whale_bids': [
                (69740.0, 45.2, 3152208.0),
                (69735.0, 38.7, 2698724.5),
                (69730.0, 25.8, 1799034.0)
            ],
            'top_whale_asks': [
                (69755.0, 12.3, 858186.5),
                (69760.0, 8.9, 620864.0)
            ]
        }
        
        await alert_manager.send_alert(
            level="info",
            message="Test Simplified Whale Alert - Executing Accumulation",
            details={
                "type": "whale_activity",
                "subtype": "accumulation", 
                "symbol": "BTCUSDT",
                "data": executing_whale_data
            }
        )
        
        await asyncio.sleep(2)
        
        # Test Case 2: CONFLICTING Whale Distribution Signal
        logger.info("\n⚠️ Test Case 2: CONFLICTING Whale Distribution")
        
        conflicting_whale_data = {
            'net_whale_volume': -85.30,
            'net_usd_value': -6420000,  # $6.42M distribution
            'whale_bid_orders': 6,
            'whale_ask_orders': 15,
            'bid_percentage': 0.18,
            'ask_percentage': 0.52,
            'imbalance': 0.71,
            'whale_trades_count': 5,
            'whale_buy_volume': 45.8,  # More buying than expected
            'whale_sell_volume': 31.2,  # Less selling than order book suggests
            'trade_imbalance': 0.19,   # Positive despite distribution orders
            'trade_confirmation': False,  # Orders and trades don't align
            'whale_bid_usd': 1840000,
            'whale_ask_usd': 4580000,
            'whale_bid_volume': 27.3,
            'whale_ask_volume': 58.0,
            'total_market_volume': 165.8,
            'whale_market_share': 0.515,
            'orderbook_depth': 98,
            'volume_velocity': 1.2,
            'price': 2.29,
            # Individual whale trades showing conflict
            'top_whale_trades': [
                {'side': 'buy', 'size': 15800.0, 'price': 2.288, 'value': 36150.40, 'time': time.time() - 240},
                {'side': 'buy', 'size': 12200.0, 'price': 2.291, 'value': 27950.20, 'time': time.time() - 120},
                {'side': 'sell', 'size': 8900.0, 'price': 2.285, 'value': 20336.50, 'time': time.time() - 90}
            ],
            # Large orders showing distribution intent
            'top_whale_bids': [
                (2.280, 5200.0, 11856.0),
                (2.275, 3800.0, 8645.0)
            ],
            'top_whale_asks': [
                (2.295, 18500.0, 42457.5),
                (2.300, 15200.0, 34960.0),
                (2.305, 12800.0, 29504.0)
            ]
        }
        
        await alert_manager.send_alert(
            level="info", 
            message="Test Enhanced Whale Alert - Conflicting Distribution",
            details={
                "type": "whale_activity",
                "subtype": "distribution",
                "symbol": "XRPUSDT", 
                "data": conflicting_whale_data
            }
        )
        
        await asyncio.sleep(2)
        
        logger.info("\n✅ Enhanced whale alert tests completed!")
        logger.info("Check your Discord channel for the enhanced alerts with:")
        logger.info("  • Unique Alert IDs for tracking (format: WA-timestamp-symbol)")
        logger.info("  • Prominent manipulation warnings for CONFLICTING signals")
        logger.info("  • Essential information only")
        logger.info("  • Plain English interpretation")
        logger.info("  • Only EXECUTING and CONFLICTING signals")
        logger.info("  • Individual whale trades and large orders")
        logger.info("  • Clean, actionable format")
        
        await asyncio.sleep(1)
        await alert_manager.stop()
        
    except Exception as e:
        logger.error(f"Error in enhanced whale alert test: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_enhanced_whale_alerts()) 