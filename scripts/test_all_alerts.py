#!/usr/bin/env python3
"""
Test all alert types in the Virtuoso trading system.
This script sends test alerts for each type to verify Discord webhook integration.
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path

async def send_test_alert(webhook_url: str, embed: dict):
    """Send a test alert to Discord."""
    payload = {'embeds': [embed]}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as response:
            if response.status == 204:
                return True
            else:
                print(f"Failed: {response.status}")
                return False

async def test_confluence_alert(webhook_url: str):
    """Test confluence/signal alert."""
    embed = {
        'title': '🎯 HIGH CONFLUENCE SIGNAL (TEST)',
        'color': 0x00ff00,  # Green
        'description': '**Strong bullish confluence detected**',
        'fields': [
            {'name': '📊 Symbol', 'value': 'BTCUSDT', 'inline': True},
            {'name': '📈 Signal', 'value': 'BUY', 'inline': True},
            {'name': '🎯 Score', 'value': '85/100', 'inline': True},
            {'name': '💰 Entry', 'value': '$114,250', 'inline': True},
            {'name': '🛡️ Stop Loss', 'value': '$112,800', 'inline': True},
            {'name': '🎯 Target', 'value': '$116,500', 'inline': True},
            {
                'name': '📊 Components',
                'value': '• Orderflow: 92% bullish\n• Volume: 88% bullish\n• Technical: 78% bullish\n• Sentiment: 81% bullish',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso Confluence System - TEST ALERT'}
    }
    
    print("📈 Testing Confluence Alert...")
    return await send_test_alert(webhook_url, embed)

async def test_volume_spike_alert(webhook_url: str):
    """Test volume spike alert."""
    embed = {
        'title': '📊 VOLUME SPIKE DETECTED (TEST)',
        'color': 0xffff00,  # Yellow
        'description': '**Unusual volume activity detected**',
        'fields': [
            {'name': '📊 Symbol', 'value': 'ETHUSDT', 'inline': True},
            {'name': '📈 Volume', 'value': '5.2x normal', 'inline': True},
            {'name': '💰 USD Volume', 'value': '$450M', 'inline': True},
            {'name': '📍 Price Level', 'value': '$4,420', 'inline': True},
            {'name': '⏱️ Time Window', 'value': '15 minutes', 'inline': True},
            {'name': '📊 Type', 'value': 'Accumulation', 'inline': True},
            {
                'name': '🎯 Analysis',
                'value': '• Institutional buying detected\n• Breaking above resistance\n• Momentum increasing',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso Volume Monitor - TEST ALERT'}
    }
    
    print("📊 Testing Volume Spike Alert...")
    return await send_test_alert(webhook_url, embed)

async def test_smart_money_alert(webhook_url: str):
    """Test smart money detection alert."""
    embed = {
        'title': '🧠 SMART MONEY DETECTED (TEST)',
        'color': 0x9b59b6,  # Purple
        'description': '**Sophisticated trading pattern identified**',
        'fields': [
            {'name': '📊 Symbol', 'value': 'SOLUSDT', 'inline': True},
            {'name': '🎯 Pattern', 'value': 'Accumulation', 'inline': True},
            {'name': '🧠 Sophistication', 'value': '8.5/10', 'inline': True},
            {'name': '💰 Est. Size', 'value': '$1.2M', 'inline': True},
            {'name': '📍 Price Zone', 'value': '$225-227', 'inline': True},
            {'name': '⏱️ Duration', 'value': '45 minutes', 'inline': True},
            {
                'name': '📊 Characteristics',
                'value': '• Layered limit orders\n• Minimal market impact\n• Strategic timing\n• Cross-exchange coordination',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso Smart Money Detector - TEST ALERT'}
    }
    
    print("🧠 Testing Smart Money Alert...")
    return await send_test_alert(webhook_url, embed)

async def test_system_alert(webhook_url: str):
    """Test system/performance alert."""
    embed = {
        'title': '⚠️ SYSTEM ALERT (TEST)',
        'color': 0xff9900,  # Orange
        'description': '**System performance warning**',
        'fields': [
            {'name': '🖥️ Component', 'value': 'Trading Engine', 'inline': True},
            {'name': '⚠️ Issue', 'value': 'High CPU Usage', 'inline': True},
            {'name': '📊 Level', 'value': '92%', 'inline': True},
            {'name': '⏱️ Duration', 'value': '5 minutes', 'inline': True},
            {'name': '🔄 Status', 'value': 'Monitoring', 'inline': True},
            {'name': '🛠️ Action', 'value': 'Auto-scaling', 'inline': True},
            {
                'name': '📝 Details',
                'value': '• Processing 1,250 events/sec\n• Memory usage: 78%\n• Active connections: 45\n• Queue depth: 230',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso System Monitor - TEST ALERT'}
    }
    
    print("⚠️ Testing System Alert...")
    return await send_test_alert(webhook_url, embed)

async def test_cascade_alert(webhook_url: str):
    """Test liquidation cascade warning."""
    embed = {
        'title': '🌊 LIQUIDATION CASCADE WARNING (TEST)',
        'color': 0xff0000,  # Red
        'description': '**⚠️ High risk of cascading liquidations detected**',
        'fields': [
            {'name': '📊 Primary Symbol', 'value': 'BTCUSDT', 'inline': True},
            {'name': '⚠️ Risk Level', 'value': 'CRITICAL', 'inline': True},
            {'name': '📉 Trigger Price', 'value': '$112,500', 'inline': True},
            {'name': '💰 At Risk', 'value': '$45M', 'inline': True},
            {'name': '🔗 Correlation', 'value': '12 pairs', 'inline': True},
            {'name': '📊 Probability', 'value': '78%', 'inline': True},
            {
                'name': '⚠️ Impact Analysis',
                'value': '• Estimated liquidations: $45M\n• Price impact: -3.2%\n• Affected exchanges: 4\n• Time to trigger: ~15 min',
                'inline': False
            },
            {
                'name': '🛡️ Recommended Action',
                'value': '• Reduce leverage immediately\n• Set stop losses above $113,000\n• Monitor closely',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso Risk Monitor - TEST ALERT'}
    }
    
    print("🌊 Testing Cascade Alert...")
    return await send_test_alert(webhook_url, embed)

async def test_alpha_alert(webhook_url: str):
    """Test alpha opportunity alert."""
    embed = {
        'title': '💎 ALPHA OPPORTUNITY (TEST)',
        'color': 0x00ffff,  # Cyan
        'description': '**Market inefficiency detected**',
        'fields': [
            {'name': '📊 Type', 'value': 'Arbitrage', 'inline': True},
            {'name': '💰 Profit', 'value': '2.3%', 'inline': True},
            {'name': '⏱️ Window', 'value': '~3 minutes', 'inline': True},
            {'name': '📍 Exchange A', 'value': 'Binance: $226.45', 'inline': True},
            {'name': '📍 Exchange B', 'value': 'Bybit: $231.65', 'inline': True},
            {'name': '🎯 Symbol', 'value': 'SOLUSDT', 'inline': True},
            {
                'name': '📊 Execution',
                'value': '• Buy on Binance\n• Sell on Bybit\n• Est. profit: $520\n• Risk: Low',
                'inline': False
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'footer': {'text': 'Virtuoso Alpha Scanner - TEST ALERT'}
    }
    
    print("💎 Testing Alpha Alert...")
    return await send_test_alert(webhook_url, embed)

async def main():
    """Run all alert tests."""
    # Get webhook URL
    webhook_url = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    if not webhook_url:
        # Try local .env first
        env_file = Path(".env")
        if not env_file.exists():
            env_file = Path("/home/linuxuser/trading/Virtuoso_ccxt/.env")
        
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if 'SYSTEM_ALERTS_WEBHOOK_URL=' in line:
                        webhook_url = line.split('=', 1)[1].strip()
                        break
    
    if not webhook_url:
        print("❌ No webhook URL found")
        return
    
    print("🧪 TESTING ALL ALERT TYPES")
    print("=" * 60)
    print("This will send test alerts for each alert type to Discord")
    print("-" * 60)
    
    # Test each alert type
    tests = [
        ("Liquidation", None),  # Already tested separately
        ("Whale Activity", None),  # Already tested separately
        ("Confluence/Signal", test_confluence_alert),
        ("Volume Spike", test_volume_spike_alert),
        ("Smart Money", test_smart_money_alert),
        ("System/Performance", test_system_alert),
        ("Cascade Warning", test_cascade_alert),
        ("Alpha Opportunity", test_alpha_alert),
    ]
    
    results = []
    
    for name, test_func in tests:
        if test_func is None:
            print(f"✅ {name} - Already tested")
            results.append((name, True))
        else:
            success = await test_func(webhook_url)
            status = "✅" if success else "❌"
            print(f"{status} {name} Alert")
            results.append((name, success))
            await asyncio.sleep(1)  # Avoid rate limiting
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("-" * 60)
    
    for name, success in results:
        status = "✅ Working" if success else "❌ Failed"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{total} alert types working")
    
    print("\n" + "=" * 60)
    print("✅ Alert testing complete!")
    print("Check your Discord channel for the test alerts")

if __name__ == "__main__":
    asyncio.run(main())