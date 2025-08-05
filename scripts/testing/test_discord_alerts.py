#!/usr/bin/env python3
"""
Test Discord Alert Functionality
Quick test to verify Discord webhooks are working
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

async def test_discord_alerts():
    """Test Discord alert functionality"""
    print("🧪 Testing Discord Alert Functionality")
    print("=" * 50)
    
    try:
        # Import alert manager
        from monitoring.alert_manager import AlertManager
        
        # Create basic config for alert manager
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook': {
                        'max_retries': 3,
                        'timeout_seconds': 30,
                        'exponential_backoff': True
                    }
                }
            }
        }
        
        # Initialize alert manager
        print("📡 Initializing Alert Manager...")
        alert_manager = AlertManager(config)
        
        # Test basic alert
        print("📤 Sending test market report alert to Discord...")
        
        test_message = {
            "title": "🧪 Test Market Report Alert",
            "description": "This is a test alert to verify Discord integration is working",
            "fields": [
                {
                    "name": "Market Regime",
                    "value": "📈 Bullish Test",
                    "inline": True
                },
                {
                    "name": "Test Signal Score",
                    "value": "75.0%",
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "✅ Testing Discord Integration",
                    "inline": False
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "color": 0x00ff00  # Green color
        }
        
        # Send the test alert
        success = await alert_manager.send_discord_webhook_message(test_message)
        
        if success:
            print("✅ Discord alert sent successfully!")
            print("   Check your Discord channel for the test message")
        else:
            print("❌ Discord alert failed to send")
            print("   Check your webhook URL and network connection")
            
        return success
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Alert manager may not be available")
        return False
        
    except Exception as e:
        print(f"❌ Error testing Discord alerts: {e}")
        return False

async def test_market_report_discord():
    """Test market report specific Discord functionality"""
    print("\n🧪 Testing Market Report Discord Integration")
    print("=" * 50)
    
    try:
        from monitoring.market_reporter import MarketReporter
        
        # Create basic config for alert manager
        config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook': {
                        'max_retries': 3,
                        'timeout_seconds': 30,
                        'exponential_backoff': True
                    }
                }
            }
        }
        
        # Create mock alert manager
        alert_manager = AlertManager(config)
        
        # Create sample market report data
        sample_report = {
            'market_overview': {
                'regime': '📈 Test Bullish',
                'trend_strength': 75.0,
                'total_volume': 1500000000,
                'bullish_symbols': 8,
                'bearish_symbols': 2
            },
            'smart_money_index': {
                'index': 65.0,
                'signal': 'BULLISH',
                'change': 2.5
            },
            'whale_activity': {
                'transactions': [
                    {'symbol': 'BTCUSDT', 'side': 'buy', 'usd_value': 2000000}
                ]
            },
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        
        # Initialize market reporter with alert manager
        reporter = MarketReporter(alert_manager=alert_manager)
        
        # Test market report formatting for Discord
        print("📊 Formatting test market report for Discord...")
        
        formatted_report = await reporter.format_market_report(
            overview=sample_report['market_overview'],
            top_pairs=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            market_regime=sample_report['market_overview']['regime'],
            smart_money=sample_report['smart_money_index'],
            whale_activity=sample_report['whale_activity']
        )
        
        if formatted_report and 'embeds' in formatted_report:
            print(f"✅ Market report formatted successfully!")
            print(f"   - Number of embeds: {len(formatted_report['embeds'])}")
            print(f"   - Content length: {len(formatted_report.get('content', ''))}")
            
            # Send the formatted report
            print("📤 Sending formatted market report to Discord...")
            success = await alert_manager.send_discord_webhook_message(formatted_report)
            
            if success:
                print("✅ Market report sent to Discord successfully!")
                print("   Check your Discord channel for the market report")
            else:
                print("❌ Failed to send market report to Discord")
                
            return success
        else:
            print("❌ Failed to format market report")
            return False
            
    except Exception as e:
        print(f"❌ Error testing market report Discord: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_discord_config():
    """Check Discord configuration"""
    print("\n🔧 Checking Discord Configuration")
    print("=" * 50)
    
    # Check environment variables
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    system_webhook = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    print(f"Discord Webhook URL: {'✅ Set' if discord_webhook else '❌ Not set'}")
    print(f"System Alerts Webhook: {'✅ Set' if system_webhook else '❌ Not set'}")
    
    if discord_webhook:
        print(f"   URL preview: {discord_webhook[:50]}...")
    
    if system_webhook:
        print(f"   System URL preview: {system_webhook[:50]}...")
    
    # Check if URLs look valid
    valid_webhooks = 0
    if discord_webhook and 'discord.com/api/webhooks' in discord_webhook:
        print("✅ Discord webhook URL format looks valid")
        valid_webhooks += 1
    elif discord_webhook:
        print("⚠️ Discord webhook URL format may be incorrect")
    
    if system_webhook and 'discord.com/api/webhooks' in system_webhook:
        print("✅ System webhook URL format looks valid")
        valid_webhooks += 1
    elif system_webhook:
        print("⚠️ System webhook URL format may be incorrect")
    
    return valid_webhooks > 0

async def main():
    """Main test function"""
    print("🚀 Discord Alert System Test Suite")
    print("=" * 60)
    
    # Set up logging
    logging.basicConfig(level=logging.WARNING)
    
    # Test configuration
    config_ok = await check_discord_config()
    
    if not config_ok:
        print("\n❌ Discord configuration issues detected!")
        print("   Please check your DISCORD_WEBHOOK_URL environment variable")
        return
    
    # Test basic alerts
    basic_test = await test_discord_alerts()
    
    # Test market report alerts
    market_test = await test_market_report_discord()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Discord Alert Test Summary")
    print("=" * 60)
    
    print(f"Configuration: {'✅ OK' if config_ok else '❌ Failed'}")
    print(f"Basic Alert Test: {'✅ Passed' if basic_test else '❌ Failed'}")
    print(f"Market Report Test: {'✅ Passed' if market_test else '❌ Failed'}")
    
    if basic_test and market_test:
        print("\n🎉 All Discord alert tests passed!")
        print("   Your Discord integration is working correctly")
        print("   Market reports should be sent to Discord when conditions are met")
    else:
        print("\n⚠️ Some Discord tests failed")
        print("   Check your Discord webhook configuration and network connection")

if __name__ == "__main__":
    asyncio.run(main())