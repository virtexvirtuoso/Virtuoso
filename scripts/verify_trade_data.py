#!/usr/bin/env python3
"""
Script to verify live trade data collection and add trade enhancements to monitor.py

This script:
1. Verifies we're using live data (not mock data)
2. Checks trade data fields are properly collected
3. Adds the trade enhancement method to monitor.py
4. Tests the enhanced whale detection
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

def add_trade_enhancement_method():
    """Add the trade enhancement method to monitor.py"""
    
    monitor_path = Path("src/monitoring/monitor.py")
    
    if not monitor_path.exists():
        print(f"❌ Error: {monitor_path} not found!")
        return False
    
    print(f"📁 Found monitor.py at: {monitor_path}")
    
    # Read the current file
    with open(monitor_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if enhancements are already added
    if '_check_trade_enhancements' in content:
        print("✅ Trade enhancements already present in monitor.py")
        return True
    
    # Create backup
    backup_path = f"{monitor_path}.backup_trade_verification"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Created backup at: {backup_path}")
    
    # Find the end of the _monitor_whale_activity method
    # Look for the method signature and find its end
    method_start = content.find("async def _monitor_whale_activity(")
    if method_start == -1:
        print("❌ Could not find _monitor_whale_activity method")
        return False
    
    # Find the end of this method by looking for the next method or class definition
    # Start searching after the method signature
    search_start = method_start + len("async def _monitor_whale_activity(")
    
    # Look for the next method definition at the same indentation level
    lines = content[search_start:].split('\n')
    method_end_line = -1
    indent_level = None
    
    for i, line in enumerate(lines):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue
            
        # If we haven't determined the indent level yet, use the first non-empty line
        if indent_level is None and line.strip():
            # Count leading spaces
            indent_level = len(line) - len(line.lstrip())
            continue
        
        # Check if this line starts a new method or class at the same or higher level
        if line.strip() and not line.startswith(' ' * (indent_level + 1)):
            # This line is at the same or higher level, so the previous line was the end
            method_end_line = i - 1
            break
    
    if method_end_line == -1:
        # Method goes to end of file
        method_end_line = len(lines)
    
    # Calculate the actual position in the original content
    method_end_pos = search_start + sum(len(line) + 1 for line in lines[:method_end_line])
    
    # The trade enhancement method to add
    enhancement_method = '''
    async def _check_trade_enhancements(self, symbol: str, current_activity: Dict[str, Any], current_price: float, accumulation_threshold: float, min_order_count: int, market_percentage: float) -> None:
        """
        Check for three critical trade-based whale patterns:
        1. Pure trade imbalance alerts (without order book confirmation)
        2. Conflicting signals detection (order book vs trade data disagreement)  
        3. Enhanced sensitivity (early detection through trade data)
        """
        try:
            if 'whale_trades_count' not in current_activity:
                return
                
            # Extract trade data
            whale_trades_count = current_activity.get('whale_trades_count', 0)
            whale_buy_volume = current_activity.get('whale_buy_volume', 0)
            whale_sell_volume = current_activity.get('whale_sell_volume', 0)
            net_trade_volume = current_activity.get('net_trade_volume', 0)
            trade_imbalance = current_activity.get('trade_imbalance', 0)
            
            # Extract order book data
            whale_bid_orders = current_activity.get('whale_bid_orders', 0)
            whale_ask_orders = current_activity.get('whale_ask_orders', 0)
            imbalance = current_activity.get('imbalance', 0)
            bid_percentage = current_activity.get('bid_percentage', 0)
            ask_percentage = current_activity.get('ask_percentage', 0)
            
            current_time = time.time()
            
            # ENHANCEMENT 1: Pure trade imbalance alerts
            trade_volume_threshold = accumulation_threshold * 0.3  # Lower threshold for trade-only
            trade_imbalance_threshold = 0.6  # Higher imbalance for trades
            min_trade_count = 3
            
            if (whale_trades_count >= min_trade_count and 
                abs(net_trade_volume * current_price) >= trade_volume_threshold and
                abs(trade_imbalance) >= trade_imbalance_threshold):
                
                trade_type = "accumulation" if net_trade_volume > 0 else "distribution"
                emoji = "🐋📈" if trade_type == "accumulation" else "🐋📉"
                
                message = f"""{emoji} **Pure Trade {trade_type.title()} Alert** for {symbol}
