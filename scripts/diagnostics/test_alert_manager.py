#!/usr/bin/env python3
"""
AlertManager Signal Test

This script tests the exact signal alert flow that should have triggered
for your SUIUSDT signal.
"""

import os
import sys
import asyncio
import yaml
import json
from pathlib import Path
from datetime import datetime

# Add src to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def test_imports():
    """Test if we can import required modules"""
    try:
        from monitoring.alert_manager import AlertManager
        print("✅ Successfully imported AlertManager")
        return True
    except Exception as e:
        print(f"❌ Failed to import AlertManager: {e}")
        return False

async def test_signal_alert():
    """Test the exact signal that should have been sent"""
    print(f"\n{'='*60}")
    print("🧪 TESTING ALERT MANAGER SIGNAL FLOW")
    print(f"{'='*60}")
    
    # Import modules
    from monitoring.alert_manager import AlertManager
    
    # Load config
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"📋 Loaded config from {config_path}")
    
    # Initialize AlertManager
    alert_manager = AlertManager(config)
    print(f"✅ Created AlertManager")
    
    # Check AlertManager state
    print(f"🔍 AlertManager webhook URL set: {bool(getattr(alert_manager, 'discord_webhook_url', None))}")
    print(f"🔍 AlertManager handlers: {getattr(alert_manager, 'handlers', {})}")
    
    # Create test signal data that matches your SUIUSDT signal
    signal_data = {
        'symbol': 'SUIUSDT',
        'confluence_score': 69.30,  # Your actual score
        'signal_type': 'BUY',       # Your actual signal type
        'components': {
            'technical': 64.47,
            'volume': 63.96,
            'orderbook': 82.37,
            'orderflow': 83.91,
            'sentiment': 46.66,
            'price_structure': 52.34
        },
        'results': {
            'technical': {'score': 64.47},
            'volume': {'score': 63.96},
            'orderbook': {'score': 82.37},
            'orderflow': {'score': 83.91},
            'sentiment': {'score': 46.66},
            'price_structure': {'score': 52.34}
        },
        'weights': {
            'technical': 0.167,
            'volume': 0.167,
            'orderbook': 0.167,
            'orderflow': 0.167,
            'sentiment': 0.167,
            'price_structure': 0.167
        },
        'reliability': 1.0,
        'price': 3.67,
        'buy_threshold': 68.0,
        'sell_threshold': 35.0,
        'transaction_id': 'test-90a32283',
        'signal_id': 'test-edbceb7e',
        'timestamp': int(datetime.now().timestamp() * 1000),
        # Add market interpretations like in your logs
        'market_interpretations': [
            {
                'component': 'orderflow',
                'display_name': 'Orderflow',
                'interpretation': 'Extremely strong bullish orderflow indicating aggressive buying pressure'
            },
            {
                'component': 'orderbook',
                'display_name': 'Orderbook', 
                'interpretation': 'Strong bid-side dominance with high liquidity and tight spreads'
            },
            {
                'component': 'technical',
                'display_name': 'Technical',
                'interpretation': 'Technical indicators show slight bullish bias within overall neutrality'
            }
        ],
        'actionable_insights': [
            'BULLISH BIAS: Overall confluence score (69.30) above buy threshold (65)',
            'RISK ASSESSMENT: HIGH - Reduce position size despite bullish bias',
            'TIMING: Strong buying pressure; favorable timing for bullish strategies'
        ]
    }
    
    print(f"📊 Created test signal data for {signal_data['symbol']}")
    print(f"   Score: {signal_data['confluence_score']}")
    print(f"   Signal: {signal_data['signal_type']}")
    print(f"   Price: ${signal_data['price']}")
    
    # Test send_signal_alert method
    print(f"\n🚀 Testing send_signal_alert...")
    
    try:
        await alert_manager.send_signal_alert(signal_data)
        print(f"✅ send_signal_alert completed without errors!")
        print(f"🔔 Check your Discord channel for the notification")
        
    except Exception as e:
        print(f"❌ send_signal_alert failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_direct_webhook():
    """Test direct webhook sending"""
    print(f"\n{'='*60}")
    print("🧪 TESTING DIRECT WEBHOOK")
    print(f"{'='*60}")
    
    from monitoring.alert_manager import AlertManager
    
    # Load config
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    alert_manager = AlertManager(config)
    
    # Create simple test message
    test_message = {
        "content": "🧪 **Direct Webhook Test**\n" +
                  f"Test performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" +
                  "This tests if the webhook URL itself is working.",
        "username": "Virtuoso Test Bot"
    }
    
    try:
        await alert_manager.send_discord_webhook_message(test_message)
        print("✅ Direct webhook test successful!")
        return True
    except Exception as e:
        print(f"❌ Direct webhook test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🔬 AlertManager Signal Test")
    print("This will test the exact signal flow that should have worked for SUIUSDT")
    
    # Test imports
    if not test_imports():
        print("❌ Cannot proceed - import errors")
        return
    
    # Test direct webhook first
    print("\n" + "="*60)
    print("PHASE 1: Testing direct webhook connectivity")
    webhook_works = await test_direct_webhook()
    
    if not webhook_works:
        print("❌ Direct webhook failed - check your Discord webhook URL")
        return
    
    # Test signal alert
    print("\n" + "="*60)
    print("PHASE 2: Testing signal alert flow")
    signal_works = await test_signal_alert()
    
    if signal_works:
        print(f"\n🎉 All tests passed!")
        print(f"Your Discord notifications should now be working.")
        print(f"If you didn't receive the test messages, check:")
        print(f"   • Discord channel permissions")
        print(f"   • Webhook is still active")
        print(f"   • Network connectivity")
    else:
        print(f"\n❌ Signal alert test failed")
        print(f"There may be an issue with the AlertManager logic")

if __name__ == "__main__":
    asyncio.run(main()) 