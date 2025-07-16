#!/usr/bin/env python3
"""Check webhook configuration and routing settings."""

import os
import sys
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_webhook_config():
    """Check webhook configuration."""
    print("🔍 Checking Webhook Configuration\n")
    
    # Check environment variables
    print("📋 Environment Variables:")
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    system_webhook = os.getenv('SYSTEM_ALERTS_WEBHOOK_URL')
    
    print(f"DISCORD_WEBHOOK_URL: {'✅ Set' if discord_webhook else '❌ Not set'}")
    if discord_webhook:
        print(f"  Value: {discord_webhook[:50]}...")
    
    print(f"SYSTEM_ALERTS_WEBHOOK_URL: {'✅ Set' if system_webhook else '❌ Not set'}")
    if system_webhook:
        print(f"  Value: {system_webhook[:50]}...")
    
    print()
    
    # Check config file
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.yaml')
    
    if os.path.exists(config_path):
        print("📄 Config File (config.yaml):")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            monitoring_config = config.get('monitoring', {})
            alerts_config = monitoring_config.get('alerts', {})
            system_alerts_config = alerts_config.get('system_alerts', {})
            
            print(f"monitoring.alerts.discord_webhook_url: {alerts_config.get('discord_webhook_url', 'Not set')}")
            print(f"monitoring.alerts.system_alerts_webhook_url: {alerts_config.get('system_alerts_webhook_url', 'Not set')}")
            print()
            
            print("🎯 System Alerts Configuration:")
            print(f"  enabled: {system_alerts_config.get('enabled', False)}")
            print(f"  use_system_webhook: {system_alerts_config.get('use_system_webhook', False)}")
            
            types_config = system_alerts_config.get('types', {})
            print(f"  types.market_report: {types_config.get('market_report', False)}")
            print(f"  types.cpu: {types_config.get('cpu', False)}")
            print(f"  types.memory: {types_config.get('memory', False)}")
            
            mirror_config = system_alerts_config.get('mirror_alerts', {})
            print(f"  mirror_alerts.enabled: {mirror_config.get('enabled', False)}")
            if mirror_config.get('enabled'):
                mirror_types = mirror_config.get('types', {})
                print(f"  mirror_alerts.types.market_report: {mirror_types.get('market_report', False)}")
            
        except Exception as e:
            print(f"❌ Error reading config file: {str(e)}")
    else:
        print("❌ Config file not found")
    
    print()
    
    # Summary
    print("📊 Routing Summary:")
    if discord_webhook and system_webhook:
        print("✅ Both webhook URLs are configured")
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            system_alerts_config = config.get('monitoring', {}).get('alerts', {}).get('system_alerts', {})
            
            if (system_alerts_config.get('use_system_webhook', False) and 
                system_alerts_config.get('types', {}).get('market_report', False)):
                print("✅ Market reports should route to SYSTEM_ALERTS_WEBHOOK_URL")
            else:
                print("⚠️  Market reports will route to DISCORD_WEBHOOK_URL (main webhook)")
                print("   To fix: Set monitoring.alerts.system_alerts.use_system_webhook=true")
                print("   and monitoring.alerts.system_alerts.types.market_report=true")
        except:
            print("❌ Could not determine routing configuration")
    else:
        if not discord_webhook:
            print("❌ DISCORD_WEBHOOK_URL not set")
        if not system_webhook:
            print("❌ SYSTEM_ALERTS_WEBHOOK_URL not set")

if __name__ == "__main__":
    check_webhook_config() 