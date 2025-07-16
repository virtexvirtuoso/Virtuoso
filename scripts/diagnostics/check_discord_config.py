#!/usr/bin/env python3
"""
Simple Discord Configuration Checker

This script checks if Discord webhook is properly configured.
"""

import os
import yaml
import sys
from pathlib import Path

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

def main():
    """Main diagnostic function"""
    print_header("DISCORD CONFIGURATION CHECK")
    print("Checking why Discord notifications aren't working...\n")
    
    issues_found = []
    
    # 1. Check environment variable
    print_header("STEP 1: Environment Variable Check")
    
    discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
    if discord_webhook:
        print_status("DISCORD_WEBHOOK_URL found", True, f"Length: {len(discord_webhook)}")
        
        # Validate URL format
        if discord_webhook.startswith('https://discord.com/api/webhooks/'):
            print_status("Webhook URL format", True, "Valid Discord webhook URL")
        else:
            print_status("Webhook URL format", False, f"Invalid format: {discord_webhook[:50]}...")
            issues_found.append("Invalid Discord webhook URL format")
    else:
        print_status("DISCORD_WEBHOOK_URL found", False, "Not set in environment")
        issues_found.append("DISCORD_WEBHOOK_URL environment variable not set")
    
    # 2. Check .env file
    print_header("STEP 2: .env File Check")
    
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        print_status(".env file exists", True, f"Found at {env_file}")
        
        try:
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            if 'DISCORD_WEBHOOK_URL' in env_content:
                print_status("DISCORD_WEBHOOK_URL in .env", True, "Found in .env file")
                
                # Extract the URL from .env
                for line in env_content.split('\n'):
                    if line.startswith('DISCORD_WEBHOOK_URL='):
                        env_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                        if env_url.startswith('https://discord.com/api/webhooks/'):
                            print_status(".env webhook URL format", True, "Valid URL in .env")
                        else:
                            print_status(".env webhook URL format", False, f"Invalid URL: {env_url[:50]}...")
                        break
            else:
                print_status("DISCORD_WEBHOOK_URL in .env", False, "Not found in .env file")
        except Exception as e:
            print_status(".env file readable", False, f"Error reading: {e}")
    else:
        print_status(".env file exists", False, "No .env file found")
    
    # 3. Check config file
    print_header("STEP 3: Configuration File Check")
    
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print_status("Config file loaded", True, f"From {config_path}")
        
        # Check monitoring.alerts section
        monitoring_config = config.get('monitoring', {})
        alerts_config = monitoring_config.get('alerts', {})
        
        if alerts_config:
            print_status("Alerts configuration", True, "Found in config")
            
            # Check webhook URL reference
            webhook_url_config = alerts_config.get('discord_webhook_url')
            if webhook_url_config:
                print_status("discord_webhook_url in config", True, f"Value: {webhook_url_config}")
                
                if webhook_url_config == '${DISCORD_WEBHOOK_URL}':
                    print_status("Environment variable reference", True, "Config references env var correctly")
                else:
                    print_status("Environment variable reference", False, "Config has hardcoded value")
            else:
                print_status("discord_webhook_url in config", False, "Not found")
        else:
            print_status("Alerts configuration", False, "Missing from config")
            issues_found.append("Missing alerts configuration in config.yaml")
            
    except Exception as e:
        print_status("Config file loading", False, f"Error: {str(e)}")
        issues_found.append(f"Config file error: {str(e)}")
    
    # 4. Summary and recommendations
    print_header("SUMMARY")
    
    if not issues_found:
        print("🎉 Configuration looks good!")
        print("\nIf Discord notifications still aren't working:")
        print("   • Check if your Discord webhook URL is active")
        print("   • Verify your signal thresholds")
        print("   • Check Discord server permissions")
    else:
        print(f"❌ Found {len(issues_found)} issue(s):")
        for i, issue in enumerate(issues_found, 1):
            print(f"   {i}. {issue}")
    
    print_header("QUICK FIX")
    
    if not discord_webhook:
        print("""
🔧 TO FIX DISCORD NOTIFICATIONS:

1. Get your Discord webhook URL:
   • Go to your Discord server
   • Server Settings → Integrations → Webhooks  
   • Create New Webhook
   • Copy the webhook URL

2. Set the environment variable:
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_URL_HERE"

3. Or add to .env file:
   echo 'DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_URL_HERE' >> .env

4. Restart your trading system

Example webhook URL format:
https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
""")
    
    # Check if user wants to set webhook URL now
    if not discord_webhook:
        try:
            webhook_input = input("\n📋 Do you have a Discord webhook URL to set now? (y/n): ").strip().lower()
            if webhook_input == 'y':
                new_webhook = input("Enter your Discord webhook URL: ").strip()
                
                if new_webhook.startswith('https://discord.com/api/webhooks/'):
                    # Add to .env file
                    env_file = Path(__file__).parent.parent.parent / ".env"
                    with open(env_file, 'a') as f:
                        f.write(f"\nDISCORD_WEBHOOK_URL={new_webhook}\n")
                    
                    print(f"✅ Added to {env_file}")
                    print("🔄 Please restart your trading system for changes to take effect.")
                    
                    # Set in current environment for testing
                    os.environ['DISCORD_WEBHOOK_URL'] = new_webhook
                    print("✅ Set in current environment for testing.")
                else:
                    print("❌ Invalid webhook URL format!")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main() 