"""
Enhanced Alert Formatter for Virtuoso Trading System
Provides clean, informative, and actionable alert messages
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

class AlertFormatter:
    """Format alerts with improved clarity and actionable information"""
    
    def __init__(self):
        self.alert_levels = {
            'critical': {'emoji': '🚨', 'color': 0xFF0000},  # Red
            'high': {'emoji': '⚠️', 'color': 0xFFA500},     # Orange
            'medium': {'emoji': '📊', 'color': 0xFFFF00},   # Yellow
            'low': {'emoji': 'ℹ️', 'color': 0x3498DB},      # Blue
            'info': {'emoji': '💡', 'color': 0x00FF00}      # Green
        }
    
    def format_whale_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format whale activity alerts with clear, non-conflicting information"""
        
        symbol = data.get('symbol', 'UNKNOWN')
        subtype = data.get('subtype', 'activity')
        whale_trades = data.get('whale_trades', [])
        large_orders = data.get('large_orders', [])
        net_value = data.get('net_usd_value', 0)
        current_price = data.get('current_price', 0)
        signal_strength = data.get('signal_strength', 'UNKNOWN')
        
        # Calculate actual metrics
        total_buy_value = sum(t.get('value', 0) for t in whale_trades if t.get('side') == 'buy')
        total_sell_value = sum(t.get('value', 0) for t in whale_trades if t.get('side') == 'sell')
        buy_count = len([t for t in whale_trades if t.get('side') == 'buy'])
        sell_count = len([t for t in whale_trades if t.get('side') == 'sell'])
        total_trades = len(whale_trades)
        net_flow = total_buy_value - total_sell_value  # Initialize here for use throughout
        
        # Determine alert level and type
        if signal_strength == "CONFLICTING":
            alert_level = 'critical'
            alert_type = "⚠️ MANIPULATION WARNING"
        elif abs(net_value) > 5000000:
            alert_level = 'high'
            alert_type = "🐋 MAJOR WHALE ACTIVITY"
        elif abs(net_value) > 1000000:
            alert_level = 'medium'
            alert_type = "🐋 WHALE ACTIVITY"
        else:
            alert_level = 'low'
            alert_type = "📊 MARKET ACTIVITY"
        
        # Build clear, structured message
        embed = {
            'title': f"{alert_type} - {symbol}",
            'color': self.alert_levels[alert_level]['color'],
            'timestamp': datetime.utcnow().isoformat(),
            'fields': []
        }
        
        # Price Information (always first)
        if current_price >= 0:
            embed['fields'].append({
                'name': '💰 Current Price',
                'value': f"${current_price:,.4f}" if current_price < 10 else f"${current_price:,.2f}",
                'inline': True
            })
        
        # Trade Summary (if trades exist)
        if total_trades > 0:
            trade_summary = f"**Total:** {total_trades} trades\n"
            if buy_count > 0:
                trade_summary += f"**Buys:** {buy_count} (${total_buy_value:,.0f})\n"
            if sell_count > 0:
                trade_summary += f"**Sells:** {sell_count} (${total_sell_value:,.0f})\n"
            
            embed['fields'].append({
                'name': '📈 Trade Activity',
                'value': trade_summary.strip(),
                'inline': True
            })
            
            # Net Flow (net_flow already calculated above)
            flow_direction = "↗️ Net Buying" if net_flow > 0 else "↘️ Net Selling"
            embed['fields'].append({
                'name': '💸 Net Flow',
                'value': f"{flow_direction}\n${abs(net_flow):,.0f}",
                'inline': True
            })
        
        # Order Book Analysis (if large orders exist)
        if large_orders:
            bid_orders = [o for o in large_orders if o.get('side') == 'bid']
            ask_orders = [o for o in large_orders if o.get('side') == 'ask']
            
            orderbook_summary = ""
            if bid_orders:
                total_bid_value = sum(o.get('value', 0) for o in bid_orders)
                orderbook_summary += f"**Buy Orders:** {len(bid_orders)} (${total_bid_value:,.0f})\n"
            if ask_orders:
                total_ask_value = sum(o.get('value', 0) for o in ask_orders)
                orderbook_summary += f"**Sell Orders:** {len(ask_orders)} (${total_ask_value:,.0f})\n"
            
            if orderbook_summary:
                embed['fields'].append({
                    'name': '📚 Order Book',
                    'value': orderbook_summary.strip(),
                    'inline': False
                })
        
        # Signal Analysis
        signal_analysis = self._get_signal_analysis(
            signal_strength, subtype, buy_count, sell_count, 
            large_orders, whale_trades
        )
        
        if signal_analysis:
            embed['fields'].append({
                'name': '🎯 Signal Analysis',
                'value': signal_analysis,
                'inline': False
            })
        
        # Risk Assessment
        risk_level = self._assess_risk(signal_strength, net_value, total_trades)
        embed['fields'].append({
            'name': '⚡ Risk Level',
            'value': risk_level,
            'inline': True
        })
        
        # Recommended Action
        action = self._get_recommended_action(
            signal_strength, subtype, net_flow, risk_level
        )
        embed['fields'].append({
            'name': '💡 Recommended Action',
            'value': action,
            'inline': False
        })
        
        # Add footer with metadata
        embed['footer'] = {
            'text': f"Alert ID: {data.get('alert_id', 'N/A')} | Virtuoso Trading System"
        }
        
        return embed
    
    def _get_signal_analysis(self, signal_strength: str, subtype: str, 
                            buy_count: int, sell_count: int,
                            large_orders: List, whale_trades: List) -> str:
        """Generate clear signal analysis"""
        
        if signal_strength == "CONFLICTING":
            # Check for specific manipulation patterns
            has_fake_walls = len(large_orders) > 0 and len(whale_trades) > 0
            opposite_flow = (subtype == "accumulation" and sell_count > buy_count) or \
                          (subtype == "distribution" and buy_count > sell_count)
            
            if has_fake_walls and opposite_flow:
                return (
                    "**⚠️ MANIPULATION DETECTED**\n"
                    "• Order book shows large {0} orders\n"
                    "• Actual trades are mostly {1}\n"
                    "• Likely spoofing to create false signals\n"
                    "• **DO NOT TRADE** based on order book alone"
                ).format(
                    "buy" if subtype == "accumulation" else "sell",
                    "sells" if sell_count > buy_count else "buys"
                )
            else:
                return "**Mixed Signals** - Conflicting order flow patterns detected"
        
        elif signal_strength == "EXECUTING":
            direction = "buying" if buy_count > sell_count else "selling"
            return f"**Active Whale {direction.title()}**\nWhales are actively {direction} with confirmed trades"
        
        elif signal_strength == "POSITIONING":
            return "**Whale Positioning**\nLarge orders placed but not yet executing"
        
        else:
            return "**Normal Activity**\nNo significant whale patterns detected"
    
    def _assess_risk(self, signal_strength: str, net_value: float, 
                    total_trades: int) -> str:
        """Assess risk level based on signal characteristics"""
        
        if signal_strength == "CONFLICTING":
            return "🔴 **HIGH RISK** - Potential manipulation"
        elif abs(net_value) > 5000000 and total_trades > 50:
            return "🟠 **MEDIUM-HIGH** - Large whale activity"
        elif abs(net_value) > 1000000:
            return "🟡 **MEDIUM** - Significant activity"
        else:
            return "🟢 **LOW** - Normal market activity"
    
    def _get_recommended_action(self, signal_strength: str, subtype: str,
                               net_flow: float, risk_level: str) -> str:
        """Generate actionable recommendations"""
        
        if "HIGH RISK" in risk_level:
            return (
                "⛔ **AVOID TRADING**\n"
                "• Wait for manipulation to clear\n"
                "• Watch for sudden order cancellations\n"
                "• Monitor actual trade flow vs orders"
            )
        
        elif signal_strength == "EXECUTING":
            if net_flow > 1000000:
                return (
                    "📈 **BULLISH SIGNAL**\n"
                    "• Consider long positions on dips\n"
                    "• Set stops below whale entry\n"
                    "• Monitor for continuation"
                )
            elif net_flow < -1000000:
                return (
                    "📉 **BEARISH SIGNAL**\n"
                    "• Consider short positions on rallies\n"
                    "• Set stops above whale exit\n"
                    "• Watch for support breaks"
                )
            else:
                return "⏸️ **WAIT** - Monitor for clearer direction"
        
        else:
            return "👀 **MONITOR** - No immediate action required"
    
    def format_signal_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format confluence signal alerts"""
        
        symbol = data.get('symbol', 'UNKNOWN')
        signal_type = data.get('signal_type', 'NEUTRAL')
        confluence_score = data.get('confluence_score', 0)
        components = data.get('components', {})
        price = data.get('price', 0)
        reliability = data.get('reliability', 0)
        
        # Determine signal strength
        if confluence_score > 80:
            strength = "STRONG"
            emoji = "🚀" if signal_type == "BUY" else "🔻"
            color = 0x00FF00 if signal_type == "BUY" else 0xFF0000
        elif confluence_score > 65:
            strength = "MODERATE"
            emoji = "📈" if signal_type == "BUY" else "📉"
            color = 0x90EE90 if signal_type == "BUY" else 0xFFA07A
        else:
            strength = "WEAK"
            emoji = "📊"
            color = 0xFFFF00
        
        embed = {
            'title': f"{emoji} {strength} {signal_type} SIGNAL - {symbol}",
            'color': color,
            'timestamp': datetime.utcnow().isoformat(),
            'fields': []
        }
        
        # Key Metrics
        embed['fields'].append({
            'name': '📊 Signal Metrics',
            'value': (
                f"**Score:** {confluence_score:.1f}/100\n"
                f"**Reliability:** {reliability:.0%}\n"
                f"**Price:** ${price:,.4f}" if price < 10 else f"${price:,.2f}"
            ),
            'inline': True
        })
        
        # Top Components
        if components:
            sorted_components = sorted(components.items(), key=lambda x: x[1], reverse=True)
            top_3 = sorted_components[:3]
            
            component_text = ""
            for name, score in top_3:
                indicator = "✅" if score > 60 else "⚠️" if score > 40 else "❌"
                component_text += f"{indicator} **{name.title()}:** {score:.1f}\n"
            
            embed['fields'].append({
                'name': '🎯 Key Indicators',
                'value': component_text.strip(),
                'inline': True
            })
        
        # Entry Zones
        if signal_type == "BUY":
            entry_zones = self._calculate_entry_zones(price, 'buy')
        elif signal_type == "SELL":
            entry_zones = self._calculate_entry_zones(price, 'sell')
        else:
            entry_zones = None
        
        if entry_zones:
            embed['fields'].append({
                'name': '🎯 Entry Zones',
                'value': entry_zones,
                'inline': False
            })
        
        # Risk Management
        risk_mgmt = self._get_risk_management(signal_type, price, confluence_score)
        embed['fields'].append({
            'name': '⚡ Risk Management',
            'value': risk_mgmt,
            'inline': False
        })
        
        return embed
    
    def _calculate_entry_zones(self, price: float, direction: str) -> str:
        """Calculate optimal entry zones"""
        
        if direction == 'buy':
            return (
                f"**Aggressive:** ${price * 1.002:.4f} (Market)\n"
                f"**Optimal:** ${price * 0.995:.4f} (-0.5%)\n"
                f"**Conservative:** ${price * 0.99:.4f} (-1%)"
            )
        else:
            return (
                f"**Aggressive:** ${price * 0.998:.4f} (Market)\n"
                f"**Optimal:** ${price * 1.005:.4f} (+0.5%)\n"
                f"**Conservative:** ${price * 1.01:.4f} (+1%)"
            )
    
    def _get_risk_management(self, signal_type: str, price: float, 
                            confluence_score: float) -> str:
        """Generate risk management recommendations"""
        
        # Dynamic stop loss based on confluence
        if confluence_score > 80:
            stop_pct = 0.015  # 1.5% for strong signals
            target_pct = 0.03  # 3% target
        elif confluence_score > 65:
            stop_pct = 0.02  # 2% for moderate signals
            target_pct = 0.025  # 2.5% target
        else:
            stop_pct = 0.025  # 2.5% for weak signals
            target_pct = 0.02  # 2% target
        
        if signal_type == "BUY":
            stop_loss = price * (1 - stop_pct)
            target = price * (1 + target_pct)
            return (
                f"**Stop Loss:** ${stop_loss:.4f} (-{stop_pct:.1%})\n"
                f"**Target 1:** ${target:.4f} (+{target_pct:.1%})\n"
                f"**Risk/Reward:** 1:{target_pct/stop_pct:.1f}"
            )
        elif signal_type == "SELL":
            stop_loss = price * (1 + stop_pct)
            target = price * (1 - target_pct)
            return (
                f"**Stop Loss:** ${stop_loss:.4f} (+{stop_pct:.1%})\n"
                f"**Target 1:** ${target:.4f} (-{target_pct:.1%})\n"
                f"**Risk/Reward:** 1:{target_pct/stop_pct:.1f}"
            )
        else:
            return "**No Position** - Wait for clearer signals"