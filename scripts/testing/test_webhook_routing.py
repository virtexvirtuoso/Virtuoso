#!/usr/bin/env python3
"""
Test script to verify webhook routing configuration.
This script tests that system alerts are properly routed to SYSTEM_ALERTS_WEBHOOK_URL
instead of DISCORD_WEBHOOK_URL.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from src.core.config.config_manager import ConfigManager
from src.monitoring.alert_manager import AlertManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_status(description: str, status: bool, details: str = ""):
    """Print status with emoji indicators."""
    emoji = "✅" if status else "❌"
    print(f"{emoji} {description}: {details}")

async def test_webhook_routing():
    """Test webhook routing configuration."""
    print("🔍 Testing Webhook Routing Configuration\n")
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    print("📋 Environment Variables:")
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    system_webhook = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    print_status("DISCORD_WEBHOOK_URL", bool(discord_webhook), 
                f"{'Set' if discord_webhook else 'Not set'}")
    print_status("SYSTEM_ALERTS_WEBHOOK_URL", bool(system_webhook), 
                f"{'Set' if system_webhook else 'Not set'}")
    
    if not system_webhook:
        print("\n❌ SYSTEM_ALERTS_WEBHOOK_URL is not set. Please set it in your .env file:")
        print("SYSTEM_ALERTS_WEBHOOK_URL=https://discord.com/api/webhooks/your-system-webhook-url")
        return False
    
    print()
    
    # Load configuration
    try:
        config_manager = ConfigManager()
        config = config_manager._config
        print_status("Configuration loading", True, "Loaded successfully")
    except Exception as e:
        print_status("Configuration loading", False, f"Error: {str(e)}")
        return False
    
    # Check system alerts configuration
    print("\n🎯 System Alerts Configuration:")
    system_alerts_config = config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})
    cpu_alerts_config = config.get('monitoring', {}).get('alerts', {}).get('cpu_alerts', {})
    
    print_status("system_alerts.enabled", 
                system_alerts_config.get('enabled', False), 
                str(system_alerts_config.get('enabled', False)))
    print_status("system_alerts.use_system_webhook", 
                system_alerts_config.get('use_system_webhook', False), 
                str(system_alerts_config.get('use_system_webhook', False)))
    print_status("cpu_alerts.use_system_webhook", 
                cpu_alerts_config.get('use_system_webhook', False), 
                str(cpu_alerts_config.get('use_system_webhook', False)))
    print_status("system_alerts.types.cpu", 
                system_alerts_config.get('types', {}).get('cpu', False), 
                str(system_alerts_config.get('types', {}).get('cpu', False)))
    
    # Check system webhook URL configuration
    system_webhook_url_config = config.get('monitoring', {}).get('alerts', {}).get('system_alerts_webhook_url', '')
    print_status("system_alerts_webhook_url in config", 
                bool(system_webhook_url_config), 
                f"Value: {system_webhook_url_config}")
    
    print()
    
    # Test AlertManager initialization
    print("🧪 Testing AlertManager:")
    try:
        alert_manager = AlertManager(config)
        print_status("AlertManager creation", True, "Successfully created")
        
        # Check webhook URLs
        discord_url_loaded = bool(alert_manager.discord_webhook_url)
        system_url_loaded = bool(alert_manager.system_webhook_url)
        
        print_status("Discord webhook URL loaded", discord_url_loaded, 
                    f"Length: {len(alert_manager.discord_webhook_url) if discord_url_loaded else 0}")
        print_status("System webhook URL loaded", system_url_loaded, 
                    f"Length: {len(alert_manager.system_webhook_url) if system_url_loaded else 0}")
        
        if discord_url_loaded:
            print(f"  Discord URL starts with: {alert_manager.discord_webhook_url[:50]}...")
        if system_url_loaded:
            print(f"  System URL starts with: {alert_manager.system_webhook_url[:50]}...")
            
    except Exception as e:
        print_status("AlertManager creation", False, f"Error: {str(e)}")
        return False
    
    print()
    
    # Test CPU alert routing
    print("🚨 Testing CPU Alert Routing:")
    try:
        # Test CPU alert details
        test_details = {
            'type': 'cpu',
            'value': 99.8,
            'threshold': 90.0,
            'source': 'system'
        }
        
        # Send a test CPU alert
        await alert_manager.send_alert(
            level="warning",
            message="High cpu_usage value 99.8 threshold 90.0",
            details=test_details,
            throttle=False
        )
        
        print_status("CPU alert sent", True, "Alert dispatched successfully")
        
    except Exception as e:
        print_status("CPU alert sending", False, f"Error: {str(e)}")
        return False
    
    print()
    
    # Summary
    print("📊 Routing Summary:")
    if system_url_loaded and (system_alerts_config.get('use_system_webhook', False) or cpu_alerts_config.get('use_system_webhook', False)):
        print("✅ CPU alerts should route to SYSTEM_ALERTS_WEBHOOK_URL")
    else:
        print("⚠️  CPU alerts will route to DISCORD_WEBHOOK_URL (main webhook)")
        print("   Configuration issue detected!")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_webhook_routing()) 