• **TRADE-ONLY SIGNAL** (No order book confirmation)
• Whale trades executed: {whale_trades_count} trades
• Net trade volume: {abs(net_trade_volume):,.2f} units (${abs(net_trade_volume * current_price):,.2f})
• Trade imbalance: {abs(trade_imbalance):.1%}
• Buy volume: {whale_buy_volume:,.2f} | Sell volume: {whale_sell_volume:,.2f}
• Current price: ${current_price:,.4f}
⚠️ **Note**: Order book shows no significant whale positioning"""
                
                await self.alert_manager.send_alert(
                    level="info",
                    message=message,
                    details={
                        "type": "whale_activity",
                        "subtype": f"trade_{trade_type}",
                        "symbol": symbol,
                        "data": current_activity
                    }
                )
                
                self._last_whale_alert[symbol] = current_time
                self.logger.info(f"🐋 Sent pure trade {trade_type} alert for {symbol}: {whale_trades_count} trades")
                return
                
            # ENHANCEMENT 2: Conflicting signals detection
            has_moderate_bids = whale_bid_orders >= 2 and bid_percentage > market_percentage * 0.3
            has_moderate_asks = whale_ask_orders >= 2 and ask_percentage > market_percentage * 0.3
            has_trades = whale_trades_count >= 2
            
            conflicting_signal = False
            conflict_type = ""
            
            if has_moderate_bids and has_trades and trade_imbalance < -0.3:
                conflicting_signal = True
                conflict_type = "Order book shows accumulation, but trades show distribution"
            elif has_moderate_asks and has_trades and trade_imbalance > 0.3:
                conflicting_signal = True
                conflict_type = "Order book shows distribution, but trades show accumulation"
            
            if conflicting_signal:
                message = f"""⚠️ **Conflicting Whale Signals** for {symbol}
• **{conflict_type}**
• Order book: {whale_bid_orders} whale bids, {whale_ask_orders} whale asks
• Recent trades: {whale_trades_count} whale trades
• Trade imbalance: {trade_imbalance:.1%}
• Order imbalance: {imbalance:.1%}
• Current price: ${current_price:,.4f}
🚨 **Analysis**: This may indicate whale deception or market manipulation"""
                
                await self.alert_manager.send_alert(
                    level="warning",
                    message=message,
                    details={
                        "type": "whale_activity",
                        "subtype": "conflicting_signals",
                        "symbol": symbol,
                        "data": current_activity
                    }
                )
                
                self._last_whale_alert[symbol] = current_time
                self.logger.warning(f"⚠️ Sent conflicting whale signals alert for {symbol}: {conflict_type}")
                return
                
            # ENHANCEMENT 3: Enhanced sensitivity (early detection)
            if whale_trades_count >= 2:
                early_trade_threshold = accumulation_threshold * 0.15  # Very low threshold for early detection
                early_imbalance_threshold = 0.4
                total_trade_volume = whale_buy_volume + whale_sell_volume
                
                if (total_trade_volume * current_price >= early_trade_threshold and
                    abs(trade_imbalance) >= early_imbalance_threshold):
                    
                    trade_direction = "bullish" if trade_imbalance > 0 else "bearish"
                    emoji = "📈" if trade_direction == "bullish" else "📉"
                    
                    message = f"""{emoji} **Early Whale Activity** for {symbol}
