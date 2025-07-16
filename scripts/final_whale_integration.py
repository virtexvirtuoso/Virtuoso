#!/usr/bin/env python3
"""
Final script to integrate whale trade enhancements properly
"""

def integrate_whale_enhancements():
    """Integrate whale trade enhancements in monitor.py"""
    
    print("🐋 **FINAL WHALE TRADE ENHANCEMENTS INTEGRATION**")
    print("=" * 60)
    
    try:
        # Read the file
        with open("src/monitoring/monitor.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if the enhancement method already exists
        if "_check_trade_enhancements" in content:
            print("✅ Enhancement method already exists")
        else:
            print("❌ Enhancement method missing - adding it")
            
            # Add the enhancement method at the end of the MarketMonitor class
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
            
            # Find the last method in the MarketMonitor class and add the enhancement method before the last closing brace
            # Look for the pattern of the last method
            import re
            
            # Find the end of the last method in the class (before the final class closing)
            # Look for the last method definition and its end
            lines = content.split('\n')
            
            # Find where to insert the method - before the end of the class
            insert_line = -1
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].strip()
                if line and not line.startswith('#') and not line.startswith('"""'):
                    # This is the last non-empty, non-comment line
                    insert_line = i + 1
                    break
            
            if insert_line > 0:
                # Insert the enhancement method
                lines.insert(insert_line, enhancement_method)
                content = '\n'.join(lines)
                print(f"✅ Added enhancement method at line {insert_line}")
            else:
                print("❌ Could not find insertion point for enhancement method")
                return False
        
        # Now check if the enhancement call exists
        if "await self._check_trade_enhancements" in content:
            print("✅ Enhancement call already exists")
        else:
            print("❌ Enhancement call missing - adding it")
            
            # Find the whale distribution alert line and add the else clause
            distribution_pattern = r'(self\.logger\.info\(f"Sent whale distribution alert for \{symbol\}: \$\{abs\(net_usd_value\):\,\.2f\}"\))'
            
            if re.search(distribution_pattern, content):
                # Add the else clause with the enhancement call
                enhancement_call = '''
            else:
                # ENHANCEMENT: When no traditional whale alerts are triggered,
                # check for trade-based patterns that might be missed
                await self._check_trade_enhancements(
                    symbol, current_activity, current_price,
                    accumulation_threshold, min_order_count, market_percentage
                )
                '''
                
                # Replace the distribution alert line with itself plus the else clause
                replacement = r'\1' + enhancement_call
                content = re.sub(distribution_pattern, replacement, content)
                print("✅ Added enhancement call after whale distribution alert")
            else:
                print("❌ Could not find whale distribution alert to add enhancement call")
                return False
        
        # Write the updated content back
        with open("src/monitoring/monitor.py", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("\n🎉 **INTEGRATION COMPLETED SUCCESSFULLY!**")
        print("✅ Trade enhancement method: Added/Verified")
        print("✅ Enhancement call: Added/Verified") 
        print("✅ Integration: Complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during integration: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    integrate_whale_enhancements() 