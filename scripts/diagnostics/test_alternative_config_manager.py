#!/usr/bin/env python3
"""
Test Alternative ConfigManager Environment Variable Substitution

This script tests if the alternative ConfigManager in src/core/config/config_manager.py
also properly substitutes environment variables like ${DISCORD_WEBHOOK_URL} with actual values.
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def test_imports():
    """Test if we can import required modules"""
    try:
        from src.core.config.config_manager import ConfigManager
        from monitoring.alert_manager import AlertManager
        print("✅ Successfully imported alternative ConfigManager and AlertManager")
        return True
    except Exception as e:
        print(f"❌ Failed to import modules: {e}")
        return False

async def test_alternative_config_manager():
    """Test alternative ConfigManager environment variable substitution"""
    print(f"\n{'='*60}")
    print("🧪 TESTING ALTERNATIVE CONFIGMANAGER ENVIRONMENT VARIABLE SUBSTITUTION")
    print(f"{'='*60}")
    
    from src.core.config.config_manager import ConfigManager
    from monitoring.alert_manager import AlertManager
    
    # Check environment variable
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        print(f"✅ DISCORD_WEBHOOK_URL found in environment: {discord_webhook[:20]}...{discord_webhook[-10:]}")
    else:
        print("❌ DISCORD_WEBHOOK_URL not found in environment")
        return False
    
    # Test alternative ConfigManager loading
    print(f"📋 Creating alternative ConfigManager (should process environment variables)...")
    config_manager = ConfigManager()
    
    # Check the config - we need to check the full structure
    print(f"🔍 Checking config structure...")
    if hasattr(config_manager, '_config') and config_manager._config:
        print(f"✅ ConfigManager has config loaded")
        
        # Navigate through the config structure to find Discord webhook URL
        monitoring_config = config_manager._config.get('monitoring', {})
        alerts_config = monitoring_config.get('alerts', {})
        discord_webhook_from_config = alerts_config.get('discord_webhook_url')
        
        print(f"🔍 Webhook URL from alternative ConfigManager: {str(discord_webhook_from_config)[:20]}...{str(discord_webhook_from_config)[-10:] if discord_webhook_from_config else 'None'}")
        
        if discord_webhook_from_config == discord_webhook:
            print("✅ Environment variable properly substituted in alternative ConfigManager!")
        elif discord_webhook_from_config == '${DISCORD_WEBHOOK_URL}':
            print("❌ Environment variable NOT substituted - still literal string")
            return False
        else:
            print(f"⚠️  Unexpected webhook URL value: {discord_webhook_from_config}")
            return False
    else:
        print("❌ ConfigManager config not loaded")
        return False
    
    # Test AlertManager with alternative ConfigManager config
    print(f"📋 Creating AlertManager with alternative ConfigManager config...")
    alert_manager = AlertManager(config_manager._config)
    
    # Check AlertManager webhook URL
    if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
        if alert_manager.discord_webhook_url == discord_webhook:
            print("✅ AlertManager received properly substituted webhook URL from alternative ConfigManager!")
        elif alert_manager.discord_webhook_url == '${DISCORD_WEBHOOK_URL}':
            print("❌ AlertManager still received literal string - substitution failed")
            return False
        else:
            print(f"⚠️  AlertManager webhook URL: {alert_manager.discord_webhook_url[:20]}...{alert_manager.discord_webhook_url[-10:]}")
    else:
        print("❌ AlertManager does not have webhook URL set")
        return False
    
    # Test webhook functionality
    print(f"🚀 Testing webhook sending with alternative ConfigManager...")
    test_message = {
        "content": "🧪 **Alternative ConfigManager Fix Test**\n" +
                  f"Test performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" +
                  "If you see this, environment variable substitution is working in both ConfigManagers!",
        "username": "Virtuoso Alt Config Test"
    }
    
    try:
        await alert_manager.send_discord_webhook_message(test_message)
        print("✅ Webhook test successful with alternative ConfigManager! Check your Discord channel.")
        return True
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🔧 Alternative ConfigManager Environment Variable Substitution Test")
    print("This tests if our fix for environment variable substitution works in the alternative ConfigManager")
    
    # Test imports
    if not test_imports():
        print("❌ Cannot proceed - import errors")
        return
    
    # Test alternative ConfigManager environment variable substitution
    success = await test_alternative_config_manager()
    
    if success:
        print(f"\n🎉 SUCCESS! Environment variable substitution is working in both ConfigManagers!")
        print(f"All parts of your system should now work with Discord notifications.")
    else:
        print(f"\n❌ FAILED! Environment variable substitution is not working in the alternative ConfigManager.")
        print(f"Further investigation may be needed.")

if __name__ == "__main__":
    asyncio.run(main()) 