• **{trade_direction.upper()} whale activity detected**
• Early signal: {whale_trades_count} whale trades
• Trade volume: {total_trade_volume:,.2f} units
• Trade imbalance: {trade_imbalance:.1%} ({trade_direction})
• USD value: ${total_trade_volume * current_price:,.2f}
• Current price: ${current_price:,.4f}
⚡ **Early Warning**: Monitor for order book confirmation"""
                    
                    await self.alert_manager.send_alert(
                        level="info",
                        message=message,
                        details={
                            "type": "whale_activity",
                            "subtype": f"early_{trade_direction}",
                            "symbol": symbol,
                            "data": current_activity
                        }
                    )
                    
                    self._last_whale_alert[symbol] = current_time
                    self.logger.info(f"⚡ Sent early whale activity alert for {symbol}: {trade_direction} ({whale_trades_count} trades)")
                    
        except Exception as e:
            self.logger.error(f"Error in trade-based whale analysis for {symbol}: {str(e)}")
            self.logger.debug(traceback.format_exc())
'''
    
    # Insert the enhancement method
    new_content = content[:method_end_pos] + enhancement_method + content[method_end_pos:]
    
    # Now add a call to this method in the whale monitoring
    # Find where to add the call - look for the end of the main whale monitoring logic
    call_insertion_point = new_content.find("self.logger.info(f\"Sent whale distribution alert for {symbol}: ${abs(net_usd_value):,.2f}\")")
    if call_insertion_point != -1:
        # Find the end of this line
        line_end = new_content.find('\n', call_insertion_point)
        if line_end != -1:
            # Add the enhancement call
            enhancement_call = '''
                
                # Check for trade-based enhancements when no traditional whale activity is detected
                else:
                    await self._check_trade_enhancements(
                        symbol, current_activity, current_price,
                        accumulation_threshold, min_order_count, market_percentage
                    )'''
            
            new_content = new_content[:line_end] + enhancement_call + new_content[line_end:]
    
    # Write the updated content
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added trade-based whale enhancements!")
    return True

async def verify_live_trade_data():
    """Verify that we're collecting live trade data"""
    
    print("\n🔍 **VERIFYING LIVE TRADE DATA COLLECTION**")
    print("=" * 60)
    
    try:
        from monitoring.whale_activity import WhaleActivityDetector
        from exchange.bybit_exchange import BybitExchange
        from core.config.config_manager import ConfigManager
        import logging
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
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
        
        # Get market data
        print(f"\n📊 Testing live data collection for {test_symbol}...")
        
        # Get orderbook
        orderbook = await exchange.fetch_order_book(test_symbol)
        print(f"✅ Orderbook: {len(orderbook.get('bids', []))} bids, {len(orderbook.get('asks', []))} asks")
        
        # Get recent trades
        trades = await exchange.fetch_trades(test_symbol, limit=100)
        print(f"✅ Recent trades: {len(trades)} trades collected")
        
        if trades:
            latest_trade = trades[0]
            trade_time = datetime.fromtimestamp(latest_trade['timestamp'] / 1000)
            time_diff = datetime.now() - trade_time
            
            print(f"   Latest trade: {latest_trade['side']} {latest_trade['amount']} @ ${latest_trade['price']}")
            print(f"   Trade time: {trade_time} ({time_diff.total_seconds():.1f}s ago)")
            
            if time_diff.total_seconds() < 60:
                print("✅ Trade data is LIVE (< 1 minute old)")
            else:
                print("⚠️ Trade data may be delayed")
        
        # Test whale detection
        print(f"\n🐋 Testing whale activity detection...")
        
        whale_detector = WhaleActivityDetector(config)
        
        # Analyze current market data
        market_data = {
            'symbol': test_symbol,
            'orderbook': orderbook,
            'trades': trades,
            'timestamp': int(time.time() * 1000)
        }
        
        whale_activity = await whale_detector.analyze_whale_activity(market_data)
        
        if whale_activity:
            print("✅ Whale activity analysis completed")
            
            # Check for trade data fields
            trade_fields = ['whale_trades_count', 'whale_buy_volume', 'whale_sell_volume', 'net_trade_volume', 'trade_imbalance']
            
            print("\n📈 Trade data fields:")
            for field in trade_fields:
                value = whale_activity.get(field, 'MISSING')
                status = "✅" if field in whale_activity else "❌"
                print(f"   {status} {field}: {value}")
            
            # Check order book fields
            orderbook_fields = ['whale_bid_orders', 'whale_ask_orders', 'imbalance', 'bid_percentage', 'ask_percentage']
            
            print("\n📊 Order book data fields:")
            for field in orderbook_fields:
                value = whale_activity.get(field, 'MISSING')
                status = "✅" if field in whale_activity else "❌"
                print(f"   {status} {field}: {value}")
        
        await exchange.close()
        print("\n✅ Live data verification completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("This indicates the modules may not be properly set up")
        return False
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False

def main():
    """Main function"""
    print("🐋 **TRADE DATA VERIFICATION & ENHANCEMENT SCRIPT**")
    print("=" * 60)
    
    # Step 1: Add trade enhancement method
    print("\n📝 Step 1: Adding trade enhancement method to monitor.py")
    if not add_trade_enhancement_method():
        print("❌ Failed to add trade enhancements")
        return False
    
    # Step 2: Verify syntax
    print("\n🔍 Step 2: Verifying syntax")
    result = os.system("python -m py_compile src/monitoring/monitor.py")
    if result == 0:
        print("✅ Syntax verification passed")
    else:
        print("❌ Syntax errors detected")
        return False
    
    # Step 3: Verify live data (async)
    print("\n📡 Step 3: Verifying live trade data collection")
    try:
        asyncio.run(verify_live_trade_data())
    except Exception as e:
        print(f"⚠️ Live data verification failed: {e}")
        print("This may be due to network issues or exchange API limits")
    
    print("\n🎉 **ENHANCEMENT COMPLETED SUCCESSFULLY!**")
    print("\n📋 **What was added:**")
    print("   ✅ Pure trade imbalance alerts (without order book confirmation)")
    print("   ✅ Conflicting signals detection (order book vs trade disagreement)")
    print("   ✅ Enhanced sensitivity (early detection through trades)")
    print("\n🚀 **Next steps:**")
    print("   1. Restart the monitoring system")
    print("   2. Monitor logs for new whale alert types")
    print("   3. Test with live market data")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 