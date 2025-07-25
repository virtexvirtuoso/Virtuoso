#!/usr/bin/env python3

"""
Test script to generate a signal with rich formatting and PDF attachment
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import just what we need
import json
import yaml
import logging

async def test_rich_alert():
    """Test generating a signal with rich formatting and PDF"""
    
    # Load configuration
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml'), 'r') as f:
        config = yaml.safe_load(f)
    
    # Import and create AlertManager instance
    from src.monitoring.alert_manager import AlertManager
    alert_manager = AlertManager(config)
    
    # Create test signal data (same as before but ensure we have all fields)
    signal_data = {
        "symbol": "BTCUSDT",
        "signal_type": "BUY", 
        "confluence_score": 76.2,
        "reliability": 93.1,
        "timestamp": "2025-07-22T10:45:30.123456",
        "price": 104125.75,
        "transaction_id": "test-rich-alert-123",
        "signal_id": "signal-rich-test-456",
        "components": {
            "technical": 79.1,
            "volume": 73.8,
            "orderbook": 87.2,
            "orderflow": 78.5,
            "sentiment": 63.4,
            "price_structure": 71.2
        },
        "sub_components": {
            "technical": {
                "rsi": 74.2,
                "macd": 69.8,
                "ao": 82.5,
                "williams_r": 76.1,
                "cci": 77.3,
                "atr": 70.8
            },
            "volume": {
                "relative_volume": 84.1,
                "volume_delta": 71.2,
                "obv": 76.8,
                "cmf": 73.4,
                "adl": 70.1,
                "volume_profile": 74.9,
                "vwap": 72.3
            },
            "orderbook": {
                "imbalance": 89.8,
                "depth": 85.1,
                "mpi": 84.7,
                "liquidity": 83.9,
                "spread": 80.2,
                "pressure": 87.3,
                "absorption_exhaustion": 82.5,
                "obps": 81.1,
                "dom_momentum": 79.8
            },
            "orderflow": {
                "cvd": 80.9,
                "trade_flow": 77.8,
                "imbalance": 76.3,
                "open_interest": 75.7,
                "pressure": 80.1,
                "liquidity": 74.2,
                "liquidity_zones": 72.8
            },
            "sentiment": {
                "funding_rate": 66.8,
                "liquidations": 60.2,
                "long_short_ratio": 64.1,
                "volatility": 61.5,
                "market_activity": 65.3,
                "risk": 62.1
            },
            "price_structure": {
                "trend_position": 74.5,
                "support_resistance": 69.8,
                "order_blocks": 73.1,
                "volume_profile": 69.2,
                "market_structure": 71.4,
                "range_analysis": 68.1
            }
        },
        "market_data": {
            "volume_24h": 29547362840,
            "change_24h": 2.78,
            "high_24h": 105250.75,
            "low_24h": 102890.25,
            "turnover_24h": 3065847291000
        },
        "interpretations": {
            "technical": "Technical indicators show strong bullish momentum with RSI at 74.2 indicating strong upward pressure. MACD shows positive divergence with strong momentum continuation.",
            "volume": "Volume analysis reveals significant institutional participation with 84.1% relative volume spike. Volume delta strongly bullish, indicating sustained buying pressure.",
            "orderbook": "Extreme orderbook imbalance at 89.8% favoring buyers. Depth analysis shows robust bid-side support with minimal ask-side resistance.",
            "orderflow": "Cumulative volume delta at 80.9% confirms institutional accumulation. Trade flow indicates coordinated buying patterns.",
            "sentiment": "Mixed sentiment with funding rates neutral. Long/short ratio slightly bullish. Low liquidation risk detected.",
            "price_structure": "Price structure shows healthy uptrend continuation with strong support levels. Order blocks provide solid foundation."
        },
        "actionable_insights": [
            "🚀 Strong bullish bias - Consider aggressive position sizing",
            "📈 Monitor for momentum continuation above $104,500 resistance", 
            "⚡ Positive institutional flow supports sustained upward movement",
            "🎯 Target levels: $106,000 (short-term), $108,500 (extended)",
            "🛡️ Risk management: Stop below $103,200 support level"
        ],
        "top_components": [
            {
                "name": "Orderbook Imbalance",
                "category": "Orderbook", 
                "value": 89.8,
                "impact": 3.4,
                "trend": "up",
                "description": "Extreme bid-side dominance indicates strong buying pressure"
            },
            {
                "name": "Relative Volume",
                "category": "Volume",
                "value": 84.1, 
                "impact": 2.9,
                "trend": "up",
                "description": "Significant volume spike confirms institutional interest"
            },
            {
                "name": "Technical AO",
                "category": "Technical",
                "value": 82.5,
                "impact": 2.3,
                "trend": "up", 
                "description": "Strong momentum with room for continuation"
            }
        ]
    }
    
    print("🧪 Testing Rich Alert with PDF Generation")
    print("="*60)
    print(f"📊 Signal: {signal_data['symbol']} {signal_data['signal_type']}")
    print(f"🎯 Confluence Score: {signal_data['confluence_score']}")
    print(f"💎 Reliability: {signal_data['reliability']}%")
    print()
    
    try:
        # Send signal alert - this should trigger frequency tracking and rich formatting
        await alert_manager.send_signal_alert(signal_data)
        print("✅ Alert sent successfully!")
        
    except Exception as e:
        print(f"❌ Error sending alert: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rich_alert())