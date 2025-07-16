#!/usr/bin/env python3
"""
Simple script to add trade enhancement method to MarketMonitor class
"""

import os
import sys
from pathlib import Path

def add_trade_enhancement():
    """Add trade enhancement method to MarketMonitor class"""
    
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
    backup_path = f"{monitor_path}.backup_simple_trade"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"💾 Created backup at: {backup_path}")
    
    # Find the end of the MarketMonitor class
    # Look for the last method in the class
    last_method_pattern = "async def _monitor_whale_activity("
    last_method_pos = content.rfind(last_method_pattern)
    
    if last_method_pos == -1:
        print("❌ Could not find _monitor_whale_activity method")
        return False
    
    # Find the end of this method by looking for the next method or end of class
    # Start from the method signature and find the end
    method_start = last_method_pos
    
    # Find the end by looking for the next method at the same indentation level
    # or the end of the file
    lines = content[method_start:].split('\n')
    method_end_line = len(lines)  # Default to end of file
    
    # Look for the next method definition at class level (4 spaces indentation)
    for i, line in enumerate(lines[1:], 1):  # Skip the method signature line
        if line.strip() and not line.startswith('    ') and not line.startswith('\t'):
            # This line is at class level or higher, so previous line was end of method
            method_end_line = i
            break
        elif line.strip().startswith('async def ') or line.strip().startswith('def '):
            # Check indentation - if it's at class level (4 spaces), this is the next method
            if len(line) - len(line.lstrip()) == 4:
                method_end_line = i
                break
    
    # Calculate the insertion point
    method_end_pos = method_start + sum(len(line) + 1 for line in lines[:method_end_line])
    
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
    
    # Write the updated content
    with open(monitor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added trade enhancement method!")
    return True

def main():
    """Main function"""
    print("🐋 **SIMPLE TRADE ENHANCEMENT SCRIPT**")
    print("=" * 50)
    
    # Add the method
    if not add_trade_enhancement():
        print("❌ Failed to add trade enhancements")
        return False
    
    # Test syntax
    print("\n🔍 Testing syntax...")
    result = os.system("python -m py_compile src/monitoring/monitor.py")
    if result == 0:
        print("✅ Syntax verification passed")
    else:
        print("❌ Syntax errors detected")
        return False
    
    print("\n🎉 **SUCCESS!** Trade enhancement method added!")
    print("\n📋 **What was added:**")
    print("   ✅ _check_trade_enhancements() method to MarketMonitor class")
    print("   ✅ Pure trade imbalance alerts")
    print("   ✅ Conflicting signals detection")
    print("   ✅ Enhanced sensitivity alerts")
    print("\n🚀 **Next steps:**")
    print("   1. Call this method from _monitor_whale_activity")
    print("   2. Test with live market data")
    print("   3. Monitor for new alert types")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 