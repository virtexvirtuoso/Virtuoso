#!/usr/bin/env python3
"""
Discord Webhook Diagnostic Script

This script tests the Discord webhook configuration and identifies common issues
that might prevent alerts from being sent successfully.
"""

import os
import sys
import asyncio
import logging
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.monitoring.alert_manager import AlertManager
from src.core.config.config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_webhook_test')

def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_status(item: str, status: bool, details: str = ""):
    """Print status with color coding."""
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {item}: {details}")

async def test_discord_webhook():
    """Test Discord webhook configuration and functionality."""
    
    print_header("DISCORD WEBHOOK DIAGNOSTIC TEST")
    
    issues_found = []
    
    # 1. Check environment variables
    print_header("STEP 1: Environment Variable Check")
    
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        print_status("DISCORD_WEBHOOK_URL environment variable", True, f"Found (length: {len(discord_webhook)})")
        print_status("Webhook URL format", discord_webhook.startswith('https://discord'), 
                    f"Starts with: {discord_webhook[:50]}...")
    else:
        print_status("DISCORD_WEBHOOK_URL environment variable", False, "Not found")
        issues_found.append("DISCORD_WEBHOOK_URL environment variable not set")
    
    # 2. Load configuration
    print_header("STEP 2: Configuration Loading")
    
    try:
        config_manager = ConfigManager()
        config = config_manager._config  # Access the loaded config directly
        print_status("Configuration loading", True, "Config loaded successfully")
        
        # Check monitoring.alerts section
        monitoring_config = config.get('monitoring', {})
        alerts_config = monitoring_config.get('alerts', {})
        
        if alerts_config:
            print_status("Alerts configuration section", True, "Found in config")
            
            # Check webhook URL in config
            config_webhook = alerts_config.get('discord_webhook_url')
            if config_webhook:
                print_status("discord_webhook_url in config", True, f"Found (length: {len(config_webhook)})")
            else:
                print_status("discord_webhook_url in config", False, "Not configured")
                
        else:
            print_status("Alerts configuration section", False, "Missing from config")
            issues_found.append("Missing alerts configuration in config")
            
    except Exception as e:
        print_status("Configuration loading", False, f"Error: {str(e)}")
        issues_found.append(f"Config loading error: {str(e)}")
        return
    
    # 3. Test AlertManager initialization
    print_header("STEP 3: AlertManager Initialization")
    
    try:
        alert_manager = AlertManager(config)
        print_status("AlertManager creation", True, "Successfully created")
        
        # Check webhook URL
        if hasattr(alert_manager, 'discord_webhook_url') and alert_manager.discord_webhook_url:
            webhook_url = alert_manager.discord_webhook_url
            print_status("Discord webhook URL loaded", True, f"Length: {len(webhook_url)}")
            print_status("Webhook URL format", webhook_url.startswith('https://discord'), 
                        f"Starts with: {webhook_url[:50]}...")
            
            # Test URL validation
            if hasattr(alert_manager, '_validate_discord_webhook_url'):
                is_valid = alert_manager._validate_discord_webhook_url(webhook_url)
                print_status("Webhook URL validation", is_valid, 
                           "Passed validation" if is_valid else "Failed validation")
                if not is_valid:
                    issues_found.append("Discord webhook URL failed validation")
            else:
                print_status("Webhook URL validation method", False, "Method not found")
                
        else:
            print_status("Discord webhook URL loaded", False, "Not loaded or empty")
            issues_found.append("Discord webhook URL not loaded in AlertManager")
        
        # Check handlers
        handlers = getattr(alert_manager, 'handlers', [])
        if 'discord' in handlers:
            print_status("Discord handler registered", True, "Handler is active")
        else:
            print_status("Discord handler registered", False, "Handler not found")
            issues_found.append("Discord handler not registered")
            
        # Check retry configuration
        max_retries = getattr(alert_manager, 'webhook_max_retries', 0)
        print_status("Webhook max retries", max_retries > 0, f"Set to: {max_retries}")
        if max_retries <= 0:
            issues_found.append(f"Webhook max retries is too low: {max_retries}")
            
    except Exception as e:
        print_status("AlertManager creation", False, f"Error: {str(e)}")
        issues_found.append(f"AlertManager initialization error: {str(e)}")
        logger.error(traceback.format_exc())
        return
    
    # 4. Test webhook sending
    print_header("STEP 4: Webhook Sending Test")
    
    if alert_manager.discord_webhook_url and 'discord' in alert_manager.handlers:
        try:
            # Create a test alert
            test_alert = {
                'level': 'INFO',
                'message': '🧪 Discord Webhook Test - Alert Manager Diagnostic',
                'details': {
                    'type': 'diagnostic_test',
                    'timestamp': '2025-01-10 19:12:24',
                    'test_id': 'webhook_diagnostic_001',
                    'status': 'Testing webhook functionality'
                },
                'timestamp': asyncio.get_event_loop().time()
            }
            
            print_status("Sending test alert", True, "Attempting to send...")
            
            # Send the test alert
            await alert_manager._send_discord_alert(test_alert)
            
            # Check if it was successful (based on stats)
            sent_count = alert_manager._alert_stats.get('sent', 0)
            error_count = alert_manager._alert_stats.get('errors', 0)
            
            if sent_count > 0:
                print_status("Test alert sent", True, f"Successfully sent (sent: {sent_count}, errors: {error_count})")
            else:
                print_status("Test alert sent", False, f"Failed to send (sent: {sent_count}, errors: {error_count})")
                issues_found.append("Test alert failed to send")
                
        except Exception as e:
            print_status("Test alert sending", False, f"Error: {str(e)}")
            issues_found.append(f"Test alert error: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        print_status("Test alert sending", False, "Skipped - webhook not configured or handler not registered")
    
    # 5. Summary
    print_header("DIAGNOSTIC SUMMARY")
    
    if not issues_found:
        print_status("Overall Status", True, "All tests passed! Discord webhook should be working.")
    else:
        print_status("Overall Status", False, f"Found {len(issues_found)} issues")
        print("\n🔧 ISSUES TO FIX:")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
        
        print("\n💡 RECOMMENDED ACTIONS:")
        if "DISCORD_WEBHOOK_URL environment variable not set" in issues_found:
            print("   • Set DISCORD_WEBHOOK_URL in your .env file")
            print("   • Format: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN")
        
        if any("validation" in issue.lower() for issue in issues_found):
            print("   • Check that your Discord webhook URL is properly formatted")
            print("   • Ensure it starts with https://discord.com/api/webhooks/")
            print("   • Verify the webhook ID and token are present")
        
        if any("retry" in issue.lower() for issue in issues_found):
            print("   • Check webhook retry configuration in config.yaml")
            print("   • Ensure monitoring.alerts.discord_webhook.max_retries > 0")
    
    print_header("TEST COMPLETE")

if __name__ == "__main__":
    try:
        asyncio.run(test_discord_webhook())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        logger.error(traceback.format_exc()) 