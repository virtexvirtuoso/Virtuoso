#!/usr/bin/env python3
"""
Test script to verify AlertManager Discord webhook URL loading fix.
"""

import os
import sys
import yaml
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.monitoring.alert_manager import AlertManager

def main():
    """Test AlertManager Discord webhook URL loading."""
    print("Testing AlertManager Discord webhook URL loading fix...")
    
    # Load environment variables
    load_dotenv()
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Environment DISCORD_WEBHOOK_URL: {repr(os.getenv('DISCORD_WEBHOOK_URL'))}")
    print(f"Config discord_webhook_url: {repr(config.get('monitoring', {}).get('alerts', {}).get('discord_webhook_url'))}")
    
    # Test AlertManager initialization
    print("\nInitializing AlertManager...")
    alert_manager = AlertManager(config)
    
    print(f"AlertManager discord_webhook_url: {repr(alert_manager.discord_webhook_url)}")
    print(f"AlertManager discord_webhook_url length: {len(alert_manager.discord_webhook_url) if alert_manager.discord_webhook_url else 0}")
    print(f"AlertManager discord_webhook_url bool: {bool(alert_manager.discord_webhook_url)}")
    
    if alert_manager.discord_webhook_url:
        print("✅ SUCCESS: AlertManager properly loaded Discord webhook URL")
        print(f"URL preview: {alert_manager.discord_webhook_url[:30]}...{alert_manager.discord_webhook_url[-20:]}")
    else:
        print("❌ FAILED: AlertManager did not load Discord webhook URL")
    
    # Test handlers
    print(f"\nRegistered handlers: {alert_manager.handlers}")
    print(f"Alert handlers: {list(alert_manager.alert_handlers.keys()) if hasattr(alert_manager, 'alert_handlers') else 'N/A'}")

if __name__ == "__main__":
    main() 