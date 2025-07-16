#!/usr/bin/env python3
"""
Test script to verify SignalGenerator AlertManager initialization fix.
"""

import os
import sys
import yaml
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.signal_generation.signal_generator import SignalGenerator

def main():
    """Test SignalGenerator AlertManager initialization."""
    print("Testing SignalGenerator AlertManager initialization fix...")
    
    # Load environment variables
    load_dotenv()
    
    # Load config
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"Environment DISCORD_WEBHOOK_URL: {repr(os.getenv('DISCORD_WEBHOOK_URL'))}")
    print(f"Config discord_webhook_url: {repr(config.get('monitoring', {}).get('alerts', {}).get('discord_webhook_url'))}")
    
    # Test SignalGenerator initialization
    print("\nInitializing SignalGenerator...")
    signal_generator = SignalGenerator(config)
    
    # Check AlertManager
    if signal_generator.alert_manager:
        print("✅ SignalGenerator has AlertManager")
        print(f"AlertManager discord_webhook_url: {repr(signal_generator.alert_manager.discord_webhook_url)}")
        print(f"AlertManager discord_webhook_url bool: {bool(signal_generator.alert_manager.discord_webhook_url)}")
        
        if signal_generator.alert_manager.discord_webhook_url:
            print("✅ SUCCESS: SignalGenerator's AlertManager has Discord webhook URL")
            print(f"URL preview: {signal_generator.alert_manager.discord_webhook_url[:30]}...{signal_generator.alert_manager.discord_webhook_url[-20:]}")
        else:
            print("❌ FAILED: SignalGenerator's AlertManager does not have Discord webhook URL")
        
        # Test handlers
        print(f"Registered handlers: {signal_generator.alert_manager.handlers}")
        print(f"Alert handlers: {list(signal_generator.alert_manager.alert_handlers.keys()) if hasattr(signal_generator.alert_manager, 'alert_handlers') else 'N/A'}")
    else:
        print("❌ FAILED: SignalGenerator does not have AlertManager")

if __name__ == "__main__":
    main() 