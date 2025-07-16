#!/usr/bin/env python3
"""
Simple script to add trade-based whale enhancement method to monitor.py
"""

import os
import re
import sys
from pathlib import Path

def add_enhancement_method():
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
    backup_path = monitor_path.with_suffix('.py.backup_simple_enhancement')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Created backup at: {backup_path}")
    
    # Define the enhancement method - properly indented as a class method
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
    
    # Find the whale activity monitoring function and add a call to our enhancement
    whale_activity_lines = content.split('\n')
    
    # Find lines containing whale activity monitoring and distribution alert
    modified_lines = []
    in_whale_function = False
    added_call = False
    
    for i, line in enumerate(whale_activity_lines):
        modified_lines.append(line)
        
        # Check if we're entering the whale activity function
        if 'async def _monitor_whale_activity' in line:
            in_whale_function = True
        
        # If we're in the whale function and see distribution alert, add our call
        if (in_whale_function and 
            'distribution alert' in line.lower() and 
            not added_call):
            
            # Look ahead for the except block
            j = i + 1
            while j < len(whale_activity_lines) and j < i + 20:  # Look within next 20 lines
                if 'except Exception as e:' in whale_activity_lines[j] and 'whale activity' in whale_activity_lines[j + 1]:
                    # Add our enhancement call before the except block
                    enhancement_call_lines = [
                        "                # ENHANCEMENT: Call trade-based whale analysis for additional detection",
                        "                else:",
                        "                    await self._check_trade_enhancements(",
                        "                        symbol, current_activity, current_price,", 
                        "                        accumulation_threshold, min_order_count, market_percentage",
                        "                    )",
                        ""
                    ]
                    
                    # Insert the lines before the except block
                    for call_line in enhancement_call_lines:
                        modified_lines.append(call_line)
                    
                    added_call = True
                    break
                j += 1
        
        # Check if we're leaving the whale function
        if in_whale_function and line.strip().startswith('async def ') and '_monitor_whale_activity' not in line:
            in_whale_function = False
    
    # Join the lines back together
    modified_content = '\n'.join(modified_lines)
    
    # Find a good place to add our method - at the end of the MarketMonitor class
    # Look for the end of the class (before any other class definition)
    if 'class MarketMonitor' in modified_content:
        # Find where to insert our method - before any other class starts
        next_class_pattern = r'\nclass (?!MarketMonitor)'
        next_class_match = re.search(next_class_pattern, modified_content)
        
        if next_class_match:
            insertion_point = next_class_match.start()
            print(f"📍 Found insertion point at position {insertion_point}")
            
            # Insert our method
            new_content = (modified_content[:insertion_point] + 
                          enhancement_method + 
                          modified_content[insertion_point:])
        else:
            # If no next class found, add at the end of the file
            print("📍 Adding method at end of file")
            new_content = modified_content + enhancement_method
    else:
        print("❌ Could not find MarketMonitor class!")
        return False
    
    # Write the enhanced content
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added trade-based whale enhancements!")
    if added_call:
        print("✅ Successfully added enhancement call to whale monitoring")
    else:
        print("⚠️ Could not add enhancement call - may need manual integration")
    
    return True

def main():
    """Main function"""
    print("🐋 Adding Trade-Based Whale Enhancement Method")
    print("=" * 50)
    
    try:
        success = add_enhancement_method()
        
        if success:
            print("\n🎉 **SUCCESS!** Enhancement method added!")
            print("\n📋 **Next Steps:**")
            print("   1. Test syntax: python -m py_compile src/monitoring/monitor.py")
            print("   2. Run verification: python scripts/verify_trade_data.py")
            print("   3. Restart monitoring system")
        else:
            print("\n❌ **FAILED** to add enhancement!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 **ERROR:** {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 