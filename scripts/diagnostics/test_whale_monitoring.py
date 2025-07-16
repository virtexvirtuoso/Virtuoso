#!/usr/bin/env python3
"""
Diagnostic script to test whale monitoring system.
This script will help identify why whale alerts are showing zero units and imbalance.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import logging
from src.monitoring.monitor import MarketMonitor
from src.monitoring.alert_manager import AlertManager
from src.core.config import config_manager
from src.core.exchanges.bybit import BybitExchange
import time
import json

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_whale_monitoring():
    """Test the whale monitoring system with debug output."""
    
    try:
        logger.info("🐋 Starting whale monitoring diagnostic test...")
        
        # Initialize configuration
        config = config_manager.get_config()
        logger.info(f"Config loaded: {bool(config)}")
        
        # Create exchange instance
        exchange = BybitExchange()
        await exchange.initialize()
        logger.info("Exchange initialized")
        
        # Create alert manager
        alert_config = config.get('monitoring', {}).get('alerts', {})
        alert_manager = AlertManager(alert_config)
        logger.info("Alert manager created")
        
        # Create market monitor
        monitor = MarketMonitor(
            exchange=exchange,
            config=config,
            alert_manager=alert_manager
        )
        logger.info("Market monitor created")
        
        # Check whale activity configuration
        whale_config = monitor.whale_activity_config
        logger.info(f"Whale activity config: {json.dumps(whale_config, indent=2)}")
        
        # Test with BTC first
        symbol = "BTCUSDT"
        logger.info(f"\n🔍 Testing whale monitoring for {symbol}...")
        
        # Fetch market data manually
        logger.info("Fetching market data...")
        market_data = await monitor._get_market_data(symbol)
        
        # Check if we have orderbook data
        orderbook = market_data.get('orderbook')
        if not orderbook:
            logger.error("❌ No orderbook data available!")
            return
            
        logger.info(f"✅ Orderbook data available - Bids: {len(orderbook.get('bids', []))}, Asks: {len(orderbook.get('asks', []))}")
        
        # Check ticker data for price
        ticker = market_data.get('ticker', {})
        current_price = float(ticker.get('last', 0))
        logger.info(f"✅ Current price: ${current_price:,.2f}")
        
        # Manual whale threshold calculation (same as in monitor)
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        logger.info(f"Orderbook depth - Bids: {len(bids)}, Asks: {len(asks)}")
        
        # Sample some orders for debugging
        if bids:
            logger.info(f"Top 5 bids: {bids[:5]}")
        if asks:
            logger.info(f"Top 5 asks: {asks[:5]}")
        
        # Calculate whale threshold manually
        all_sizes = []
        for order in bids[:50] + asks[:50]:
            if isinstance(order, list) and len(order) >= 2:
                all_sizes.append(float(order[1]))
        
        logger.info(f"Order sizes collected: {len(all_sizes)}")
        
        if all_sizes:
            import numpy as np
            mean_size = float(np.mean(all_sizes))
            std_size = float(np.std(all_sizes))
            whale_threshold = mean_size + (2 * std_size)
            
            logger.info(f"📊 Whale threshold calculation:")
            logger.info(f"  - Mean size: {mean_size:.4f}")
            logger.info(f"  - Std deviation: {std_size:.4f}")
            logger.info(f"  - Whale threshold: {whale_threshold:.4f}")
            
            # Find whale orders
            whale_bids = [order for order in bids if float(order[1]) >= whale_threshold]
            whale_asks = [order for order in asks if float(order[1]) >= whale_threshold]
            
            logger.info(f"🐋 Whale orders found:")
            logger.info(f"  - Whale bids: {len(whale_bids)}")
            logger.info(f"  - Whale asks: {len(whale_asks)}")
            
            if whale_bids:
                logger.info(f"  - Sample whale bids: {whale_bids[:3]}")
            if whale_asks:
                logger.info(f"  - Sample whale asks: {whale_asks[:3]}")
            
            # Calculate volumes
            whale_bid_volume = sum(float(order[1]) for order in whale_bids)
            whale_ask_volume = sum(float(order[1]) for order in whale_asks)
            
            # Calculate total volumes
            total_bid_volume = sum(float(order[1]) for order in bids)
            total_ask_volume = sum(float(order[1]) for order in asks)
            
            # Calculate percentages
            bid_percentage = (whale_bid_volume / total_bid_volume) if total_bid_volume > 0 else 0
            ask_percentage = (whale_ask_volume / total_ask_volume) if total_ask_volume > 0 else 0
            
            # Calculate imbalance
            total_whale_volume = whale_bid_volume + whale_ask_volume
            if total_whale_volume > 0:
                bid_ratio = whale_bid_volume / total_whale_volume
                ask_ratio = whale_ask_volume / total_whale_volume
                imbalance = abs(bid_ratio - ask_ratio)
            else:
                imbalance = 0
            
            # Calculate USD values
            net_volume = whale_bid_volume - whale_ask_volume
            net_usd_value = net_volume * current_price
            
            logger.info(f"📈 Whale activity analysis:")
            logger.info(f"  - Whale bid volume: {whale_bid_volume:.4f} units")
            logger.info(f"  - Whale ask volume: {whale_ask_volume:.4f} units")
            logger.info(f"  - Net volume: {net_volume:.4f} units")
            logger.info(f"  - Net USD value: ${net_usd_value:,.2f}")
            logger.info(f"  - Bid percentage: {bid_percentage:.1%}")
            logger.info(f"  - Ask percentage: {ask_percentage:.1%}")
            logger.info(f"  - Imbalance ratio: {imbalance:.1%}")
            
            # Check thresholds
            logger.info(f"🎯 Threshold analysis:")
            logger.info(f"  - Accumulation threshold: ${whale_config.get('accumulation_threshold', 5000000):,}")
            logger.info(f"  - Distribution threshold: ${whale_config.get('distribution_threshold', 5000000):,}")
            logger.info(f"  - Imbalance threshold: {whale_config.get('imbalance_threshold', 0.3):.1%}")
            logger.info(f"  - Min order count: {whale_config.get('min_order_count', 8)}")
            logger.info(f"  - Market percentage: {whale_config.get('market_percentage', 0.05):.1%}")
            
            # Check if thresholds would be met
            accumulation_met = (
                net_usd_value > whale_config.get('accumulation_threshold', 5000000) and
                len(whale_bids) >= whale_config.get('min_order_count', 8) and
                bid_percentage > whale_config.get('market_percentage', 0.05) and
                imbalance > whale_config.get('imbalance_threshold', 0.3)
            )
            
            distribution_met = (
                abs(net_usd_value) > whale_config.get('distribution_threshold', 5000000) and
                net_usd_value < -whale_config.get('distribution_threshold', 5000000) and
                len(whale_asks) >= whale_config.get('min_order_count', 8) and
                ask_percentage > whale_config.get('market_percentage', 0.05) and
                imbalance > whale_config.get('imbalance_threshold', 0.3)
            )
            
            logger.info(f"⚡ Alert conditions:")
            logger.info(f"  - Would trigger accumulation alert: {accumulation_met}")
            logger.info(f"  - Would trigger distribution alert: {distribution_met}")
            
            if not accumulation_met and not distribution_met:
                logger.info("ℹ️  No alerts would be triggered with current thresholds")
                logger.info("💡 Consider lowering thresholds for testing:")
                logger.info(f"   - Lower accumulation threshold from ${whale_config.get('accumulation_threshold', 5000000):,} to ${1000000:,}")
                logger.info(f"   - Lower imbalance threshold from {whale_config.get('imbalance_threshold', 0.3):.1%} to 10%")
                logger.info(f"   - Lower min order count from {whale_config.get('min_order_count', 8)} to 3")
        
        else:
            logger.error("❌ No order sizes found for whale threshold calculation!")
        
        # Now test the actual monitoring method
        logger.info(f"\n🧪 Testing actual _monitor_whale_activity method...")
        
        # Clear any existing cooldowns for testing
        monitor._last_whale_alert = {}
        
        try:
            await monitor._monitor_whale_activity(symbol, market_data)
            logger.info("✅ _monitor_whale_activity completed without errors")
        except Exception as e:
            logger.error(f"❌ Error in _monitor_whale_activity: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info("🎉 Whale monitoring diagnostic test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Cleanup
        if 'exchange' in locals():
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_whale_monitoring()) 