#!/usr/bin/env python3
"""
Simple whale monitoring test to debug zero units and imbalance issue.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import logging
import json
import numpy as np
from src.core.exchanges.bybit import BybitExchange

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_whale_calculations():
    """Test whale calculations directly without the full monitoring system."""
    
    try:
        logger.info("🐋 Starting simple whale calculation test...")
        
        # Create exchange instance
        exchange = BybitExchange()
        await exchange.initialize()
        logger.info("Exchange initialized")
        
        # Test with BTC
        symbol = "BTCUSDT"
        logger.info(f"\n🔍 Testing whale calculations for {symbol}...")
        
        # Fetch orderbook directly
        logger.info("Fetching orderbook...")
        orderbook = await exchange.fetch_order_book(symbol, limit=100)
        
        if not orderbook:
            logger.error("❌ No orderbook data available!")
            return
            
        # Fetch ticker for price
        ticker = await exchange.fetch_ticker(symbol)
        current_price = float(ticker.get('last', 0))
        
        logger.info(f"✅ Current price: ${current_price:,.2f}")
        logger.info(f"✅ Orderbook - Bids: {len(orderbook.get('bids', []))}, Asks: {len(orderbook.get('asks', []))}")
        
        # Get bids and asks
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        
        # Sample some orders for debugging
        if bids:
            logger.info(f"Top 5 bids: {bids[:5]}")
        if asks:
            logger.info(f"Top 5 asks: {asks[:5]}")
        
        # Calculate whale threshold manually (same logic as MarketMonitor)
        all_sizes = []
        for order in bids[:50] + asks[:50]:
            if isinstance(order, list) and len(order) >= 2:
                all_sizes.append(float(order[1]))
        
        logger.info(f"Order sizes collected: {len(all_sizes)}")
        
        if all_sizes:
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
            bid_usd_value = whale_bid_volume * current_price
            ask_usd_value = whale_ask_volume * current_price
            
            logger.info(f"📈 Whale activity analysis:")
            logger.info(f"  - Whale bid volume: {whale_bid_volume:.4f} units")
            logger.info(f"  - Whale ask volume: {whale_ask_volume:.4f} units")
            logger.info(f"  - Net volume: {net_volume:.4f} units")
            logger.info(f"  - Net USD value: ${net_usd_value:,.2f}")
            logger.info(f"  - Bid USD value: ${bid_usd_value:,.2f}")
            logger.info(f"  - Ask USD value: ${ask_usd_value:,.2f}")
            logger.info(f"  - Bid percentage: {bid_percentage:.1%}")
            logger.info(f"  - Ask percentage: {ask_percentage:.1%}")
            logger.info(f"  - Imbalance ratio: {imbalance:.1%}")
            
            # Check if values are zero
            if whale_bid_volume == 0 and whale_ask_volume == 0:
                logger.warning("⚠️  ISSUE FOUND: Both whale bid and ask volumes are ZERO!")
                logger.warning("This means no orders meet the whale threshold.")
                logger.warning(f"Whale threshold: {whale_threshold:.4f}")
                logger.warning("Possible causes:")
                logger.warning("1. Threshold calculation is too high")
                logger.warning("2. Order sizes are very uniform (low standard deviation)")
                logger.warning("3. No large orders in the orderbook")
                
                # Show distribution of order sizes
                logger.info(f"Order size distribution:")
                logger.info(f"  - Min: {min(all_sizes):.4f}")
                logger.info(f"  - Max: {max(all_sizes):.4f}")
                logger.info(f"  - Median: {np.median(all_sizes):.4f}")
                logger.info(f"  - 95th percentile: {np.percentile(all_sizes, 95):.4f}")
                
                # Try a lower threshold
                lower_threshold = mean_size + std_size  # 1 std dev instead of 2
                whale_bids_lower = [order for order in bids if float(order[1]) >= lower_threshold]
                whale_asks_lower = [order for order in asks if float(order[1]) >= lower_threshold]
                
                logger.info(f"💡 With lower threshold ({lower_threshold:.4f}):")
                logger.info(f"  - Whale bids: {len(whale_bids_lower)}")
                logger.info(f"  - Whale asks: {len(whale_asks_lower)}")
            
            if imbalance == 0:
                logger.warning("⚠️  ISSUE FOUND: Imbalance is ZERO!")
                logger.warning("This means whale bid and ask volumes are equal.")
                logger.warning(f"Whale bid volume: {whale_bid_volume:.4f}")
                logger.warning(f"Whale ask volume: {whale_ask_volume:.4f}")
                logger.warning(f"Total whale volume: {total_whale_volume:.4f}")
                
                if total_whale_volume == 0:
                    logger.warning("Root cause: No whale activity detected (total whale volume = 0)")
                else:
                    logger.warning("Root cause: Perfectly balanced whale orders")
            
            # Create alert data structure (like what would be sent to AlertManager)
            alert_data = {
                'whale_bid_volume': whale_bid_volume,
                'whale_ask_volume': whale_ask_volume,
                'whale_bid_usd': bid_usd_value,
                'whale_ask_usd': ask_usd_value,
                'net_whale_volume': net_volume,
                'net_usd_value': net_usd_value,
                'imbalance': imbalance,
                'bid_percentage': bid_percentage,
                'ask_percentage': ask_percentage,
                'whale_bid_orders': len(whale_bids),
                'whale_ask_orders': len(whale_asks),
                'current_price': current_price
            }
            
            logger.info(f"📋 Alert data structure:")
            logger.info(json.dumps(alert_data, indent=2))
            
        else:
            logger.error("❌ No order sizes found for whale threshold calculation!")
        
        logger.info("🎉 Simple whale calculation test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Cleanup
        if 'exchange' in locals():
            await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_whale_calculations()) 