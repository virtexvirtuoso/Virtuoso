#!/usr/bin/env python3
"""
Simple script to test live trade data collection
"""

import asyncio
import sys
import os
from pathlib import Path
import json
from datetime import datetime
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_live_data():
    """Test live trade data collection"""
    
    print("🔍 **TESTING LIVE TRADE DATA COLLECTION**")
    print("=" * 50)
    
    try:
        # Import required modules
        from core.config.config_manager import ConfigManager
        from core.exchanges.bybit import BybitExchange
        import logging
        
        # Set up basic logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        logger = logging.getLogger(__name__)
        
        print("✅ Successfully imported required modules")
        
        # Initialize config
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Initialize exchange
        exchange = BybitExchange(config)
        await exchange.initialize()
        
        print("✅ Exchange initialized successfully")
        
        # Test symbol
        test_symbol = "BTCUSDT"
        
        print(f"\n📊 Testing live data for {test_symbol}...")
        
        # Get recent trades
        trades = await exchange.fetch_trades(test_symbol, limit=50)
        print(f"✅ Collected {len(trades)} recent trades")
        
        if trades:
            # Analyze trade data
            latest_trade = trades[0]
            trade_time = datetime.fromtimestamp(latest_trade['timestamp'] / 1000)
            time_diff = datetime.now() - trade_time
            
            print(f"\n📈 Latest trade analysis:")
            print(f"   Side: {latest_trade['side']}")
            print(f"   Amount: {latest_trade['amount']}")
            print(f"   Price: ${latest_trade['price']}")
            print(f"   Time: {trade_time}")
            print(f"   Age: {time_diff.total_seconds():.1f} seconds")
            
            if time_diff.total_seconds() < 60:
                print("✅ Trade data is LIVE (< 1 minute old)")
            else:
                print("⚠️ Trade data may be delayed")
            
            # Analyze trade patterns
            buy_trades = [t for t in trades if t['side'] == 'buy']
            sell_trades = [t for t in trades if t['side'] == 'sell']
            
            buy_volume = sum(t['amount'] for t in buy_trades)
            sell_volume = sum(t['amount'] for t in sell_trades)
            total_volume = buy_volume + sell_volume
            
            print(f"\n📊 Trade volume analysis (last {len(trades)} trades):")
            print(f"   Buy trades: {len(buy_trades)} ({buy_volume:,.2f} units)")
            print(f"   Sell trades: {len(sell_trades)} ({sell_volume:,.2f} units)")
            print(f"   Total volume: {total_volume:,.2f} units")
            
            if total_volume > 0:
                buy_percentage = (buy_volume / total_volume) * 100
                sell_percentage = (sell_volume / total_volume) * 100
                imbalance = (buy_volume - sell_volume) / total_volume
                
                print(f"   Buy percentage: {buy_percentage:.1f}%")
                print(f"   Sell percentage: {sell_percentage:.1f}%")
                print(f"   Trade imbalance: {imbalance:.3f}")
                
                if abs(imbalance) > 0.2:
                    direction = "bullish" if imbalance > 0 else "bearish"
                    print(f"   🎯 Significant {direction} imbalance detected!")
                else:
                    print("   ⚖️ Balanced trading activity")
            
            # Check for large trades (potential whale activity)
            large_trades = [t for t in trades if t['amount'] * t['price'] > 10000]  # $10k+ trades
            
            if large_trades:
                print(f"\n🐋 Large trades detected:")
                print(f"   Count: {len(large_trades)} out of {len(trades)} trades")
                
                for i, trade in enumerate(large_trades[:5]):  # Show top 5
                    value = trade['amount'] * trade['price']
                    trade_time = datetime.fromtimestamp(trade['timestamp'] / 1000)
                    print(f"   {i+1}. {trade['side'].upper()} ${value:,.0f} at {trade_time.strftime('%H:%M:%S')}")
            else:
                print(f"\n📊 No large trades (>$10k) in recent {len(trades)} trades")
        
        # Get orderbook for comparison
        orderbook = await exchange.fetch_order_book(test_symbol, limit=20)
        
        if orderbook and 'bids' in orderbook and 'asks' in orderbook:
            print(f"\n📚 Orderbook data:")
            print(f"   Bids: {len(orderbook['bids'])} levels")
            print(f"   Asks: {len(orderbook['asks'])} levels")
            
            if orderbook['bids'] and orderbook['asks']:
                best_bid = orderbook['bids'][0][0]
                best_ask = orderbook['asks'][0][0]
                spread = best_ask - best_bid
                spread_pct = (spread / best_bid) * 100
                
                print(f"   Best bid: ${best_bid}")
                print(f"   Best ask: ${best_ask}")
                print(f"   Spread: ${spread:.4f} ({spread_pct:.3f}%)")
        
        await exchange.close()
        
        print(f"\n🎉 **LIVE DATA TEST COMPLETED SUCCESSFULLY!**")
        print(f"\n✅ **Verification Results:**")
        print(f"   ✅ Exchange connection: Working")
        print(f"   ✅ Trade data collection: Working")
        print(f"   ✅ Orderbook data: Working")
        print(f"   ✅ Data freshness: {'Live' if time_diff.total_seconds() < 60 else 'Delayed'}")
        print(f"\n🚀 **Ready for enhanced whale detection!**")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   This indicates missing dependencies or incorrect paths")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        print(f"   Details: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        success = asyncio.run(test_live_data())
        return success
    except Exception as e:
        print(f"❌ Failed to run test: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 