#!/usr/bin/env python3
"""
Discord Notification Diagnostic Script

This script will diagnose why Discord notifications are not being sent
and provide step-by-step instructions to fix the issue.
"""

import os
import sys
import asyncio
import logging
import yaml
import json
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from monitoring.alert_manager import AlertManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_status(check_name, status, details=None):
    """Print a formatted status line"""
    emoji = "✅" if status else "❌"
    print(f"{emoji} {check_name}")
    if details:
        print(f"   📝 {details}")

async def main():
    """Main diagnostic function"""
    print_header("DISCORD NOTIFICATION DIAGNOSTIC")
    print("This script will help identify why Discord notifications aren't working.\n")
    
    issues_found = []
    fixes_needed = []
    
    # 1. Check environment variable
    print_header("STEP 1: Environment Variable Check")
    
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        print_status("DISCORD_WEBHOOK_URL environment variable", True, 
                    f"Found (length: {len(discord_webhook)})")
        
        # Validate URL format
        if discord_webhook.startswith('https://discord.com/api/webhooks/'):
            print_status("Webhook URL format", True, "Valid Discord webhook URL format")
        else:
            print_status("Webhook URL format", False, 
                        f"Invalid format: {discord_webhook[:50]}...")
            issues_found.append("Invalid Discord webhook URL format")
            fixes_needed.append("Obtain a valid Discord webhook URL from your Discord server")
    else:
        print_status("DISCORD_WEBHOOK_URL environment variable", False, "Not set")
        issues_found.append("DISCORD_WEBHOOK_URL environment variable not set")
        fixes_needed.append("Set the DISCORD_WEBHOOK_URL environment variable")
    
    # 2. Check config file
    print_header("STEP 2: Configuration File Check")
    
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print_status("Config file loaded", True, f"From {config_path}")
        
        # Check monitoring.alerts section
        monitoring_config = config.get('monitoring', {})
        alerts_config = monitoring_config.get('alerts', {})
        
        if alerts_config:
            print_status("Alerts configuration section", True, "Found in config")
            
            # Check various webhook URL configurations
            webhook_configs = [
                ('discord_webhook_url', alerts_config.get('discord_webhook_url')),
                ('discord.webhook_url', alerts_config.get('discord', {}).get('webhook_url')),
                ('discord_network', alerts_config.get('discord_network'))
            ]
            
            for config_key, config_value in webhook_configs:
                if config_value:
                    print_status(f"Config key: {config_key}", True, f"Value: {str(config_value)[:50]}...")
                else:
                    print_status(f"Config key: {config_key}", False, "Not configured")
        else:
            print_status("Alerts configuration section", False, "Missing from config")
            issues_found.append("Missing alerts configuration in config.yaml")
            
    except Exception as e:
        print_status("Config file loading", False, f"Error: {str(e)}")
        issues_found.append(f"Config file error: {str(e)}")
    
    # 3. Test AlertManager initialization
    print_header("STEP 3: AlertManager Initialization Test")
    
    try:
        # Create test config
        test_config = {
            'monitoring': {
                'alerts': {
                    'discord_webhook_url': discord_webhook or 'https://example.com/webhook',
                    'thresholds': {
                        'buy': 65,
                        'sell': 35
                    }
                }
            }
        }
        
        alert_manager = AlertManager(test_config)
        print_status("AlertManager creation", True, "Successfully created")
        
        # Check if webhook URL is set
        if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
            print_status("Discord webhook URL in AlertManager", True, 
                        f"Set (length: {len(alert_manager.discord_webhook_url)})")
        else:
            print_status("Discord webhook URL in AlertManager", False, "Not set")
            issues_found.append("AlertManager discord_webhook_url not set")
        
        # Check handlers
        handlers = getattr(alert_manager, 'handlers', {})
        if 'discord' in handlers:
            print_status("Discord handler registered", True, "Handler is active")
        else:
            print_status("Discord handler registered", False, "Handler not found")
            issues_found.append("Discord handler not registered")
            
    except Exception as e:
        print_status("AlertManager creation", False, f"Error: {str(e)}")
        issues_found.append(f"AlertManager initialization error: {str(e)}")
    
    # 4. Test webhook connectivity (if URL available)
    if discord_webhook and discord_webhook.startswith('https://discord.com/api/webhooks/'):
        print_header("STEP 4: Webhook Connectivity Test")
        
        try:
            # Create a test message
            test_message = {
                "content": "🔧 **Discord Webhook Test**\n" +
                          f"Test performed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" +
                          "If you see this message, your webhook is working correctly!",
                "username": "Virtuoso Diagnostics"
            }
            
            # Test sending
            await alert_manager.send_discord_webhook_message(test_message)
            print_status("Test message sent", True, "Check your Discord channel for the test message")
            
        except Exception as e:
            print_status("Test message sent", False, f"Error: {str(e)}")
            issues_found.append(f"Webhook test failed: {str(e)}")
    
    # 5. Summary and recommendations
    print_header("DIAGNOSTIC SUMMARY")
    
    if not issues_found:
        print("🎉 No issues found! Your Discord notifications should be working.")
        print("\nIf you're still not receiving signals, check:")
        print("   • Your signal thresholds (buy/sell limits)")
        print("   • That signals are actually being generated")
        print("   • Discord server permissions for the webhook")
    else:
        print(f"❌ Found {len(issues_found)} issue(s):")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
    
    print_header("RECOMMENDED FIXES")
    
    if not discord_webhook:
        print("""
📋 HOW TO GET A DISCORD WEBHOOK URL:

1. Open your Discord server
2. Go to Server Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Choose the channel where you want signals
5. Copy the webhook URL
6. Set it as an environment variable:

   For Linux/macOS:
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
   
   For Windows:
   set DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
   
   Or add it to your .env file:
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
""")
    
    if fixes_needed:
        print("\n🔧 SPECIFIC FIXES NEEDED:")
        for i, fix in enumerate(fixes_needed, 1):
            print(f"   {i}. {fix}")
    
    # 6. Create a fix script
    print_header("AUTOMATED FIX")
    
    fix_script_path = Path(__file__).parent / "fix_discord_notifications.py"
    fix_script_content = f'''#!/usr/bin/env python3
"""
Automated Discord Notification Fix Script
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import os
import sys

def main():
    print("🔧 Discord Notification Fix Script")
    print("This script will help you set up Discord notifications.")
    
    webhook_url = input("\\nPlease enter your Discord webhook URL: ").strip()
    
    if not webhook_url.startswith('https://discord.com/api/webhooks/'):
        print("❌ Invalid webhook URL format!")
        print("Expected format: https://discord.com/api/webhooks/...")
        return
    
    # Set environment variable
    os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
    
    # Add to .env file
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    try:
        with open(env_file, 'a') as f:
            f.write(f"\\nDISCORD_WEBHOOK_URL={webhook_url}\\n")
        print(f"✅ Added to .env file: {env_file}")
    except Exception as e:
        print(f"⚠️  Could not write to .env file: {e}")
    
    print("\\n✅ Discord webhook URL configured!")
    print("Please restart your trading system for changes to take effect.")
    
    # Test the webhook
    test = input("\\nTest the webhook now? (y/n): ").strip().lower()
    if test == 'y':
        try:
            import asyncio
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
            from monitoring.alert_manager import AlertManager
            
            config = {{
                'monitoring': {{
                    'alerts': {{
                        'discord_webhook_url': webhook_url,
                        'thresholds': {{'buy': 65, 'sell': 35}}
                    }}
                }}
            }}
            
            async def test_webhook():
                alert_manager = AlertManager(config)
                await alert_manager.send_discord_webhook_message({{
                    "content": "🎉 Discord notifications are now working!",
                    "username": "Virtuoso Trading"
                }})
                print("✅ Test message sent! Check your Discord channel.")
            
            asyncio.run(test_webhook())
            
        except Exception as e:
            print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open(fix_script_path, 'w') as f:
            f.write(fix_script_content)
        print(f"📝 Created automated fix script: {fix_script_path}")
        print(f"   Run with: python {fix_script_path}")
    except Exception as e:
        print(f"⚠️  Could not create fix script: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 